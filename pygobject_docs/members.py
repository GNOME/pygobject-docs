from itertools import chain

from gi._gi import SignalInfo, VFuncInfo

from pygobject_docs.inspect import gi_type_to_python


def own_dir(obj_type: type) -> list[str]:
    # Find all elements of a type, that are part of the type
    # and not of a parent or interface.

    if obj_type.__module__.startswith("gi.overrides"):
        parent_types = obj_type.__base__.__bases__
    else:
        parent_types = obj_type.__bases__

    members = set(dir(obj_type))
    parent_members: set[str] = set(chain(*(dir(b) for b in parent_types)))

    return sorted(members - parent_members)


def properties(obj_type: type) -> list[tuple[str, object | type]]:
    try:
        props = obj_type.__info__.get_properties()  # type: ignore[attr-defined]
    except AttributeError:
        return []

    return sorted((p.get_name(), gi_type_to_python(p.get_type())) for p in props)


def virtual_methods(obj_type: type) -> list[VFuncInfo]:
    try:
        vfuncs = obj_type.__info__.get_vfuncs()  # type: ignore[attr-defined]
    except AttributeError:
        return []

    return sorted(vfuncs, key=lambda v: v.get_name())


def signals(obj_type: type) -> list[SignalInfo]:
    try:
        sigs = obj_type.__info__.get_signals()  # type: ignore[attr-defined]
    except AttributeError:
        return []

    return sorted(sigs, key=lambda s: s.get_name())
