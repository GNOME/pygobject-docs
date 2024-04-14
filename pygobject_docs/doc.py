"""Translate gtk-doc text to reStructuredText.

TODO:

- replace #\\w+ (type ref); #guint64 -> :obj:int
  else lookup Type.ctype or some field/member and provide official type
- replace \\w+() -> look up Callable.identifier in GIR repo and return official type
- convert tables to list-tables. https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table

See also https://gitlab.gnome.org/GNOME/gi-docgen/-/blob/main/gidocgen/utils.py

"""

from functools import partial
from itertools import zip_longest
import re


def rstify(text, gir, *, image_base_url=""):
    """Convert gtk-doc to rst."""
    if not text:
        return ""

    lines = text.splitlines(keepends=False)

    return pipe(
        lines,
        code_snippets,
        tags,
        markdown_italic,
        code_abbreviations,
        partial(c_constants, gir=gir),
        whitespace_before_lists,
        partial(markdown_table, image_url=image_base_url, gir=gir),
        partial(markdown_images, image_url=image_base_url),
        partial(gtk_doc_link, namespace=gir.namespace[0]),
        parameters,  # after gtk-doc links, since those also contain `@` symbols
        markdown_inline_code,
        markdown_links,
        s_after_inline_code,
        markdown_heading,
        partial(c_type, gir=gir),
        partial(c_symbol, gir=gir),
        partial(html_picture, image_url=image_base_url),
        "\n".join,
    )


def pipe(obj, *filters):
    for f in filters:
        obj = f(obj)
    return obj


def markdown_italic(lines):
    return (re.sub(r"(?:(?<!\w)|^)_([^_]+?)_((?!\w)|$)", r"*\1*", line) for line in lines)


def markdown_inline_code(lines):
    return (re.sub(r"(?:(?<![:`])|^)`([^` ]+?)`(?=[^`]|$)", r"``\1``", line) for line in lines)


def code_abbreviations(lines):
    return (re.sub(r"(?:(?<!\w)|^)(\w+_[\.]*)(?!\w)", r"``\1``", line) for line in lines)


def s_after_inline_code(lines):
    return (re.sub(r"(?<=`)s(?=\W|$)", r"'s", line) for line in lines)


def parameters(lines):
    return (re.sub(r"@(\w+)", r"``\1``", line) for line in lines)


def markdown_table(lines, image_url, gir):
    def as_table(table_lines):
        cells = [
            [
                rstify(cell.strip(), gir=gir, image_base_url=image_url).strip()
                for cell in line[1:-1].split("|")
            ]
            for line in table_lines
        ]
        lens = [max(max(len(line) for line in cell.split("\n")) for cell in col) for col in zip(*cells)]
        sep = "-"
        for row in cells:
            if "---" in row:
                sep = "="
            else:
                yield "+" + "+".join(sep * (len + 2) for len in lens) + "+"
                for line in zip_longest(*(cell.split("\n") for cell in row), fillvalue=""):
                    yield "| " + " | ".join(
                        cell.lstrip().ljust(length) for cell, length in zip(line, lens)
                    ) + " |"
                sep = "-"
        yield "+" + "+".join("-" * (len + 2) for len in lens) + "+"
        yield ""

    table_lines = []
    for line in lines:
        if line.startswith("| ") and line.endswith("|"):
            table_lines.append(line)
        else:
            if table_lines:
                yield from as_table(table_lines)
                del table_lines[:]
            yield line

    if table_lines:
        yield from as_table(table_lines)


def markdown_images(lines, image_url):
    return (re.sub(r" *!\[.*?\]\((.+?)\)", f"\n.. image:: {image_url}/\\1\n", line) for line in lines)


def markdown_links(lines):
    return (re.sub(r"\[(.+?)\]\((.+?)\)", r"`\1 <\2>`_", line) for line in lines)


def markdown_heading(lines):
    for line in lines:
        if re.search(r"^#+ ", line):
            h = line.split(" ", 1)[1]
            yield h
            yield "-" * len(h)
        else:
            yield line


def code_snippets(lines):
    """Deal with markdown and gtk-doc style code blocks."""
    in_code = False
    for line in lines:
        if not in_code and line.startswith("```"):
            yield "\n.. code-block::\n   :dedent:\n"
            in_code = True
        elif not in_code and re.search(r"^ *\|\[", line):
            yield re.sub(
                r' *\|\[ *(<!-- *language="(\w+)" *-->)?', r"\n.. code-block:: \2\n   :dedent:\n", line
            )
            in_code = True
        elif in_code and line == "```":
            yield ""
            in_code = False
        elif in_code and re.search(r"^ *\]\|", line):
            yield ""
            in_code = False
        elif in_code:
            yield f"   {line}"
        else:
            yield line


def tags(lines):
    return (re.sub(r" *# +\{#[\w-]+\}$", "", line) for line in lines)


def gtk_doc_link(lines, namespace):
    tmp = (
        re.sub(
            r"\[(?:ctor|class|const|enum|error|flags|func|id|iface|method|struct|type|vfunc)@(.+?)\]",
            lambda m: f":obj:`~gi.repository.{m.group(1)}`"
            if "." in m.group(1)
            else f":obj:`~gi.repository.{namespace}.{m.group(1)}`",
            line,
        )
        for line in lines
    )
    tmp = (
        re.sub(
            r"\[property@([^:]+?):(.+?)\]",
            lambda m: f":attr:`~gi.repository.{m.group(1)}.props.{m.group(2).replace('-', '_')}`"
            if "." in m.group(1)
            else f":attr:`~gi.repository.{namespace}.{m.group(1)}.props.{m.group(2).replace('-', '_')}`",
            line,
        )
        for line in tmp
    )
    tmp = (
        re.sub(
            r"\[signal@([^:]+?)::(.+?)\]",
            lambda m: f":obj:`~gi.repository.{m.group(1)}.signals.{m.group(2).replace('-', '_')}`"
            if "." in m.group(1)
            else f":obj:`~gi.repository.{namespace}.{m.group(1)}.signals.{m.group(2).replace('-', '_')}`",
            line,
        )
        for line in tmp
    )
    return (
        re.sub(
            r"\[`*(?:alias|callback)@(.+?)`*\]",
            r"``\1``",
            line,
        )
        for line in tmp
    )


def whitespace_before_lists(lines):
    paragraph = True
    for line in lines:
        if paragraph and line.startswith("-"):
            yield ""
            yield line
            paragraph = False
        elif not paragraph and line and line[0] not in (" ", "-"):
            yield line
            paragraph = True
        else:
            yield line


def html_picture(lines, image_url):
    picture = False
    for line in lines:
        if "<picture>" in line:
            picture = True
        if "</picture>" in line:
            picture = False
        elif picture and "<img " in line:
            path = re.sub(r'^.* src="([^"]+)".*$', r"\1", line)
            yield f".. image:: {image_url}/{path}"
        elif not picture:
            yield line


def c_type(lines, gir):
    if not gir:
        return lines

    def repl(m: re.Match[str]) -> str:
        p = m.group(1)
        g = m.group(2)
        if g.startswith("gint") or g.startswith("gunit"):
            return f"{p}:obj:`int`"
        if g == "gdouble":
            return f"{p}:obj:`float`"
        if t := gir.c_type(g):
            return f"{p}:obj:`~gi.repository.{t}`"
        return f"{p}``{g}``"

    return (re.sub(r"(\W|\A)#(\w+)", repl, line) for line in lines)


def c_symbol(lines, gir):
    if not gir:
        return lines

    def repl(m: re.Match[str]) -> str:
        g = m.group(1)
        if s := gir.c_symbol(g):
            return f":func:`~gi.repository.{s}`"
        return f"{g}()"

    return (re.sub(r"(\w+)\(\)", repl, line) for line in lines)


_python_consts = {
    "TRUE": ":const:`True`",
    "FALSE": ":const:`False`",
    "NULL": ":const:`None`",
    "G_TYPE_CHAR": ":obj:`int`",
    "G_TYPE_INT": ":obj:`int`",
    "G_TYPE_INT64": ":obj:`int`",
    "G_TYPE_LONG": ":obj:`int`",
    "G_TYPE_UCHAR": "unsigned :obj:`int`",
    "G_TYPE_UINT": "unsigned :obj:`int`",
    "G_TYPE_UINT64": "unsigned :obj:`int`",
    "G_TYPE_ULONG": "unsigned :obj:`int`",
    "G_TYPE_OBJECT": ":obj:`object`",
    "G_TYPE_PARAM": ":obj:`~gi.repository.GObject.ParamSpec`",
    "G_TYPE_BOXED": "``Boxed``",
    "G_TYPE_STRING": ":obj:`str`",
    "G_TYPE_FLOAT": ":obj:`float`",
    "G_TYPE_BOOLEAN": ":obj:`bool`",
    "G_TYPE_DOUBLE": ":obj:`float`",
    "G_TYPE_ENUM": "``Enum``",
    "G_TYPE_FLAGS": "``Flags``",
    "G_TYPE_GTYPE": "``GType``",
    "G_TYPE_INVALID": "``Invalid``",
}


def c_constants(lines, gir):
    if not gir:
        return lines

    def repl(m: re.Match[str]) -> str:
        g = m.group(1)
        if g in _python_consts:
            return _python_consts[g]
        if s := gir.c_const(g):
            return f":const:`~gi.repository.{s}`"
        return f"``%{g}``"

    return (re.sub(r"%(\w+)", repl, line) for line in lines)
