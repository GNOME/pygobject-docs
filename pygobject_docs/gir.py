from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from gi.repository import GLib


@lru_cache(maxsize=0)
def load_gir_file(namespace, version) -> Gir | None:
    for gir_dir in gir_dirs():
        if (gir_file := gir_dir / f"{namespace}-{version}.gir").exists():
            return Gir(gir_file)
    return None


def gir_dirs() -> Iterable[Path]:
    return (path for d in GLib.get_system_data_dirs() if (path := Path(d) / "gir-1.0").exists())


NS = {"": "http://www.gtk.org/introspection/core/1.0", "glib": "http://www.gtk.org/introspection/glib/1.0"}


class Gir:
    def __init__(self, gir_file: Path):
        self.gir_file = gir_file
        self.etree = ElementTree.parse(gir_file)

    @property
    def namespace(self):
        namespace = self.etree.find("./namespace", namespaces=NS)
        return namespace.attrib["name"], namespace.attrib["version"]

    def node(self, name):
        return self.etree.find(f"./namespace/*[@name='{name}']", namespaces=NS)

    def doc(self, name) -> str:
        node = self.node(name)
        return node and node.findtext("./doc", namespaces=NS) or ""

    def parameter_doc(self, func_name, param_name):
        if not (node := self.node(func_name)):
            return

        return node.findtext(f"./parameters/parameter[@name='{param_name}']/doc", namespaces=NS) or ""

    def return_doc(self, name) -> str:
        if not (node := self.node(name)):
            return ""
        return node.findtext("./return-value/doc", namespaces=NS) or ""

    def deprecated(self, name) -> tuple[bool, str, str]:
        if not (node := self.node(name)):
            return False, "", ""

        deprecated = node.attrib.get("deprecated")
        version = node.attrib.get("deprecated-version") or ""
        doc = node.findtext("./doc-deprecated", namespaces=NS) or ""

        return deprecated, version, doc

    def since(self, name) -> str | None:
        if not (node := self.node(name)):
            return None

        return node.attrib.get("version")

    def member_doc(self, type_name, class_name, name):
        if not (node := self.node(class_name)):
            return ""
        return node.findtext(f"./{type_name}[@name='{name}']/doc", namespaces=NS) or ""

    def member(self, member_type, klass_name, name):
        if "(" in name:
            name, _ = name.split("(", 1)

        if not (node := self.node(klass_name)):
            return None

        member = node.find(f"./{member_type}[@name='{name}']", namespaces=NS)
        if not member and (cnode := self.node(f"{klass_name}Class")):
            member = cnode.find(f"./{member_type}[@name='{name}']", namespaces=NS)

        return member

    def member_parameter_doc(self, member_type, klass_name, member_name, param_name):
        if not (member := self.member(member_type, klass_name, member_name)):
            return

        return member.findtext(f"./parameters/parameter[@name='{param_name}']/doc", namespaces=NS) or ""

    def member_return_doc(self, member_type, klass_name, name):
        if not (member := self.member(member_type, klass_name, name)):
            return ""

        return member.findtext("./return-value/doc", namespaces=NS) or ""


# Classes:
# - .@parent
# - ./implements
# - ./constructor (+ parameters)
# - ./method (+ parameters+ property?)
# - ./property
# - ./virtual-method
