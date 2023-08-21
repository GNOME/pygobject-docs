"""Our own inspect, it can inspect normal Python
methods, as well as gi objects.
"""

import logging
from typing import Any, Callable, Optional, Sequence
from importlib import import_module
from inspect import Signature, Parameter, unwrap
from keyword import iskeyword

from gi._gi import CallbackInfo, CallableInfo, TypeInfo, TypeTag, Direction
from gi.repository import GLib, GObject
from sphinx.util.inspect import signature as sphinx_signature, stringify_signature

from pygobject_docs import overrides


log = logging.getLogger(__name__)

Signature.__str__ = lambda self: stringify_signature(self, unqualified_typehints=True)  # type: ignore[method-assign]


def patch_gi_overrides():
    import gi.overrides
    from gi.overrides import override as real_override

    def override(type_):
        namespace = type_.__module__.rsplit(".", 1)[-1]
        new_type = real_override(type_)
        new_type.__module__ = "gi.repository." + namespace
        new_type.__overridden__ = True
        return new_type

    gi.overrides.override = override


def is_classmethod(klass: type, name: str) -> bool:
    assert getattr(klass, name)
    for c in klass.__mro__:
        if name in c.__dict__:
            obj = c.__dict__.get(name)
            return isinstance(obj, (classmethod, staticmethod))
    return False


def signature(subject: Callable, bound=False) -> Signature:
    if fun := getattr(overrides, _override_key(subject), None):
        return sphinx_signature(fun)
    if subject is GObject.Object.__init__:
        return sphinx_signature(gobject_init_placeholder)
    if isinstance(s := unwrap(subject), CallableInfo):
        return gi_signature(s)

    return sphinx_signature(subject, bound_method=bound)


def gobject_init_placeholder(**properties: Any):
    ...


def _override_key(subject):
    if hasattr(subject, "__module__"):
        return f"{subject.__module__}_{subject.__name__}".replace(".", "_")
    elif ocls := getattr(subject, "__objclass__", None):
        return f"{ocls.__module__}_{ocls.__name__}_{subject.__name__}".replace(".", "_")

    return None


def gi_signature(subject: CallableInfo) -> Signature:
    parameters = []
    return_annotations = []
    array_length_indices = {arg.get_type().get_array_length() for arg in subject.get_arguments()}
    array_length_indices.add(subject.get_return_type().get_array_length())

    for i, arg in enumerate(subject.get_arguments()):
        if arg.get_name().startswith("dummy"):
            continue
        if i in array_length_indices:
            continue

        if arg.get_direction() in (Direction.OUT, Direction.INOUT):
            return_annotations.append(gi_type_to_python(arg.get_type(), out=True))
        elif (t := gi_type_to_python(arg.get_type())) is not None:
            parameters.append(
                Parameter(
                    f"{arg.get_name()}_" if iskeyword(arg.get_name()) else arg.get_name(),
                    Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=t,
                )
            )

    return_type = gi_type_to_python(subject.get_return_type(), out=True)
    if subject.may_return_null() and return_type is not None:
        return_type = Optional[return_type]

    if return_type is not None or len(return_annotations) == 0:
        return_annotations.insert(0, return_type)

    return Signature(
        parameters,
        return_annotation=return_annotations[0]
        if len(return_annotations) == 1
        else tuple[*return_annotations],  # type: ignore[misc]
    )


# From pygobject-stubs


def gi_type_to_python(
    type_info: TypeInfo,
    out: bool = False,
) -> object | type:
    tag = type_info.get_tag()

    if tag == TypeTag.ARRAY:
        array_type = type_info.get_param_type(0)
        t = gi_type_to_python(array_type)
        if out:
            # As output argument array of type uint8 are returned as bytes
            if array_type.get_tag() == TypeTag.UINT8:
                return bytes
            return list[t]  # type: ignore[valid-type]

        # As input arguments array can be generated by any sequence
        return Sequence[t]  # type: ignore[valid-type]

    if tag in (TypeTag.GLIST, TypeTag.GSLIST):
        array_type = type_info.get_param_type(0)
        t = gi_type_to_python(array_type)
        return list[t]  # type: ignore[valid-type]

    if tag == TypeTag.BOOLEAN:
        return bool

    if tag in (TypeTag.DOUBLE, TypeTag.FLOAT):
        return float

    if tag == TypeTag.ERROR:
        return GLib.Error

    if tag == TypeTag.GHASH:
        key_type = type_info.get_param_type(0)
        value_type = type_info.get_param_type(1)
        kt = gi_type_to_python(key_type)
        vt = gi_type_to_python(value_type)
        return dict[kt, vt]  # type: ignore[valid-type]

    if tag in (TypeTag.FILENAME, TypeTag.UTF8, TypeTag.UNICHAR):
        return str

    if tag == TypeTag.GTYPE:
        return type

    if tag in (
        TypeTag.INT8,
        TypeTag.INT16,
        TypeTag.INT32,
        TypeTag.INT64,
        TypeTag.UINT8,
        TypeTag.UINT16,
        TypeTag.UINT32,
        TypeTag.UINT64,
    ):
        return int

    if tag == TypeTag.INTERFACE:
        interface = type_info.get_interface()
        if isinstance(interface, CallbackInfo):
            return _callable_with_arguments(interface)
        else:
            namespace = interface.get_namespace()
            name = interface.get_name()

            if namespace == "GObject" and name == "Value":
                return Any

            if namespace == "GObject" and name == "Closure":
                return Callable[[...], Any]

            if namespace == "cairo" and name == "Context" and not out:
                import cairo

                return cairo.Context

            mod = import_module(f"gi.repository.{namespace}")

            return getattr(mod, name, name)

    if tag == TypeTag.VOID:
        return None

    raise ValueError(f"Unknown type tag: {tag}")


def _callable_with_arguments(
    subject: CallbackInfo,
) -> object:
    parameters: list[object] = []
    return_annotations: list[object | type] = []
    for arg in subject.get_arguments():
        if arg.get_direction() in (Direction.OUT, Direction.INOUT):
            return_annotations.append(gi_type_to_python(arg.get_type(), out=True))
        elif arg.get_closure() >= 0:
            parameters.append(...)
        elif (t := gi_type_to_python(arg.get_type())) is not None:
            parameters.append(t)

    return_type = gi_type_to_python(subject.get_return_type(), out=True)
    if subject.may_return_null() and return_type is not None:
        return_type = Optional[return_type]

    if return_type is not None or len(return_annotations) == 0:
        return_annotations.insert(0, return_type)

    return Callable[
        parameters, return_annotations[0] if len(return_annotations) == 1 else tuple[*return_annotations]  # type: ignore[misc]
    ]
