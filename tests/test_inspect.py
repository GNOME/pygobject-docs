import inspect

from gi.repository import GObject

from pygobject_docs.inspect import signature


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
