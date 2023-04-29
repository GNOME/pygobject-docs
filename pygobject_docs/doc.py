"""Translate gtk-doc text to reStructuredText.

TODO:

- replace #\\w+ (type ref); #guint64 -> :obj:int
  else lookup Type.ctype or some field/member and provide official type
- replace \\w+() -> look up Callable.identifier in GIR repo and return official type
- convert tables to list-tables. https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table

See also https://gitlab.gnome.org/GNOME/gi-docgen/-/blob/main/gidocgen/utils.py

"""

from functools import partial
import re


def rstify(text, image_base_url=""):
    """Convert gtk-doc to rst."""
    if not text:
        return ""

    lines = text.splitlines(keepends=False)

    return pipe(
        lines,
        code_snippets,
        tags,
        constants,
        whitespace_before_lists,
        partial(markdown_images, image_url=image_base_url),
        gtk_doc_link,
        parameters,  # after gtk-doc links, since those also contain `@` symbols
        markdown_inline_code,
        markdown_links,
        s_after_inline_code,
        markdown_heading,
        "\n".join,
    )


def pipe(obj, *filters):
    for f in filters:
        obj = f(obj)
    return obj


def markdown_inline_code(lines):
    return (re.sub(r"(?:(?<![:`])|^)`([^` ]+?)`(?=[^`]|$)", r"``\1``", line) for line in lines)


def s_after_inline_code(lines):
    return (re.sub(r"(?<=`)s(?=\W|$)", r"'s", line) for line in lines)


def parameters(lines):
    return (re.sub(r"@(\w+)", r"``\1``", line) for line in lines)


def constants(lines):
    return (
        line.replace("%TRUE", ":const:`True`")
        .replace("%FALSE", ":const:`False`")
        .replace("%NULL", ":const:`None`")
        for line in lines
    )


def markdown_images(lines, image_url):
    return (re.sub(r" *!\[.*?\]\((.+?)\)", f"\n.. image:: {image_url}/\\1\n", line) for line in lines)


def markdown_links(lines):
    return (re.sub(r"\[(.+?)\]\((.+?)\)", r"`\1 <\2>`_", line) for line in lines)


def markdown_heading(lines):
    for line in lines:
        if re.search(r"^#+ ", line):
            h = line.split(" ", 1)[1]
            yield h
            yield "~" * len(h)
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


def gtk_doc_link(lines):
    tmp = (
        re.sub(
            r"\[`*(?:ctor|class|const|enum|flags|func|id|iface|method|property|signal|struct|vfunc)@(.+?)`*\]",
            r":obj:`~gi.repository.\1`",
            line,
        )
        for line in lines
    )
    return (
        re.sub(
            r"\[`*(?:alias|callback|error|type)@(.+?)`*\]",
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
