import inspect

import pytest
from gi.repository import GObject

from pygobject_docs.inspect import is_classmethod, signature


def test_function_signature():
    def func(arg: str, obj: GObject.Object) -> str | int:
        return 1

    assert str(signature(func)) == "(arg: str, obj: ~gi.overrides.GObject.Object) -> str | int"
    assert str(inspect.signature(func)) == "(arg: str, obj: ~gi.overrides.GObject.Object) -> str | int"


def test_builtin_function_signature():
    assert str(signature(GObject.add_emission_hook)) == "(*tbd)"


def test_function_with_callback_signature():
    assert (
        str(signature(GObject.signal_add_emission_hook))
        == "(signal_id: int, detail: int, hook_func: ~typing.Callable[[~gi.repository.GObject.SignalInvocationHint, int, ~typing.Sequence[~typing.Any], ...], bool], data_destroy: ~typing.Callable[[], None]) -> int"
    )


def test_class_signature():
    class Foo:
        def method(self, arg: int) -> GObject.Object:
            ...

    assert str(signature(Foo.method)) == "(self, arg: int) -> ~gi.overrides.GObject.Object"
    assert str(inspect.signature(Foo.method)) == "(self, arg: int) -> ~gi.overrides.GObject.Object"


def test_gi_function():
    func = GObject.flags_complete_type_info

    assert (
        str(signature(func))
        == "(g_flags_type: type, const_values: ~gi.repository.GObject.FlagsValue) -> ~gi.repository.GObject.TypeInfo"
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
