from textwrap import dedent

import pytest

from pygobject_docs.doc import rstify
from pygobject_docs.gir import load_gir_file


@pytest.mark.parametrize(
    "text, expected",
    [
        ["`class`", "``class``"],
        ["`char*[]`", "``char*[]``"],
        ["`func()`", "``func()``"],
        ["`cls::prop`", "``cls::prop``"],
        ["`interface`s", "``interface``'s"],
        ["test `Class` and `Interface`s.", "test ``Class`` and ``Interface``'s."],
        [
            "[`DBusActivatable` interface](https://some-url#dbus)",
            "```DBusActivatable`` interface <https://some-url#dbus>`_",
        ],
    ],
)
def test_markdown_inline_code(glib, text, expected):
    rst = rstify(text, gir=glib)

    assert rst == expected


def test_convert_constant(glib):
    text = r"""Lorem %TRUE ipsum %FALSE %NULL."""

    rst = rstify(text, gir=glib)

    assert rst == "Lorem :const:`True` ipsum :const:`False` :const:`None`."


def test_convert_markdown_link(glib):
    text = """Lorem ipsum [link text 1](https://gitlab.gnome.org/some_url).
    More Lorem ipsum [second link](https://gitlab.gnome.org/second_url)."""

    rst = rstify(text, gir=glib)

    assert "`link text 1 <https://gitlab.gnome.org/some_url>`" in rst
    assert "`second link <https://gitlab.gnome.org/second_url>`" in rst


def test_convert_code_snippet(glib):
    text = dedent(
        """\
    Lorem ipsum
    |[<!-- language="C" -->
      char buf[G_ASCII_DTOSTR_BUF_SIZE];

      fprintf (out, "value=%s\n", g_ascii_dtostr (buf, sizeof (buf), value));
    ]|
    """
    )

    rst = rstify(text, gir=glib)

    assert ".. code-block:: C" in rst
    assert "   char " in rst
    assert "]|" not in rst


def test_class_link(glib):
    text = "Lorem ipsum [class@Gtk.Builder] et amilet"

    rst = rstify(text, gir=glib)

    assert ":obj:`~gi.repository.Gtk.Builder`" in rst


def test_class_link_without_namespace(glib):
    text = "Lorem ipsum [class@SomeClass] et amilet"

    rst = rstify(text, gir=glib)

    assert ":obj:`~gi.repository.GLib.SomeClass`" in rst


def test_method_link(glib):
    text = "Lorem ipsum [method@Gtk.Builder.foo] et amilet"

    rst = rstify(text, gir=glib)

    assert ":obj:`~gi.repository.Gtk.Builder.foo`" in rst


def test_parameters(glib):
    text = "Lorem @ipsum et amilet"

    rst = rstify(text, gir=glib)

    assert rst == "Lorem ``ipsum`` et amilet"


def test_italic_text(glib):
    text = "This is a func_name and _italic text_."

    rst = rstify(text, gir=glib)

    assert rst == "This is a func_name and *italic text*."


def test_code_abbreviation(glib):
    text = "This is a func_name_ and _italic text_."

    rst = rstify(text, gir=glib)

    assert rst == "This is a ``func_name_`` and *italic text*."


def test_code_abbreviation_with_ellipsis(glib):
    text = "the g_convert_… functions"

    rst = rstify(text, gir=glib)

    assert rst == "the ``g_convert_``… functions"


def test_whitespace_before_lists(glib):
    text = dedent(
        """\
        line of text.
        - list item.
        """
    )

    rst = rstify(text, gir=glib)

    assert rst == dedent(
        """\
        line of text.

        - list item."""
    )


def test_simple_table(glib):
    text = dedent(
        """\
        | field 1 | field 2 |
        | field 3 | long field 4 |

        """
    )

    rst = rstify(text, gir=glib)

    assert rst == dedent(
        """\
        +---------+--------------+
        | field 1 | field 2      |
        +---------+--------------+
        | field 3 | long field 4 |
        +---------+--------------+

        """
    )


def test_table_with_header_row(glib):
    text = dedent(
        """\
        | header 1 | header 2     |
        | -        | ---          |
        | field 1  | field 2      |
        | field 3  | long field 4 |

        """
    )

    rst = rstify(text, gir=glib)

    assert rst == dedent(
        """\
        +----------+--------------+
        | header 1 | header 2     |
        +==========+==============+
        | field 1  | field 2      |
        +----------+--------------+
        | field 3  | long field 4 |
        +----------+--------------+

        """
    )


def test_table_with_multiline_content(glib):
    text = dedent(
        """\
        | | | | |
        | --- | --- | ---- | --- |
        | "none" | ![](default.png) "default" | ![](help.png) "help" |
        | ![](pointer.png) "pointer" | ![](cell_cursor.png) "cell" |

        """
    )

    rst = rstify(text, gir=glib, image_base_url="http://example.com")

    assert rst == dedent(
        """\
        +-------------------------------------------+-----------------------------------------------+
        |                                           |                                               |
        +===========================================+===============================================+
        | "none"                                    | .. image:: http://example.com/default.png     |
        |                                           | "default"                                     |
        +-------------------------------------------+-----------------------------------------------+
        | .. image:: http://example.com/pointer.png | .. image:: http://example.com/cell_cursor.png |
        | "pointer"                                 | "cell"                                        |
        +-------------------------------------------+-----------------------------------------------+

        """
    )


def test_remove_tags(glib):
    text = "I/O Priority # {#io-priority}"

    rst = rstify(text, gir=glib)

    assert rst == "I/O Priority"


@pytest.fixture
def glib():
    return load_gir_file("GLib", "2.0")


@pytest.mark.parametrize(
    "text, expected",
    [
        ["This is a #GQueue", "This is a :obj:`~gi.repository.GLib.Queue`"],
        ["a #gint32 value", "a :obj:`int` value"],
        ["#gint32 value", ":obj:`int` value"],
        ["In a url http://example.com#section-123", "In a url http://example.com#section-123"],
        [
            "If we were to use g_variant_get_child_value()",
            "If we were to use :func:`~gi.repository.GLib.Variant.get_child_value`",
        ],
        ["Good old function g_access()", "Good old function :func:`~gi.repository.GLib.access`"],
        [r"%G_SPAWN_ERROR_TOO_BIG", ":const:`~gi.repository.GLib.SpawnError.TOO_BIG`"],
    ],
)
def test_c_symbol_to_python(glib, text, expected):
    rst = rstify(text, gir=glib)

    assert rst == expected


def test_html_picture_tag(glib):
    text = """
    Freeform text.

    <picture>
        <source srcset="application-window-dark.png" media="(prefers-color-scheme: dark)">
        <img src="application-window.png" alt="application-window">
    </picture>

    More freeform text.
    """

    rst = rstify(text, gir=glib, image_base_url="https://example.com")

    assert "Freeform text." in rst
    assert "More freeform text." in rst
    assert ".. image:: https://example.com/application-window.png" in rst
