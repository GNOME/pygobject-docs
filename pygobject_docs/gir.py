from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from xml.etree import ElementTree

from gi.repository import GLib


def load_gir_file(namespace, version) -> Gir | None:
    for gir_dir in gir_dirs():
        if (gir_file := gir_dir / f"{namespace}-{version}.gir").exists():
            return Gir(gir_file)
    return None


def gir_dirs() -> Iterable[Path]:
    return (path for d in GLib.get_system_data_dirs() if (path := Path(d) / "gir-1.0").exists())


NS = {"": "http://www.gtk.org/introspection/core/1.0"}


class Gir:
    def __init__(self, gir_file: Path):
        self.gir_file = gir_file
        self.etree = ElementTree.parse(gir_file)

    @property
    def namespace(self):
        namespace = self.etree.find("./namespace", namespaces=NS)
        return namespace.attrib["name"], namespace.attrib["version"]

    def doc(self, name) -> str:
        node = self.etree.find(f"./namespace/*[@name='{name}']", namespaces=NS)
        return node and node.findtext("./doc", namespaces=NS) or ""
