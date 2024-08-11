"""Our own inspect, it can inspect normal Python
methods, as well as gi objects.
"""

import logging
from typing import Any, Callable, NamedTuple, Optional, Sequence
from importlib import import_module
from inspect import Signature, Parameter, unwrap
from keyword import iskeyword
from re import match

import gi._gi as GI
from gi.repository import GLib, GObject
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.inspect import getdoc, signature as sphinx_signature, stringify_signature

from pygobject_docs import overrides


log = logging.getLogger(__name__)

Signature.__str__ = lambda self: stringify_signature(self, unqualified_typehints=True)  # type: ignore[method-assign]


def patch_gi_overrides():
    import gi.overrides
    from gi.overrides import override as real_override

    def override(type_):
        namespace = type_.__module__.rsplit(".", 1)[-1]
        new_type = real_override(type_)
        log.info("%s is overridden", new_type)
        new_type.__module__ = "gi.repository." + namespace
        new_type.__overridden__ = new_type
        return new_type

    gi.overrides.override = override

    # Fix already loaded types

    GLib.Idle.__module__ = "gi.repository.GLib"
    GLib.IOChannel.__module__ = "gi.repository.GLib"
    GLib.MainContext.__module__ = "gi.repository.GLib"
    GLib.MainLoop.__module__ = "gi.repository.GLib"
    GLib.PollFD.__module__ = "gi.repository.GLib"
    GLib.Source.__module__ = "gi.repository.GLib"
    GLib.Timeout.__module__ = "gi.repository.GLib"
    GLib.Variant.__module__ = "gi.repository.GLib"
    GObject.Binding.__module__ = "gi.repository.GObject"
    GObject.Object.__module__ = "gi.repository.GObject"
    GObject.Value.__module__ = "gi.repository.GObject"


def is_classmethod(klass: type, name: str) -> bool:
    assert getattr(klass, name)
    for c in klass.__mro__:
        if name in c.__dict__:
            obj = c.__dict__.get(name)
            return isinstance(obj, (classmethod, staticmethod))
    return False


def is_ref_unref_copy_or_steal_function(name) -> bool:
    return bool(match(r"^(\w*_)?(ref|unref|copy|steal)(_\w*)?$", name))


def custom_docstring(subject: Callable | None) -> str | None:
    if subject.__doc__:
        doc = prepare_docstring(getdoc(subject))
        return None if not doc or match(r"^\w+\(.*\)", doc[0]) else "\n".join(doc)

    try:
        key = _override_key(subject)
    except AttributeError:
        return None

    if key and (fun := getattr(overrides, key, None)) and (doc := getdoc(fun)):
        return "\n".join(prepare_docstring(doc))
    return None


def signature(subject: Callable, bound=False) -> Signature:
    if fun := getattr(overrides, _override_key(subject), None):
        return sphinx_signature(fun)
    if isinstance(s := unwrap(subject), GI.CallableInfo):
        return gi_signature(s)

    return sphinx_signature(subject, bound_method=bound)


def _override_key(subject):
    if hasattr(subject, "__module__"):
        return f"{subject.__module__}_{subject.__name__}".replace(".", "_")
    elif ocls := getattr(subject, "__objclass__", None):
        return f"{ocls.__module__}_{ocls.__name__}_{subject.__name__}".replace(".", "_")

    return None


def gi_signature(subject: GI.CallableInfo) -> Signature:
    parameters = []

    (names, args, return_args) = _callable_get_arguments(subject, True)

    for name, arg in zip(names, args):
        if name.startswith("dummy"):
            continue

        if name.startswith("*"):
            kind = Parameter.VAR_POSITIONAL
            name = name[1:]
        else:
            kind = Parameter.POSITIONAL_OR_KEYWORD  # type: ignore[assignment]

        annotation, default = arg if isinstance(arg, AnnotationAndDefault) else (arg, Parameter.empty)
        parameters.append(
            Parameter(
                f"{name}_" if iskeyword(name) else name,
                kind,
                annotation=annotation,
                default=default,
            )
        )

    return Signature(
        parameters,
        return_annotation=return_args[0]
        if len(return_args) == 1
        else tuple[*return_args],  # type: ignore[misc]
    )


class AnnotationAndDefault(NamedTuple):
    annotation: object
    default: object | None


def gi_type_to_python(type_info: GI.TypeInfo) -> object:
    return _type_to_python(type_info)


# Adapted from pygobject-stubs
# Our version returns real types, instead of strings.
# https://github.com/pygobject/pygobject-stubs/commit/96586a1ac0f6f7f84512afa89366b29b841cd61b


def _type_to_python(type_info: GI.TypeInfo, out_arg: bool = False, varargs: bool = False) -> object:
    tag = type_info.get_tag()
    tags = GI.TypeTag

    if tag == tags.ARRAY:
        array_type = type_info.get_param_type(0)
        t = _type_to_python(array_type)
        if out_arg:
            # As output argument array of type uint8 are returned as bytes
            if array_type.get_tag() == GI.TypeTag.UINT8:
                return bytes
            return list[t]  # type: ignore[valid-type]

        # As input arguments array can be generated by any sequence
        return Sequence[t]  # type: ignore[valid-type]

    if tag in (tags.GLIST, tags.GSLIST):
        array_type = type_info.get_param_type(0)
        t = _type_to_python(array_type)
        return list[t]  # type: ignore[valid-type]

    if tag == tags.BOOLEAN:
        return bool

    if tag in (tags.DOUBLE, tags.FLOAT):
        return float

    if tag == tags.ERROR:
        return GLib.Error

    if tag == tags.GHASH:
        key_type = type_info.get_param_type(0)
        value_type = type_info.get_param_type(1)
        kt = _type_to_python(key_type)
        vt = _type_to_python(value_type)
        return dict[kt, vt]  # type: ignore[valid-type]

    if tag in (tags.FILENAME, tags.UTF8, tags.UNICHAR):
        return str

    if tag == tags.GTYPE:
        return type

    if tag in (
        tags.INT8,
        tags.INT16,
        tags.INT32,
        tags.INT64,
        tags.UINT8,
        tags.UINT16,
        tags.UINT32,
        tags.UINT64,
    ):
        return int

    if tag == tags.INTERFACE:
        interface = type_info.get_interface()
        if isinstance(interface, GI.CallbackInfo):
            (names, args, return_args) = _callable_get_arguments(interface)

            if len(return_args) == 1:
                return_type = return_args[0]
            else:
                return_type = tuple[*return_args]  # type: ignore[misc]

            # FIXME, how to express Callable with variable arguments?
            if (len(names) > 0 and names[-1].startswith("*")) or varargs:
                return Callable[..., return_type]
            else:
                return Callable[[*args], return_type]
        else:
            namespace = interface.get_namespace()
            name = interface.get_name()

            if namespace == "GObject" and name == "Value":
                return Any

            if namespace == "GObject" and name == "Closure":
                return Callable[..., Any]

            if namespace == "cairo" and name == "Context" and not out_arg:
                import cairo

                return cairo.Context

            mod = import_module(f"gi.repository.{namespace}")
            return getattr(mod, name, name)

    if tag == tags.VOID:
        return None

    raise ValueError(f"Unknown type tag: {tag}")


def _callable_get_arguments(
    type_info: GI.CallbackInfo,
    can_default: bool = False,
) -> tuple[list[str], list[object], list[object]]:
    function_args = type_info.get_arguments()
    accept_optional_args = False
    optional_args_name = ""
    dict_names: dict[int, str] = {}
    dict_args: dict[int, GI.ArgInfo] = {}
    str_args: list[object] = []
    dict_return_args: dict[int, object] = {}
    skip: list[int] = []

    # Filter out array length arguments for return type
    ret_type = type_info.get_return_type()
    if ret_type.get_array_length() >= 0:
        skip.append(ret_type.get_array_length())

    for i, arg in enumerate(function_args):
        if i in skip:
            continue

        # Special case, GObject.signal_handler_find(), has user data, but the closure has no reference to the data.
        if arg.get_closure() >= i:
            accept_optional_args = True
            optional_args_name = function_args[arg.get_closure()].get_name()
            skip.append(arg.get_closure())
            skip.append(arg.get_destroy())
        elif arg.get_closure() >= 0:
            log.warning(
                "Cannot define optional args for already processed argument for function %s: %s <- %s",
                type_info.get_name(),
                function_args[arg.get_closure()].get_name(),
                arg.get_name(),
            )

        # Filter out array length args
        arg_type = arg.get_type()
        len_arg: int = arg_type.get_array_length()
        if len_arg >= 0:
            skip.append(len_arg)
            if len_arg < i:
                dict_names.pop(len_arg, None)
                dict_args.pop(len_arg, None)
                dict_return_args.pop(len_arg, None)

        # Need to check because user_data can be the first arg
        if arg.get_closure() != i and arg.get_destroy() != i:
            direction = arg.get_direction()
            if direction == GI.Direction.OUT or direction == GI.Direction.INOUT:
                t = _type_to_python(arg.get_type(), out_arg=True)

                dict_return_args[i] = t
            elif direction == GI.Direction.IN or direction == GI.Direction.INOUT:
                dict_names[i] = arg.get_name()
                dict_args[i] = arg

    # Traverse args in reverse to check for optional args
    args = list(dict_args.values())
    for arg in reversed(args):
        t = _type_to_python(
            arg.get_type(),
            out_arg=False,
            varargs=arg.get_closure() >= 0,  # True if function admits variable arguments
        )

        if arg.may_be_null() and t is not None:
            if can_default:
                str_args.append(AnnotationAndDefault(Optional[t], None))
            else:
                str_args.append(Optional[t])
        else:
            can_default = False
            str_args.append(t)

    str_args = list(reversed(str_args))
    names = list(dict_names.values())

    if accept_optional_args:
        names.append(f"*{optional_args_name}")
        str_args.append(Any)

    return_type = _type_to_python(type_info.get_return_type(), out_arg=True)
    if type_info.may_return_null() and return_type is not None:
        return_type = Optional[return_type]

    return_args = list(dict_return_args.values())
    if return_type is not None or len(return_args) == 0:
        return_args.insert(0, return_type)

    return (names, str_args, return_args)
