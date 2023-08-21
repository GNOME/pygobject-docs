from typing import Any, Callable, Sequence

from gi.repository import GLib, GObject


# GLib
def gi__gi_add_emission_hook(
    type: GObject.Object, name: str, callback: Callable[[...], None], *args: Any  # type: ignore[misc]
) -> None:
    ...


def gi__gi_spawn_async(  # type: ignore[empty-body]
    argv: Sequence[str],
    envp: Sequence[str] | None = None,
    working_directory: str | None = None,
    flags: GLib.SpawnFlags = GLib.SpawnFlags.DEFAULT,
    child_setup: Callable[[Any], None] | None = None,
    user_data: Any = None,
    standard_input: bool = False,
    standard_output: bool = False,
    standard_error: bool = False,
) -> tuple[GLib.Pid, int | None, int | None, int | None]:
    """
    Execute a child program asynchronously within a GLib main loop.
    See the reference manual for a complete reference.
    """


def gi__gi_Pid_close() -> None:
    ...


# GObject
def gi__gi_list_properties() -> list[GObject.ParamSpec]:  # type: ignore[empty-body]
    ...


def gi__gi_new(gtype: GObject.GType) -> None:
    ...


def gi__gi_signal_new(  # type: ignore[empty-body]
    signal_name: str,
    itype: type[GObject.Object],
    signal_flags: GObject.SignalFlags,
    return_type: type,
    param_types: Sequence[GObject.GType],
) -> int:
    ...


def gi__gi_type_register(type) -> GObject.GType:
    ...


def gi__gi_GObject_bind_property(
    source_property: str, target: GObject.Object, target_property: str, flags: GObject.BindingFlags | None
) -> GObject.Binding:
    ...


def gi__gi_GObject_chain(*params) -> object:
    ...


def gi__gi_GObject_connect(  # type: ignore[empty-body]
    detailed_signal: str, handler: Callable[[GObject.Object, ...], Any], *args: Any  # type: ignore[misc]
) -> int:
    ...


def gi__gi_GObject_connect_after(  # type: ignore[empty-body]
    detailed_signal: str, handler: Callable[[GObject.Object, ...], Any], *args: Any  # type: ignore[misc]
) -> int:
    ...


def gi__gi_GObject_connect_object(  # type: ignore[empty-body]
    detailed_signal: str, handler: Callable[[GObject.Object, ...], Any], object: GObject.Object, *args: Any  # type: ignore[misc]
) -> int:
    ...


def gi__gi_GObject_connect_object_after(  # type: ignore[empty-body]
    detailed_signal: str, handler: Callable[[GObject.Object, Any], Any], object: GObject.Object, *args: Any
) -> int:
    ...


def gi__gi_GObject_disconnect_by_func(func: Callable[[GObject.Object, ...], Any]) -> None:  # type: ignore[misc]
    ...


def gi__gi_GObject_emit(signal_name: str, *args) -> None:
    ...


def gi__gi_GObject_get_properties(*prop_names: str) -> tuple[Any, ...]:  # type: ignore[empty-body]
    ...


def gi__gi_GObject_get_property(prop_name: str) -> Any:
    ...


def gi__gi_GObject_handler_block_by_func(func: Callable[[GObject.Object, ...], ...]) -> int:  # type: ignore[empty-body,misc]
    ...


def gi__gi_GObject_handler_unblock_by_func(func: Callable[[GObject.Object, ...], ...]) -> int:  # type: ignore[empty-body,misc]
    ...


def gi__gi_GObject_set_properties(**props) -> None:
    ...


def gi__gi_GObject_set_property(prop_name: str, prop_value: Any) -> None:
    ...


def gi__gi_GObject_weak_ref(callback: Callable[[Any], None] | None, *args: Any) -> GObject.Object:
    ...


# GLib.OptionContext


def gi__gi_OptionContext_add_group(group: GLib.OptionGroup) -> None:
    ...


def gi__gi_OptionContext_get_help_enabled() -> bool:  # type: ignore[empty-body]
    ...


def gi__gi_OptionContext_get_ignore_unknown_options() -> bool:  # type: ignore[empty-body]
    ...


def gi__gi_OptionContext_get_main_group() -> GLib.OptionGroup:
    ...


def gi__gi_OptionContext_parse(argv: Sequence[str]) -> tuple[bool, list[str]]:  # type: ignore[empty-body]
    ...


def gi__gi_OptionContext_set_help_enabled(help_enabled: bool) -> None:
    ...


def gi__gi_OptionContext_set_ignore_unknown_options(ignore_unknown: bool) -> None:
    ...


def gi__gi_OptionContext_set_main_group(group: GLib.OptionGroup) -> None:
    ...


def gi__gi_OptionGroup_add_entries(entries: list[GLib.OptionEntry]) -> None:
    ...


def gi__gi_OptionGroup_set_translation_domain(domain: str) -> None:
    ...


def gi__gi_GObjectWeakRef_unref() -> None:
    ...


def gobject_GBoxed_copy() -> GObject.GBoxed:
    ...


# GObject.GType


def None_from_name(name: str) -> GObject.GType:
    ...


def gobject_GType_has_value_table() -> None:
    ...


def gobject_GType_is_a(type: GObject.GType) -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_abstract() -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_classed() -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_deep_derivable() -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_derivable() -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_instantiatable() -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_interface() -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_value_abstract() -> bool:  # type: ignore[empty-body]
    ...


def gobject_GType_is_value_type() -> bool:  # type: ignore[empty-body]
    ...
