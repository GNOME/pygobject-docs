import pytest
from gi.repository import GObject

from pygobject_docs.inspect import is_classmethod, signature


def test_function_signature():
    def func(arg: str, obj: GObject.Object) -> str | int:
        return 1

    assert str(signature(func)) == "(arg: str, obj: ~gi.overrides.GObject.Object) -> str | int"


def test_builtin_function_signature():
    assert (
        str(signature(GObject.add_emission_hook))
        == "(value1: ~gi.overrides.GObject.Object, value2: str, value3: ~typing.Callable[[...], None], value4: ..., /) -> None"
    )


@pytest.mark.skip(reason="Inconsistent results on my laptop and Gitlab")
def test_function_with_callback_signature():
    assert (
        str(signature(GObject.signal_add_emission_hook))
        == "(signal_id: int, detail: int, hook_func: ~typing.Callable[[~gi.repository.GObject.SignalInvocationHint, int, ~typing.Sequence[~typing.Any]], bool], data_destroy: ~typing.Callable[[], None]) -> int"
    )


def test_class_signature():
    class Foo:
        def method(self, arg: int) -> GObject.Object:
            ...

    assert str(signature(Foo.method)) == "(self, arg: int) -> ~gi.overrides.GObject.Object"


def test_gi_function_signature():
    assert (
        str(signature(GObject.flags_complete_type_info))
        == "(g_flags_type: type, const_values: ~gi.repository.GObject.FlagsValue) -> ~gi.repository.GObject.TypeInfo"
    )
    assert (
        str(signature(GObject.signal_handler_unblock))
        == "(instance: ~gi.overrides.GObject.Object, handler_id: int) -> None"
    )


def test_builtin_method():
    assert (
        str(signature(GObject.GObject.bind_property))
        == "(value1: str, value2: ~gi.overrides.GObject.Object, value3: str, value4: ~gi.repository.GObject.BindingFlags | None, /) -> None"
    )


@pytest.mark.desktop
def test_method_with_multiple_return_values():
    from gi.repository import Gtk

    assert str(signature(Gtk.Scrollable.get_border)) == "() -> tuple[bool, gi.repository.Gtk.Border]"


def test_python_method_is_classmethod():
    class A:
        @classmethod
        def yup(cls):
            ...

        def nope(self):
            ...

    assert is_classmethod(A.yup)
    assert not is_classmethod(A.nope)


def test_gi_function_is_classmethod():
    assert is_classmethod(GObject.Object.install_properties)
    assert not is_classmethod(GObject.Object.notify)
