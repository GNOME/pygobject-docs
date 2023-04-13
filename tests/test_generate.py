from pygobject_docs.generate import (
    generate_classes,
    generate_functions,
)


def test_generate_functions(tmp_path):
    generate_functions("GLib", "2.0", tmp_path)

    assert (tmp_path / "functions.rst").exists()
    assert ".. deprecated" in (tmp_path / "functions.rst").read_text()


def test_generate_classes(tmp_path):
    generate_classes("GLib", "2.0", tmp_path)

    assert (tmp_path / "class-GError.rst").exists()
