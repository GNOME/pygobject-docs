import types
from enum import StrEnum, auto

from gi.module import repository
from gi._gi import EnumInfo, FunctionInfo, GType, InterfaceInfo, ObjectInfo, StructInfo, UnionInfo, VFuncInfo
from gi.types import GObjectMeta, StructMeta
from gi.repository import GObject


class Category(StrEnum):
    Functions = auto()
    Interfaces = auto()
    Classes = auto()
    Structures = auto()  # GI type: record
    Unions = auto()
    Flags = auto()
    Constants = auto()
    Ignored = auto()


class MemberCategory(StrEnum):
    Constructors = auto()
    Methods = auto()
    Properties = auto()
    Fields = auto()
    Signals = auto()
    VirtualMethods = auto()
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
    elif isinstance(info, FunctionInfo) or isinstance(
        field,
        (
            FunctionInfo,
            types.FunctionType,
            types.BuiltinFunctionType,
        ),
    ):
        return Category.Functions
    elif isinstance(info, UnionInfo):
        return Category.Unions
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


def determine_member_category(obj_type, name) -> MemberCategory:
    field = getattr(obj_type, name, None)

    if (
        name == "props"
        or name.startswith("_")
        or field in (GObject.Object._unsupported_method, GObject.Object._unsupported_data_method)
        or isinstance(field, type)
    ):
        return MemberCategory.Ignored
    elif isinstance(field, FunctionInfo):
        return MemberCategory.Constructors if field.is_constructor() else MemberCategory.Methods
    elif isinstance(
        field,
        (
            types.FunctionType,
            types.BuiltinFunctionType,
            types.MethodType,
            types.MethodDescriptorType,
        ),
    ):
        return MemberCategory.Methods
    elif (
        isinstance(field, VFuncInfo)
        or field is None
        and name.startswith("do_")
        and name[3:] in (v.get_name() for v in obj_type.__info__.get_vfuncs())
    ):
        return MemberCategory.VirtualMethods
    elif isinstance(field, (GObject.GEnum, GObject.GFlags, property, types.GetSetDescriptorType)):
        return MemberCategory.Fields

    raise TypeError(f"Member type not recognized for {obj_type.__name__}.{name} ({getattr(obj_type, name)})")
