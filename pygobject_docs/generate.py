"""Generate pages from an (imported) GI repository.

Usage:

    python -m pygobject_docs.generate GObject 2.0
"""

import importlib
import sys
import types
from enum import StrEnum, auto

import gi
from gi.module import repository
from gi._gi import FunctionInfo, StructInfo, UnionInfo, ObjectInfo, InterfaceInfo, EnumInfo


class Category(StrEnum):
    Functions = auto()
    Interfaces = auto()
    Classes = auto()
    Structures = auto()  # GI type: record
    Union = auto()
    Flags = auto()
    Constants = auto()
    Ignored = auto()


def categorize(namespace, version):
    """Group elements in a namespace by type.

    For all importable elements in the namespace,
    group them by type:

    * Functions
    * Interfaces
    * Classes
    * Structures
    * Unions
    * Flags
    * Constants
    """


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
    elif isinstance(info, StructInfo) or isinstance(field, gi.types.StructMeta):
        return Category.Structures
    elif isinstance(info, InterfaceInfo) or (namespace, name) == ("GObject", "GInterface"):
        return Category.Interfaces
    elif isinstance(info, ObjectInfo) or isinstance(field, (type, gi.types.GObjectMeta)):
        return Category.Classes
    elif isinstance(field, (str, int, bool, float, tuple, dict, gi._gi.GType)):
        return Category.Constants

    raise TypeError(f"Type not recognized for {module.__name__}.{name}")


def import_module(namespace, version):
    gi.require_version(namespace, version)

    return importlib.import_module(f"gi.repository.{namespace}")


def generate(namespace, version):
    gi.require_version(namespace, version)

    mod = importlib.import_module(f"gi.repository.{namespace}")

    for name in dir(mod):
        yield name


if __name__ == "__main__":
    generate(sys.argv[1], sys.argv[2])
