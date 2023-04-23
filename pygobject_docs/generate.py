"""Generate pages from an (imported) GI repository.

Usage:

    python -m pygobject_docs.generate GObject 2.0
"""

import importlib
import logging
import sys
import warnings

from functools import lru_cache
from pathlib import Path

import gi
from jinja2 import Environment, PackageLoader
from sphinx.util.inspect import stringify_annotation

from pygobject_docs.category import Category, determine_category, determine_member_category, MemberCategory
from pygobject_docs.doc import rstify
from pygobject_docs.gir import load_gir_file
from pygobject_docs.inspect import is_classmethod, signature
from pygobject_docs.members import own_dir, properties, signals


@lru_cache(maxsize=0)
def import_module(namespace, version):
    gi.require_version(namespace, version)

    return importlib.import_module(f"gi.repository.{namespace}")


@lru_cache(maxsize=0)
def jinja_env():
    env = Environment(loader=PackageLoader("pygobject_docs"), trim_blocks=True, lstrip_blocks=True)
    env.filters["rstify"] = rstify
    return env


def output_path(base_path, namespace, version):
    out_path = base_path / f"{namespace}-{version}"
    out_path.mkdir(exist_ok=True, parents=True)
    return out_path


def generate_functions(namespace, version, out_path):
    mod = import_module(namespace, version)

    if not any(determine_category(mod, name) == Category.Functions for name in dir(mod)):
        return

    gir = load_gir_file(namespace, version)
    env = jinja_env()

    template = env.get_template("functions.j2")

    def parameter_docs(name, sig):
        for param in sig.parameters:
            doc = gir.parameter_doc(name, param)
            yield param, doc

    with warnings.catch_warnings(record=True):
        (out_path / "functions.rst").write_text(
            template.render(
                functions=[
                    (
                        name,
                        sig := signature(getattr(mod, name)),
                        gir.doc(name),
                        parameter_docs(name, sig),
                        gir.return_doc(name),
                        gir.deprecated(name),
                        gir.since(name),
                    )
                    for name in dir(mod)
                    if determine_category(mod, name) == Category.Functions
                ],
                namespace=namespace,
                version=version,
            )
        )
        # TODO: register deprecated function


def generate_constants(namespace, version, out_path):
    mod = import_module(namespace, version)

    if not any(determine_category(mod, name) == Category.Constants for name in dir(mod)):
        return

    gir = load_gir_file(namespace, version)
    env = jinja_env()

    template = env.get_template("constants.j2")

    with warnings.catch_warnings(record=True):
        (out_path / "constants.rst").write_text(
            template.render(
                constants=[
                    (
                        name,
                        getattr(mod, name),
                        gir.doc(name),
                        gir.deprecated(name),
                        gir.since(name),
                    )
                    for name in dir(mod)
                    if determine_category(mod, name) == Category.Constants
                ],
                namespace=namespace,
                version=version,
            )
        )


def generate_classes(namespace, version, out_path, category, singular, plural):
    mod = import_module(namespace, version)
    gir = load_gir_file(namespace, version)
    env = jinja_env()

    template = env.get_template("class-detail.j2")

    class_names = [name for name in dir(mod) if determine_category(mod, name) == category]

    if not class_names:
        return

    for class_name in class_names:
        with warnings.catch_warnings(record=True):
            klass = getattr(mod, class_name)
            # TODO: register deprecated class

        members = own_dir(klass)

        def parameter_docs(member_type, member_name, sig):
            for i, param in enumerate(sig.parameters):
                if i == 0 and param == "self":
                    continue
                doc = gir.member_parameter_doc(member_type, class_name, member_name, param)  # noqa: B023
                yield param, doc

        (out_path / f"{singular}-{class_name}.rst").write_text(
            template.render(
                class_name=class_name,
                namespace=namespace,
                version=version,
                entity_type=singular.title(),
                signature=lambda k, m: signature(getattr(getattr(mod, k), m)),
                docstring=gir.doc,
                constructors=[
                    (
                        name,
                        sig := signature(getattr(klass, name)),
                        gir.member_doc("constructor", class_name, name),
                        parameter_docs("constructor", name, sig),
                        gir.member_return_doc("constructor", class_name, name),
                    )
                    for name in members
                    if determine_member_category(klass, name) == MemberCategory.Constructors
                ],
                fields=[
                    (name, gir.member_doc("field", class_name, name))
                    for name in members
                    if determine_member_category(klass, name) == MemberCategory.Fields
                ],
                methods=[
                    (
                        name,
                        sig := signature(getattr(klass, name)),
                        gir.member_doc("method", class_name, name),
                        parameter_docs("method", name, sig),
                        gir.member_return_doc("method", class_name, name),
                        is_classmethod(getattr(klass, name)),
                    )
                    for name in members
                    if determine_member_category(klass, name) == MemberCategory.Methods
                ],
                properties=[
                    (name, stringify_annotation(type), gir.member_doc("property", class_name, name))
                    for name, type in properties(klass)
                ],
                signals=[
                    (
                        name := info.get_name(),
                        sig := signature(info),
                        gir.member_doc("signal", class_name, name),
                        parameter_docs("signal", name, sig),
                        gir.member_return_doc("signal", class_name, name),
                    )
                    for info in signals(klass)
                ],
                virtual_methods=[
                    (
                        name,
                        sig := signature(getattr(klass, name)),
                        gir.member_doc("virtual-method", class_name, name[3:]),
                        parameter_docs("virtual-method", name[3:], sig),
                        gir.member_return_doc("virtual-method", class_name, name[3:]),
                    )
                    for name in members
                    if determine_member_category(klass, name) == MemberCategory.VirtualMethods
                ],
                return_doc=gir.return_doc,
                deprecated=gir.deprecated,
                since=gir.since,
            )
        )

    template = env.get_template("classes.j2")

    (out_path / f"{plural}.rst").write_text(
        template.render(
            namespace=namespace,
            version=version,
            entity_type=plural.title(),
            prefix=singular,
        )
    )


def generate_index(namespace, version, out_path):
    mod = import_module(namespace, version)
    gir = load_gir_file(namespace, version)
    env = jinja_env()
    template = env.get_template("index.j2")

    def has(category):
        return any(determine_category(mod, name) == category for name in dir(mod))

    (out_path / "index.rst").write_text(
        template.render(
            namespace=namespace,
            version=version,
            dependencies=gir.dependencies,
            classes=has(Category.Classes),
            interfaces=has(Category.Interfaces),
            structures=has(Category.Structures),
            unions=has(Category.Unions),
            bitfields=has(Category.Flags),
            functions=has(Category.Functions),
            constants=has(Category.Constants),
        )
    )


def generate_top_index(out_path):
    env = jinja_env()
    template = env.get_template("top-index.j2")

    (out_path / "index.rst").write_text(template.render())


def generate(namespace, version):
    base_path = Path("build/source")
    out_path = output_path(base_path, namespace, version)

    generate_functions(namespace, version, out_path)
    generate_classes(namespace, version, out_path, Category.Classes, "class", "classes")
    generate_classes(namespace, version, out_path, Category.Interfaces, "interface", "interfaces")
    generate_classes(namespace, version, out_path, Category.Structures, "structure", "structures")
    generate_classes(namespace, version, out_path, Category.Unions, "union", "unions")
    generate_classes(namespace, version, out_path, Category.Flags, "bitfield", "bitfields")
    generate_constants(namespace, version, out_path)
    generate_index(namespace, version, out_path)

    generate_top_index(base_path)


if __name__ == "__main__":
    logging.basicConfig()
    generate(sys.argv[1], sys.argv[2])
