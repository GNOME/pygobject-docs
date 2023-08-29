import pytest

from pygobject_docs.generate import import_module
from pygobject_docs.members import own_dir, properties, signals


@pytest.fixture
def gobject():
    return import_module("GObject", "2.0")


def test_override_include_members_from_class(gobject):
    obj_type = gobject.Object

    names = own_dir(obj_type)

    assert "handler_is_connected" in names
    assert "connect_data" in names


def test_override_include_members_from_base(gobject):
    obj_type = gobject.Object

    names = own_dir(obj_type)

    assert "bind_property_full" in names


def test_should_not_include_unsuppoered_methods(gobject):
    ...


def test_properties(gobject):
    props = properties(gobject.Binding)

    assert ("source", gobject.Object) in props


def test_signals(gobject):
    sigs = signals(gobject.Object)

    assert sigs


@pytest.mark.desktop
def test_no_suplicate_methods():
    from gi.repository import Gtk

    members = own_dir(Gtk.RecentInfo)

    assert "get_application_info" in members
    assert len(list(m for m in members if m == "get_application_info")) == 1
