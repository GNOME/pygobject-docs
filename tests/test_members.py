import pytest

from pygobject_docs.generate import import_module
from pygobject_docs.members import own_dir, properties


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
