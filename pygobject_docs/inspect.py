"""Our own inspect, it can inspect normal Python
methods, as well as gi objects.
"""

import logging
from typing import Any, Callable, Optional, Sequence
from importlib import import_module
from inspect import Signature, Parameter, ismethod, unwrap

from gi._gi import CallbackInfo, CallableInfo, TypeInfo, TypeTag, Direction, StructInfo
from gi.repository import GLib, GObject
from sphinx.util.inspect import signature as sphinx_signature, stringify_signature


log = logging.getLogger(__name__)

Signature.__str__ = lambda self: stringify_signature(self, unqualified_typehints=True)  # type: ignore[method-assign]

SIGNATURE_OVERRIDES = {
    # GLib
    ("gi._gi", "add_emission_hook"): ((GObject.Object, str, Callable[[...], None], ...), None),
    ("gi._gi", "spawn_async"): (
        (str, Sequence[str], Sequence[str], GLib.SpawnFlags, Callable[[...], None]),
        tuple[bool, int],
    ),
    ("gi._gi", "Pid", "close"): ((), None),
    ("gi._gi", "OptionContext", "add_group"): ((GLib.OptionGroup,), None),
    ("gi._gi", "OptionContext", "get_help_enabled"): ((), bool),
    ("gi._gi", "OptionContext", "get_ignore_unknown_options"): ((), bool),
    ("gi._gi", "OptionContext", "get_main_group"): ((), GLib.OptionGroup),
    ("gi._gi", "OptionContext", "parse"): ((str,), tuple[bool, list[str]]),
    ("gi._gi", "OptionContext", "set_help_enabled"): ((bool,), None),
    ("gi._gi", "OptionContext", "set_ignore_unknown_options"): ((bool,), None),
    ("gi._gi", "OptionContext", "set_main_group"): ((GLib.OptionGroup,), None),
    ("gi._gi", "OptionGroup", "add_entries"): ((list[GLib.OptionEntry],), None),
    ("gi._gi", "OptionGroup", "set_translation_domain"): ((str,), None),
    # GObject
    ("gi._gi", "list_properties"): ((), list[GObject.ParamSpec]),
    ("gi._gi", "new"): ((GObject.GType,), None),
    ("gi._gi", "signal_new"): ((str, type[GObject.Object], GObject.SignalFlags, type, list[type]), int),  # type: ignore[index]
    ("gi._gi", "type_register"): ((type[GObject.Object],), GObject.GType),  # type: ignore[index]
    ("gobject", "GBoxed", "copy"): ((), GObject.GBoxed),
    ("gi._gi", "GObjectWeakRef", "unref"): ((), None),
    (None, "from_name"): ((str,), GObject.GType),
    ("gobject", "GType", "has_value_table"): ((), None),
    ("gobject", "GType", "is_a"): ((GObject.Object,), bool),
    ("gobject", "GType", "is_abstract"): ((), bool),
    ("gobject", "GType", "is_classed"): ((), bool),
    ("gobject", "GType", "is_deep_derivable"): ((), bool),
    ("gobject", "GType", "is_derivable"): ((), bool),
    ("gobject", "GType", "is_instantiatable"): ((), bool),
    ("gobject", "GType", "is_interface"): ((), bool),
    ("gobject", "GType", "is_value_abstract"): ((), bool),
    ("gobject", "GType", "is_value_type"): ((), bool),
}


def is_classmethod(subject: Callable) -> bool:
    if isinstance(subject, CallableInfo):
        # -Class objects are structs
        return isinstance(subject.get_container(), StructInfo)

    return ismethod(subject)


def signature(subject: Callable) -> Signature:
    if sig := SIGNATURE_OVERRIDES.get(_override_key(subject)):
        param_types, return_type = sig
        return Signature(
            [
                Parameter(f"value{i}", Parameter.POSITIONAL_ONLY, annotation=t)
                for i, t in enumerate(param_types, start=1)
            ],
            return_annotation=return_type,
        )

    if isinstance(s := unwrap(subject), CallableInfo):
        return gi_signature(s)

    return sphinx_signature(subject)


def _override_key(subject):
    if hasattr(subject, "__module__"):
        return (subject.__module__, subject.__name__)
    elif ocls := getattr(subject, "__objclass__", None):
        return (ocls.__module__, ocls.__name__, subject.__name__)

    return None


def gi_signature(subject: CallableInfo) -> Signature:
    parameters = []
    return_annotations = []
    for arg in subject.get_arguments():
        if arg.get_direction() in (Direction.OUT, Direction.INOUT):
            return_annotations.append(gi_type_to_python(arg.get_type(), out=True))
        elif (t := gi_type_to_python(arg.get_type())) is not None:
            parameters.append(
                Parameter(
                    arg.get_name(),
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
