import pytest

from pygobject_docs.category import (
    determine_category,
    Category,
)
from pygobject_docs.generate import import_module


@pytest.fixture
def glib():
    return import_module("GLib", "2.0")


@pytest.fixture
def gobject():
    return import_module("GObject", "2.0")


def test_determine_function(glib):
    category = determine_category(glib, "filename_from_utf8")

    assert category == Category.Functions


@pytest.mark.parametrize("name", ["Object", "GType", "Binding"])
def test_determine_gobject_class(gobject, name):
    category = determine_category(gobject, name)

    assert category == Category.Classes


def test_determine_glib_structure(glib):
    category = determine_category(glib, "Error")

    assert category == Category.Structures


@pytest.mark.parametrize("name", ["CClosure", "EnumClass", "Value"])
def test_determine_gobject_structure(gobject, name):
    category = determine_category(gobject, name)

    assert category == Category.Structures


def test_determine_glib_union(glib):
    category = determine_category(glib, "FloatIEEE754")

    assert category == Category.Union


@pytest.mark.parametrize("name", ["GInterface", "TypePlugin"])
def test_determine_gobject_interface(gobject, name):
    category = determine_category(gobject, name)

    assert category == Category.Interfaces


@pytest.mark.parametrize("name", ["OptionFlags", "IOFlags"])
def test_determine_glib_flag(glib, name):
    category = determine_category(glib, name)

    assert category == Category.Flags


@pytest.mark.parametrize("name", ["GINT32_FORMAT", "BIG_ENDIAN"])
def test_determine_glib_constant(glib, name):
    category = determine_category(glib, name)

    assert category == Category.Constants


@pytest.mark.parametrize(
    "name,category",
    [
        ["threads_init", Category.Functions],
        ["unix_signal_add_full", Category.Functions],
    ],
)
def test_determine_glib_field_category(glib, name, category):
    actual_category = determine_category(glib, name)

    assert actual_category == category


@pytest.mark.parametrize("name,category", [["add_emission_hook", Category.Functions]])
def test_determine_gobject_field_category(gobject, name, category):
    actual_category = determine_category(gobject, name)

    assert actual_category == category


def test_all_glib_fields_are_categorized(glib):
    for name in dir(glib):
        determine_category(glib, name)


def test_all_gobject_fields_are_categorized(gobject):
    for name in dir(gobject):
        determine_category(gobject, name)


@pytest.mark.desktop
@pytest.mark.parametrize(
    "namespace,version",
    [
        ["Gtk", "4.0"],
        ["Gdk", "4.0"],
        ["Pango", "1.0"],
    ],
)
def test_all_gtk_fields_are_categorized(namespace, version):
    mod = import_module(namespace, version)

    for name in dir(mod):
        determine_category(mod, name)
