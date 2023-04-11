import pytest

from pygobject_docs import gir as _gir


@pytest.fixture
def glib():
    g = _gir.load_gir_file("GLib", "2.0")
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
