"""Generate pages from an (imported) GI repository.

Usage:

    python -m pygobject_docs.generate GObject 2.0
"""

import importlib
import sys
import types

from enum import StrEnum, auto
from functools import lru_cache
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


@lru_cache(maxsize=0)
def import_module(namespace, version):
    gi.require_version(namespace, version)

    return importlib.import_module(f"gi.repository.{namespace}")


def rstify(text):
    # See also https://gitlab.gnome.org/GNOME/gi-docgen/-/blob/main/gidocgen/utils.py
    # replace @\w+
    # replace #\w+ (type ref); #guint64 -> :obj:int
    # replace \w+()
    # replace %TRUE|FALSE|NULL -> ":const:`True`", etc.
    return text.replace("`", "")


@lru_cache(maxsize=0)
def jinja_env():
    env = Environment(loader=PackageLoader("pygobject_docs"))
    env.filters["rstify"] = rstify
    return env


def output_path(base_path, namespace, version):
    out_path = base_path / f"{namespace}-{version}"
    out_path.mkdir(exist_ok=True, parents=True)
    return out_path


def generate_functions(namespace, version, out_path):
    mod = import_module(namespace, version)
    gir = load_gir_file(namespace, version)
    env = jinja_env()

    template = env.get_template("functions.j2")

    (out_path / "functions.rst").write_text(
        template.render(
            functions=[f for f in dir(mod) if determine_category(mod, f) == Category.Functions],
            namespace=namespace,
            version=version,
            docstring=gir.doc,
            parameter_docs=gir.parameter_docs,
            return_doc=gir.return_doc,
            deprecated=gir.deprecated,
            since=gir.since,
        )
    )


def generate_classes(namespace, version, out_path):
    mod = import_module(namespace, version)
    gir = load_gir_file(namespace, version)
    env = jinja_env()

    template = env.get_template("class-detail.j2")

    class_names = [name for name in dir(mod) if determine_category(mod, name) == Category.Classes]

    for name in class_names:
        if determine_category(mod, name) != Category.Classes:
            continue

        (out_path / f"class-{name}.rst").write_text(
            template.render(
                name=name,
                namespace=namespace,
                version=version,
                docstring=gir.doc,
                parameter_docs=gir.parameter_docs,
                return_doc=gir.return_doc,
                deprecated=gir.deprecated,
                since=gir.since,
            )
        )

    template = env.get_template("classes.j2")

    (out_path / "classes.rst").write_text(
        template.render(
            classes=class_names,
            namespace=namespace,
            version=version,
        )
    )


def generate_index(out_path):
    env = jinja_env()
    template = env.get_template("index.j2")

    (out_path / "index.rst").write_text(template.render())


def generate(namespace, version):
    base_path = Path("build/source")
    out_path = output_path(base_path, namespace, version)

    generate_functions(namespace, version, out_path)
    generate_classes(namespace, version, out_path)

    generate_index(base_path)


if __name__ == "__main__":
    generate(sys.argv[1], sys.argv[2])
