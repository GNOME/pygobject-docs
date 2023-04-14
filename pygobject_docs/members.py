def own_dir(obj_type: type) -> list[str]:
    # Find all eleents of a type, that are part of the type
    # and not of a parent or interface.
    members = set(dir(obj_type))
    parent_members: set[str] = set(*(dir(b) for b in obj_type.__bases__))

    return sorted(members - parent_members)
