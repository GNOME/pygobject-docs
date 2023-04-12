"""Generate pages from an (imported) GI repository.

Usage:

    python -m pygobject_docs.generate GObject 2.0
"""

import importlib
import sys
import types
from enum import StrEnum, auto
from pathlib import Path

import gi
from gi.module import repository
from gi._gi import FunctionInfo, StructInfo, UnionInfo, ObjectInfo, InterfaceInfo, EnumInfo
from jinja2 import Environment, PackageLoader

from pygobject_docs.gir import load_gir_file


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
    mod = import_module(namespace, version)

    gir = load_gir_file(namespace, version)

    def docstring(name):
        if doc := gir.doc(name):
            return doc

        field = getattr(mod, name)
        return getattr(field, "__doc__", None) or ""

    env = Environment(loader=PackageLoader("pygobject_docs"))
    template = env.get_template("functions.j2")

    out_path = Path("source") / f"{namespace}-{version}"
    out_path.mkdir(exist_ok=True, parents=True)

    (out_path / "functions.rst").write_text(
        template.render(
            namespace=namespace,
            version=version,
            module=mod,
            functions=[f for f in dir(mod) if determine_category(mod, f) == Category.Functions],
            docstring=docstring,
            parameter_docs=gir.parameter_docs,
            return_doc=gir.return_doc,
        )
    )


if __name__ == "__main__":
    generate(sys.argv[1], sys.argv[2])
