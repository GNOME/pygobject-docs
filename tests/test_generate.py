import gi

from pygobject_docs.category import Category
from pygobject_docs.generate import (
    import_module,
    generate_classes,
    generate_functions,
)


def test_generate_functions(tmp_path):
    generate_functions("GLib", "2.0", tmp_path)

    assert (tmp_path / "functions.rst").exists()
    assert ".. deprecated" in (tmp_path / "functions.rst").read_text()


def test_generate_classes(tmp_path):
    generate_classes("GLib", "2.0", tmp_path, Category.Classes, "class", "classes")

    assert (tmp_path / "class-GError.rst").exists()


def test_gi_method_type():
    gobject = import_module("GObject", "2.0")

    assert not callable(gobject.ParamSpecBoxed.name)
    assert callable(gobject.ParamSpecBoxed.do_values_cmp)
    assert type(gobject.ParamSpecBoxed.do_values_cmp) is gi._gi.VFuncInfo
