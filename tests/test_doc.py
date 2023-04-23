from textwrap import dedent

from pygobject_docs.doc import rstify


def test_convert_constant():
    text = """Lorem %TRUE ipsum %FALSE %NULL."""

    rst = rstify(text)

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


def test_method_link():
    text = "Lorem ipsum [method@Gtk.Builder.foo] et amilet"

    rst = rstify(text)

    assert ":obj:`~gi.repository.Gtk.Builder.foo`" in rst


def test_parameters():
    text = "Lorem @ipsum et amilet"

    rst = rstify(text)

    assert rst == "Lorem ``ipsum`` et amilet"
