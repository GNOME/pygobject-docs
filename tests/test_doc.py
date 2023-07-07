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
def test_markdown_inline_code(text, expected):
    rst = rstify(text)

    assert rst == expected


def test_convert_constant(glib):
    text = r"""Lorem %TRUE ipsum %FALSE %NULL."""

    rst = rstify(text, gir=glib)

    assert rst == "Lorem :const:`True` ipsum :const:`False` :const:`None`."


def test_convert_markdown_link():
    text = """Lorem ipsum [link text 1](https://gitlab.gnome.org/some_url).
    More Lorem ipsum [second link](https://gitlab.gnome.org/second_url)."""

    rst = rstify(text)

    assert "`link text 1 <https://gitlab.gnome.org/some_url>`" in rst
    assert "`second link <https://gitlab.gnome.org/second_url>`" in rst


def test_convert_code_snippet():
    text = dedent(
        """\
    Lorem ipsum
    |[<!-- language="C" -->
      char buf[G_ASCII_DTOSTR_BUF_SIZE];

      fprintf (out, "value=%s\n", g_ascii_dtostr (buf, sizeof (buf), value));
    ]|
    """
    )

    rst = rstify(text)

    assert ".. code-block:: C" in rst
    assert "   char " in rst
    assert "]|" not in rst


def test_class_link():
    text = "Lorem ipsum [class@Gtk.Builder] et amilet"

    rst = rstify(text)

    assert ":obj:`~gi.repository.Gtk.Builder`" in rst


def test_class_link_without_namespace():
    text = "Lorem ipsum [class@Builder] et amilet"

    rst = rstify(text)

    assert ":obj:`Builder`" in rst


def test_method_link():
    text = "Lorem ipsum [method@Gtk.Builder.foo] et amilet"

    rst = rstify(text)

    assert ":obj:`~gi.repository.Gtk.Builder.foo`" in rst


def test_parameters():
    text = "Lorem @ipsum et amilet"

    rst = rstify(text)

    assert rst == "Lorem ``ipsum`` et amilet"


def test_italic_text():
    text = "This is a func_name and _italic text_."

    rst = rstify(text)

    assert rst == "This is a func_name and *italic text*."


def test_code_abbreviation():
    text = "This is a func_name_ and _italic text_."

    rst = rstify(text)

    assert rst == "This is a ``func_name_`` and *italic text*."


def test_whitespace_before_lists():
    text = dedent(
        """\
        line of text.
        - list item.
        """
    )

    rst = rstify(text)

    assert rst == dedent(
        """\
        line of text.

        - list item."""
    )


def test_simple_table():
    text = dedent(
        """\
        | field 1 | field 2 |
        | field 3 | long field 4 |

        """
    )

    rst = rstify(text)

    assert rst == dedent(
        """\
        +---------+--------------+
        | field 1 | field 2      |
        +---------+--------------+
        | field 3 | long field 4 |
        +---------+--------------+

        """
    )


def test_table_with_header_row():
    text = dedent(
        """\
        | header 1 | header 2     |
        | -        | ---          |
        | field 1  | field 2      |
        | field 3  | long field 4 |

        """
    )

    rst = rstify(text)

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


def test_remove_tags():
    text = "I/O Priority # {#io-priority}"

    rst = rstify(text)

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
def test_c_symbol_to_python(text, expected, glib):
    rst = rstify(text, gir=glib)

    assert rst == expected


def test_html_picture_tag():
    text = """
    Freeform text.

    <picture>
        <source srcset="application-window-dark.png" media="(prefers-color-scheme: dark)">
        <img src="application-window.png" alt="application-window">
    </picture>

    More freeform text.
    """

    rst = rstify(text, image_base_url="https://example.com")

    assert "Freeform text." in rst
    assert "More freeform text." in rst
    assert ".. image:: https://example.com/application-window.png" in rst
