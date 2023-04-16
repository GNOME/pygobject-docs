from itertools import chain


def own_dir(obj_type: type) -> list[str]:
    # Find all elements of a type, that are part of the type
    # and not of a parent or interface.
    members = set(dir(obj_type))

    if obj_type.__module__.startswith("gi.overrides"):
        parent_types = obj_type.__base__.__bases__
    else:
        parent_types = obj_type.__bases__

    parent_members: set[str] = set(chain(*(dir(b) for b in parent_types)))

    return sorted(members - parent_members)
