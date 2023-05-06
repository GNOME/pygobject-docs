from __future__ import annotations

import logging
from collections.abc import Iterable
from functools import lru_cache
from itertools import chain
from pathlib import Path

from gi.repository import GLib
from gidocgen.gir import GirParser, Class, Enumeration, Function, Repository, Type


log = logging.getLogger(__name__)


def load_gir_file(namespace, version) -> Gir | None:
    for gir_dir in gir_dirs():
        if (gir_file := gir_dir / f"{namespace}-{version}.gir").exists():
            return Gir(gir_file)
    return None


@lru_cache(maxsize=0)
def _parse(gir_file) -> Repository:
    parser = GirParser(gir_dirs())
    parser.parse(gir_file)
    repo = parser.get_repository()
    assert repo
    return repo


def gir_dirs() -> Iterable[Path]:
    return [path for d in GLib.get_system_data_dirs() if (path := Path(d) / "gir-1.0").exists()]


NS = {"": "http://www.gtk.org/introspection/core/1.0", "glib": "http://www.gtk.org/introspection/glib/1.0"}


class Gir:
    def __init__(self, gir_file: Path):
        self.repo = _parse(gir_file)

    @property
    def namespace(self):
        ns = self.repo.namespace
        return ns.name, ns.version

    @property
    def dependencies(self):
        return (f"{r.namespace.name}-{r.namespace.version}" for r in self.repo.includes.values())

    def _node(self, name) -> Function | Type | None:
        node = self.repo.namespace.find_real_type(name) or self.repo.namespace.find_function(name)
        if not node:
            log.debug("No GIR type found for %s", name)
        return node

    def ancestors(self, name) -> Iterable[str]:
        if not (node := self._node(name)) or not isinstance(node, Class):
            return []

        return [f"gi.repository.{anc.fqtn}" for anc in node.ancestors]

    def implements(self, name) -> list[str]:
        if not (node := self._node(name)) or not isinstance(node, Class):
            return []

        return [f"gi.repository.{impl.fqtn}" for impl in node.implements]

    def doc(self, name) -> str:
        if not (obj := self._node(name)) or not obj.doc:
            return ""

        return obj.doc.content or ""

    def parameter_doc(self, func_name, param_name):
        if not (obj := self.repo.namespace.find_function(func_name)):
            return ""

        param = next((p for p in obj.parameters if p.name == param_name), None)
        if not param or not param.doc:
            return ""

        return param.doc.content or ""

    def return_doc(self, name) -> str:
        if (obj := self.repo.namespace.find_function(name)) and obj.return_value and obj.return_value.doc:
            return obj.return_value.doc.content or ""

        return ""

    def deprecated(self, name) -> tuple[bool, str, str]:
        if not (obj := self._node(name)):
            return False, "", ""

        return (obj.deprecated, *(obj.deprecated_since or ("", "")))  # type: ignore[return-value]

    def since(self, name) -> str | None:
        if not (obj := self._node(name)):
            return None

        return obj.available_since

    def member(self, member_type, class_name, name):
        if "(" in name:
            name, _ = name.split("(", 1)

        if not (node := self._node(class_name)):
            return None

        if member_type == "constructor":
            return next((m for m in node.constructors if m.name == name), None)
        if member_type == "method":
            return (hasattr(node, "methods") and next((m for m in node.methods if m.name == name), None)) or (
                hasattr(node, "functions")
                and next((m for m in node.functions if m.name in (name, f"interface_{name}")), None)
            )
        if member_type == "virtual-method":
            return next((m for m in node.virtual_methods if m.name == name), None)
        if member_type == "property":
            return node.properties.get(name, None)
        if member_type == "signal":
            return node.signals.get(name, None)
        if member_type == "field":
            if isinstance(node, Enumeration):
                return next((m for m in node.members if m.name == name), "")
            return next((m for m in node.fields if m.name == name), "")

        raise ValueError("Unhandled member type %s", member_type)

    def member_doc(self, member_type, class_name, name):
        if (member := self.member(member_type, class_name, name)) and member.doc:
            return member.doc.content or ""

        return ""

    def member_parameter_doc(self, member_type, klass_name, member_name, param_name):
        if not (member := self.member(member_type, klass_name, member_name)):
            return

        param = next((p for p in member.parameters if p.name == param_name), None)
        if param and param.doc:
            return param.doc.content or ""

        return ""

    def member_return_doc(self, member_type, klass_name, name):
        if not (member := self.member(member_type, klass_name, name)):
            return ""

        if (
            (member := self.repo.namespace.find_function(name))
            and member.return_value
            and member.return_value.doc
        ):
            return member.return_value.doc.content or ""

        return ""

    def c_type(self, name: str) -> str | None:
        def find(name: str):
            for ts in self.repo.types.values():
                for t in ts:
                    ctype = getattr(t, "ctype", "")
                    if ctype.startswith("const "):
                        ctype = ctype[6:]
                    while ctype.endswith("*"):
                        ctype = ctype[:-1]
                    if name == ctype:
                        return t.fqtn

        if maybe_type := find(name):
            return maybe_type

        # Deal with plurals:
        if name.endswith("s") and (maybe_type := find(name[:-1])):
            return maybe_type

        log.warning("C type %s not found", name)
        return None

    def c_symbol(self, name: str) -> str | None:
        if not (symbol := self.repo.find_symbol(name)):
            return None

        ns, s = symbol
        if isinstance(s, Type) and (
            method := next((m for m in chain(s.methods, s.functions) if m.identifier == name), None)
        ):
            return f"{ns.name}.{s.name}.{method.name}"
        elif isinstance(s, Function):
            return f"{ns.name}.{s.name}"

        log.warning("C symbol %s not found", name)
        return None
