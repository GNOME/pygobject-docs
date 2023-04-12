import pytest

from pygobject_docs import gir as _gir


@pytest.fixture
def glib():
    g = _gir.load_gir_file("GLib", "2.0")
    assert g
    return g


@pytest.fixture
def gobject():
    g = _gir.load_gir_file("GObject", "2.0")
    assert g
    return g


def test_gir_dirs():
    dirs = _gir.gir_dirs()

    assert dirs


def test_load_gir_file(glib):
    assert str(glib.gir_file) == "/usr/share/gir-1.0/GLib-2.0.gir"
    assert glib.etree
    assert next(glib.etree.iter(), None)


def test_gir_namespace(glib):
    assert glib.namespace == ("GLib", "2.0")


def test_gir_function_doc(glib):
    doc = glib.doc("filename_from_utf8")

    assert doc
    assert doc.startswith("Converts ")


def test_gir_class_doc(gobject):
    doc = gobject.doc("Binding")

    assert doc
    assert doc.startswith("#GBinding ")


def test_gir_function_parameter_docs(gobject):
    name, doc = next(gobject.parameter_docs("boxed_copy"))

    assert name == "boxed_type"
    assert doc


def test_gir_function_return_doc(gobject):
    doc = gobject.return_doc("boxed_copy")

    assert doc
