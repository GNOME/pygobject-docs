import re


def rstify(text):
    """Convert gtk-doc to rst."""
    if not text:
        return ""

    lines = text.splitlines(keepends=False)

    return pipe(
        lines, inline_code, constants, markdown_images, markdown_links, code_snippets, gtk_doc_link, "\n".join
    )


def pipe(obj, *filters):
    for f in filters:
        obj = f(obj)
    return obj


def inline_code(lines):
    return (re.sub(r"`", r"``", line) for line in lines)


def constants(lines):
    return (
        line.replace("%TRUE", ":const:`True`")
        .replace("%FALSE", ":const:`False`")
        .replace("%NULL", ":const:`None`")
        for line in lines
    )


def markdown_images(lines):
    return (re.sub(r" *!\[\]\((.*?)\)", r"\n..image:: https://doc.gtk.org/glib/\1\n", line) for line in lines)


def markdown_links(lines):
    return (re.sub(r"\[(.*?)\]\((.*?)\)", r"`\1 <\2>`_", line) for line in lines)


def code_snippets(lines):
    in_code = False
    indent = -1
    for line in lines:
        if re.search(r"^ *\|\[", line):
            yield re.sub(r' *\|\[ *(<!-- *language="(\w+)" *-->)?', r"\n.. code-block:: \2\n", line)
            in_code = True
        elif in_code and re.search(r"^ *\]\|", line):
            yield ""
            in_code = False
            indent = -1
        elif in_code:
            if indent == -1:
                if line.startswith("  "):
                    indent = 1
                else:
                    indent = 3
            yield f"{' ' * indent}{line}"
        else:
            yield line


def gtk_doc_link(lines):
    return (re.sub(r"\[(?:class|method)@(.*?)\]", r":obj:`~gi.repository.\1`", line) for line in lines)


# See also https://gitlab.gnome.org/GNOME/gi-docgen/-/blob/main/gidocgen/utils.py
# replace @\w+
# replace #\w+ (type ref); #guint64 -> :obj:int
# replace \w+()
