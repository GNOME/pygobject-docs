"""Generate pages from an (imported) GI repository.

Usage:

    python -m pygobject_docs.generate GObject 2.0
"""

import importlib
import logging
import sys
import warnings

from functools import lru_cache, partial
from pathlib import Path

import gi
from jinja2 import Environment, PackageLoader
from sphinx.util.inspect import stringify_annotation
from sphinx.util.docstrings import prepare_docstring

from pygobject_docs.category import Category, determine_category, determine_member_category, MemberCategory
from pygobject_docs.doc import rstify
from pygobject_docs.gir import load_gir_file
from pygobject_docs.inspect import (
    custom_docstring,
    is_classmethod,
    signature,
    patch_gi_overrides,
    is_ref_unref_copy_or_steal_function,
)
from pygobject_docs.members import own_dir, properties, signals, virtual_methods

C_API_DOCS = {
    "GLib": "https://docs.gtk.org/glib",
    "GObject": "https://docs.gtk.org/gobject",
    "Gio": "https://docs.gtk.org/gio",
    "Gdk": "https://docs.gtk.org/gdk4",
    "Gsk": "https://docs.gtk.org/gsk4",
    "Gtk": "https://docs.gtk.org/gtk4",
    "Pango": "https://docs.gtk.org/Pango",
    "GdkPixbuf": "https://docs.gtk.org/gdk-pixbuf",
    "Adw": "https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest",
}

BLACKLIST = [
    ("GLib", "GError"),  # Should use GLib.Error instead
    ("GObject", "GObject"),  # Should use GObject.Object instead
    ("GObject", "Object", "newv"),  # Use normal __init__ instead
    ("GObject", "Object", "do_constructed"),
    ("GObject", "Object", "do_finalize"),
]

log = logging.getLogger(__name__)


@lru_cache(maxsize=0)
def import_module(namespace, version):
    gi.require_version(namespace, version)

    return importlib.import_module(f"gi.repository.{namespace}")


@lru_cache(maxsize=0)
def jinja_env(gir):
    namespace, _version = gir.namespace if gir else ("", "")
    env = Environment(loader=PackageLoader("pygobject_docs"), lstrip_blocks=True)
    env.filters["rstify"] = partial(rstify, image_base_url=C_API_DOCS.get(namespace, ""), gir=gir)
    env.filters["capfirst"] = lambda text: f"{text[0].upper()}{text[1:]}" if text else ""
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
    env = jinja_env(gir)
    image_base_url = C_API_DOCS.get(namespace, "")

    template = env.get_template("functions.j2")

    def func_doc(name):
        if custom_doc := custom_docstring(getattr(mod, name, None)):
            return custom_doc
        return rstify(gir.doc(name), gir=gir, image_base_url=image_base_url)

    def parameter_docs(name, sig):
        fdoc = func_doc(name)
        if ":param " in fdoc:
            return

        for param in sig.parameters:
            doc = gir.parameter_doc(name, param)
            yield param, rstify(doc, gir=gir, image_base_url=image_base_url)

    def return_doc(name):
        fdoc = func_doc(name)
        if ":returns:" in fdoc:
            return ""

        return rstify(gir.return_doc(name), gir=gir, image_base_url=image_base_url)

    with warnings.catch_warnings(record=True) as caught_warnings:

        def deprecated(name):
            if depr := gir.deprecated(name):
                version, message = depr
                return version, rstify(message, gir=gir)
            if caught_warnings:
                message = str(caught_warnings[0].message)
                caught_warnings.clear()
                return "PyGObject-3.16.0", rstify(message, gir=gir)
            return None

        (out_path / "functions.rst").write_text(
            template.render(
                functions=[
                    (
                        name,
                        sig := signature(getattr(mod, name)),
                        func_doc(name),
                        parameter_docs(name, sig),
                        return_doc(name),
                        deprecated(name),
                        gir.since(name),
                    )
                    for name in dir(mod)
                    if determine_category(mod, name) == Category.Functions
                    and not is_ref_unref_copy_or_steal_function(name)
                ],
                namespace=namespace,
                version=version,
            )
        )


def generate_constants(namespace, version, out_path):
    mod = import_module(namespace, version)

    if not any(determine_category(mod, name) == Category.Constants for name in dir(mod)):
        return

    gir = load_gir_file(namespace, version)
    env = jinja_env(gir)

    template = env.get_template("constants.j2")

    with warnings.catch_warnings(record=True) as caught_warnings:

        def deprecated(name):
            if depr := gir.deprecated(name):
                version, message = depr
                return version, rstify(message, gir=gir)
            if caught_warnings:
                message = str(caught_warnings[0].message)
                caught_warnings.clear()
                return "PyGObject-3.16.0", rstify(message, gir=gir)
            return None

        (out_path / "constants.rst").write_text(
            template.render(
                constants=[
                    (
                        name,
                        getattr(mod, name),
                        rstify(gir.doc(name), gir=gir),
                        deprecated(name),
                        gir.since(name),
                    )
                    for name in dir(mod)
                    if determine_category(mod, name) == Category.Constants
                ],
                namespace=namespace,
                version=version,
            )
        )


def generate_classes(namespace, version, out_path, category, title=None):
    mod = import_module(namespace, version)
    gir = load_gir_file(namespace, version)

    class_names = [
        name
        for name in dir(mod)
        if determine_category(mod, name, gir) == category and (namespace, name) not in BLACKLIST
    ]

    if not class_names:
        return

    for class_name in class_names:
        with warnings.catch_warnings(record=True) as caught_warnings:
            klass = getattr(mod, class_name)

        if klass is gi.PyGIDeprecationWarning:
            continue

        generate_class(
            gir=gir,
            namespace=namespace,
            version=version,
            class_name=class_name,
            klass=klass,
            out_path=out_path,
            category=category,
            caught_warnings=caught_warnings,
        )

    template = jinja_env(gir).get_template("classes.j2")

    (out_path / f"{category}.rst").write_text(
        template.render(
            namespace=namespace,
            version=version,
            entity_type=title or category.title(),
            prefix=category.single,
        )
    )


def generate_class(gir, namespace, version, class_name, klass, out_path, category, caught_warnings):
    image_base_url = C_API_DOCS.get(namespace, "")
    template = jinja_env(gir).get_template("class-detail.j2")

    class_deprecation = ("PyGObject-3.16.0", str(caught_warnings[0].message)) if caught_warnings else None
    members = [m for m in own_dir(klass) if (namespace, klass.__name__, m) not in BLACKLIST]

    for member in members:
        if member.startswith("_"):
            continue
        field = getattr(klass, member, None)
        if isinstance(field, type):
            log.info("Creating nested class %s.%s => %s", klass, member, field)

            generate_class(
                gir=gir,
                namespace=namespace,
                version=version,
                class_name=f"{class_name}.{member}",
                klass=field,
                out_path=out_path,
                category=category,
                caught_warnings=[],
            )

    def member_doc(member_type, member_name):
        if custom_doc := custom_docstring(getattr(klass, member_name, None)):  # noqa: B023
            return custom_doc

        return rstify(
            gir.member_doc(member_type, class_name, member_name), gir=gir, image_base_url=image_base_url
        )  # noqa: B023

    def member_return_doc(member_type, member_name):
        mdoc = member_doc(member_type, member_name)
        if ":return:" in mdoc:
            return None

        return rstify(
            gir.member_return_doc(member_type, class_name, member_name),
            gir=gir,
            image_base_url=image_base_url,
        )  # noqa: B023

    def parameter_docs(member_type, member_name, sig):
        mdoc = member_doc(member_type, member_name)
        if ":param " in mdoc:
            return

        for i, param in enumerate(sig.parameters):
            if i == 0 and param == "self":
                continue
            doc = rstify(
                gir.member_parameter_doc(member_type, class_name, member_name, param),
                gir=gir,
                image_base_url=image_base_url,
            )  # noqa: B023
            yield param, doc

    (out_path / f"{category.single}-{class_name}.rst").write_text(
        template.render(
            class_name=class_name,
            class_signature="" if category == Category.Enums else signature(klass.__init__, bound=True),
            namespace=namespace,
            version=version,
            entity_type=category.single.title(),
            doc=rstify(gir.doc(class_name), gir=gir, image_base_url=image_base_url)
            or ("\n".join(prepare_docstring(klass.__doc__)) if klass.__doc__ else ""),
            deprecated=gir.deprecated(class_name) or class_deprecation,
            since=gir.since(class_name),
            ancestors=gir.ancestors(class_name),
            descendants=gir.descendants(class_name),
            implements=gir.implements(class_name),
            implementations=gir.implementations(class_name),
            constructors=[
                (
                    name,
                    sig := signature(getattr(klass, name), bound=True),
                    member_doc("constructor", name),
                    parameter_docs("constructor", name, sig),
                    member_return_doc("constructor", name),
                    gir.member_deprecated("constructor", class_name, name),
                    gir.member_since("constructor", class_name, name),
                )
                for name in members
                if determine_member_category(klass, name) == MemberCategory.Constructors
            ],
            fields=[
                (
                    name,
                    member_doc("field", field_name := name.lower()),
                    gir.member_deprecated("field", class_name, field_name),
                    gir.member_since("field", class_name, field_name),
                )
                for name in members
                if determine_member_category(klass, name) == MemberCategory.Fields
            ],
            methods=[
                (
                    name,
                    sig := signature(getattr(klass, name), bound=True),
                    member_doc("method", name),
                    parameter_docs("method", name, sig),
                    member_return_doc("method", name),
                    is_classmethod(klass, name),
                    gir.member_deprecated("method", class_name, name),
                    gir.member_since("method", class_name, name),
                )
                for name in members
                if determine_member_category(klass, name) == MemberCategory.Methods
                and not is_ref_unref_copy_or_steal_function(name)
            ],
            properties=[
                (
                    name,
                    stringify_annotation(type, mode="smart"),
                    member_doc("property", name),
                    gir.member_deprecated("property", class_name, name),
                    gir.member_since("property", class_name, name),
                )
                for name, type in properties(klass)
            ],
            signals=[
                (
                    name := info.get_name(),
                    sig := signature(info),
                    member_doc("signal", name),
                    parameter_docs("signal", name, sig),
                    member_return_doc("signal", name),
                    gir.member_deprecated("signal", class_name, name),
                    gir.member_since("signal", class_name, name),
                )
                for info in signals(klass)
            ],
            virtual_methods=[
                (
                    f"do_{info.get_name()}",
                    sig := signature(info),
                    member_doc("virtual-method", info.get_name()),
                    parameter_docs("virtual-method", info.get_name(), sig),
                    member_return_doc("virtual-method", info.get_name()),
                    gir.member_deprecated("virtual-method", class_name, info.get_name()),
                    gir.member_since("virtual-method", class_name, info.get_name()),
                )
                for info in virtual_methods(klass)
                if (namespace, klass.__name__, f"do_{info.get_name()}") not in BLACKLIST
            ],
        )
    )


def generate_index(namespace, version, out_path):
    mod = import_module(namespace, version)
    gir = load_gir_file(namespace, version)
    env = jinja_env(gir)
    template = env.get_template("index.j2")

    library_version = (
        ".".join(map(str, [mod.MAJOR_VERSION, mod.MINOR_VERSION, mod.MICRO_VERSION]))
        if hasattr(mod, "MAJOR_VERSION")
        else "-"
    )

    def has(category):
        return any(determine_category(mod, name, gir) == category for name in dir(mod))

    (out_path / "index.rst").write_text(
        template.render(
            namespace=namespace,
            version=version,
            library_version=library_version,
            c_api_doc_link=C_API_DOCS.get(namespace, ""),
            dependencies=gir.dependencies,
            classes=has(Category.Classes),
            interfaces=has(Category.Interfaces),
            structures=has(Category.Structures),
            unions=has(Category.Unions),
            enums=has(Category.Enums),
            functions=has(Category.Functions),
            constants=has(Category.Constants),
            init_function="init" in dir(mod),
        )
    )


def generate_top_index(out_path):
    env = jinja_env(None)
    template = env.get_template("top-index.j2")

    (out_path / "index.rst").write_text(template.render())


def generate(namespace, version, base_path):
    out_path = output_path(base_path, namespace, version)

    generate_functions(namespace, version, out_path)
    generate_classes(namespace, version, out_path, Category.Classes)
    generate_classes(namespace, version, out_path, Category.Interfaces)
    generate_classes(namespace, version, out_path, Category.Structures)
    generate_classes(namespace, version, out_path, Category.Unions)
    generate_classes(namespace, version, out_path, Category.Enums)
    generate_constants(namespace, version, out_path)
    generate_index(namespace, version, out_path)

    generate_top_index(base_path)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s:%(message)s", datefmt="%H:%M:%S", level=logging.INFO
    )

    patch_gi_overrides()
    for arg in sys.argv[1:]:
        namespace, version = arg.split("-")
        log.info("Generating pages for %s", namespace)
        base_path = Path("build/source")
        generate(namespace, version, base_path)
