import types
from enum import StrEnum, auto

from gi.module import repository
from gi._gi import EnumInfo, FunctionInfo, GType, InterfaceInfo, ObjectInfo, StructInfo, UnionInfo
from gi.types import GObjectMeta, StructMeta


class Category(StrEnum):
    Functions = auto()
    Interfaces = auto()
    Classes = auto()
    Structures = auto()  # GI type: record
    Union = auto()
    Flags = auto()
    Constants = auto()
    Ignored = auto()


def determine_category(module, name) -> Category:
    """Determine the category to put the field in

    The category is based on the GI type info. For custom
    and overridden fields some extra checks are done.
    """
    field = getattr(module, name)

    namespace = module.__name__.split(".")[-1]
    info = repository.find_by_name(namespace, name)

    if name.startswith("_") or isinstance(field, types.ModuleType):
        return Category.Ignored
    elif isinstance(info, FunctionInfo) or type(field) in (
        FunctionInfo,
        types.FunctionType,
        types.BuiltinFunctionType,
    ):
        return Category.Functions
    elif isinstance(info, UnionInfo):
        return Category.Union
    elif isinstance(info, EnumInfo):
        return Category.Flags
    elif isinstance(info, StructInfo) or isinstance(field, StructMeta):
        return Category.Structures
    elif isinstance(info, InterfaceInfo) or (namespace, name) == ("GObject", "GInterface"):
        return Category.Interfaces
    elif isinstance(info, ObjectInfo) or isinstance(field, (type, GObjectMeta)):
        return Category.Classes
    elif isinstance(field, (str, int, bool, float, tuple, dict, GType)):
        return Category.Constants

    raise TypeError(f"Type not recognized for {module.__name__}.{name}")
