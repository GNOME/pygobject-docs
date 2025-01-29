"""Translate gtk-doc text to reStructuredText.

TODO:

- replace #\\w+ (type ref); #guint64 -> :obj:int
  else lookup Type.ctype or some field/member and provide official type
- replace \\w+() -> look up Callable.identifier in GIR repo and return official type
- convert tables to list-tables. https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table

See also https://gitlab.gnome.org/GNOME/gi-docgen/-/blob/main/gidocgen/utils.py

"""

import re
import textwrap
import xml.etree.ElementTree as etree

import markdown
import markdown.blockprocessors
import markdown.inlinepatterns


def rstify(text, gir, *, image_base_url=""):
    """Convert gtk-doc to rst."""
    if not text:
        return ""

    return GtkDocMarkdown(GtkDocExtension(gir, image_base_url), "fenced_code").convert(text)


def _to_rst(element: etree.Element):
    for n in range(0, len(element)):
        el = element[n]

        match el.tag:
            case "br":
                yield "\n\n"
            case "div":
                yield from _to_rst(el)
            case "param":
                yield f"``{el.attrib['name']}``"
            case "h1" | "h2" | "h3":
                yield el.text
                yield "\n"
                yield "-" * 20
                yield "\n"
            case "p":
                if el.text:
                    yield el.text
                yield from _to_rst(el)
                yield "\n"
            case "a":
                yield "`"
                if el.text:
                    yield el.text
                yield from _to_rst(el)
                yield f" <{el.attrib['href']}>`_"
            case "img":
                # yield f".. image:: {image_base_url}/{el.attrib['src']}"
                yield f".. image:: {el.attrib['src']}\n"
            case "blockquote":
                yield textwrap.indent(to_rst(el), "    ")
            case "pre":
                yield "\n.. code-block::\n    :dedent:\n"
                yield textwrap.indent(to_rst(el), "    ")
            case "code":
                yield "``"
                yield el.text
                yield "``"
            case "em":
                yield "*"
                yield el.text
                yield "*"
            case "strong":
                yield "**"
                yield el.text
                yield "**"
            case "li":
                yield "* "
                yield el.text
                yield from _to_rst(el)
            case "codeabbr" | "literal":
                yield f"``{el.text}``"
            case "span":
                if el.text:
                    yield el.text
                yield from _to_rst(el)
            case "ol":
                yield from _to_rst(el)
                yield "\n"
            case "ul":
                yield from _to_rst(el)
                yield "\n"
            case "const" | "func" | "ctype":
                if el.tag in el.attrib:
                    yield f":{el.tag}:`~{el.attrib[el.tag]}`"
                elif "raw" in el.attrib:
                    yield el.attrib["raw"]
                else:
                    yield el.text
            case "kbd":
                yield f":kbd:`{el.text}`"
            case "ref":
                yield f":obj:`~{el.attrib['type']}`"
            case _:
                raise ValueError(f"Unknown tag {etree.tostring(el).decode('utf-8')}")

        if el.tail:
            yield el.tail


def strip_none(iterable):
    for i in iterable:
        if i is not None:
            yield i


def to_rst(element):
    return "".join(strip_none(_to_rst(element)))


class GtkDocMarkdown(markdown.Markdown):
    markdown.Markdown.output_formats["rst"] = to_rst  # type: ignore[index]

    def __init__(self, *extensions, output_format="rst"):
        super().__init__(extensions=extensions, output_format=output_format)
        self.stripTopLevelTags = False

        self.inlinePatterns.deregister("html")
        self.postprocessors.deregister("amp_substitute")
        self.postprocessors.deregister("raw_html")


class GtkDocExtension(markdown.Extension):
    def __init__(self, gir, image_base_url):
        super().__init__()
        self.gir = gir
        self.image_base_url = image_base_url

    def extendMarkdown(self, md):
        # We want a space after the hash, so we can distinguish between a C type and a header
        markdown.blockprocessors.HashHeaderProcessor.RE = re.compile(
            r"(?:^|\n)(?P<level>#{1,6}) (?P<header>(?:\\.|[^\\])*?)#*(?:\n|$)"
        )

        LINK_RE = r"((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[\w+\.\?=#-]*)"  # link (`http://www.example.com`)
        md.inlinePatterns.register(
            markdown.inlinepatterns.AutolinkInlineProcessor(LINK_RE, md), "autolink2", 110
        )

        md.inlinePatterns.register(
            ReferenceProcessor(ReferenceProcessor.PATTERN, md, self.gir), ReferenceProcessor.TAG, 250
        )
        md.inlinePatterns.register(
            SignalOrPropertyProcessor(SignalOrPropertyProcessor.PROP_PATTERN, md, self.gir, "props"),
            SignalOrPropertyProcessor.PROP_TAG,
            250,
        )
        md.inlinePatterns.register(
            SignalOrPropertyProcessor(SignalOrPropertyProcessor.SIG_PATTERN, md, self.gir, "signals"),
            SignalOrPropertyProcessor.SIG_TAG,
            250,
        )
        md.inlinePatterns.register(KbdProcessor(KbdProcessor.PATTERN, md), KbdProcessor.TAG, 250)
        md.inlinePatterns.register(
            CConstantProcessor(CConstantProcessor.PATTERN, md, self.gir), CConstantProcessor.TAG, 250
        )
        md.inlinePatterns.register(
            DockbookNoteProcessor(DockbookNoteProcessor.PATTERN, md), DockbookNoteProcessor.TAG, 250
        )
        md.inlinePatterns.register(
            DockbookLiteralProcessor(DockbookLiteralProcessor.PATTERN, md), DockbookLiteralProcessor.TAG, 250
        )
        md.inlinePatterns.register(
            RemoveMarkdownTagsProcessor(RemoveMarkdownTagsProcessor.PATTERN, md),
            RemoveMarkdownTagsProcessor.TAG,
            250,
        )

        # Low prio parsers
        md.inlinePatterns.register(
            CSymbolProcessor(CSymbolProcessor.PATTERN, md, self.gir), CSymbolProcessor.TAG, 40
        )
        md.inlinePatterns.register(
            CTypeProcessor(CTypeProcessor.PATTERN, md, self.gir), CTypeProcessor.TAG, 40
        )
        md.inlinePatterns.register(
            ParameterProcessor(ParameterProcessor.PATTERN, md), ParameterProcessor.TAG, 40
        )
        md.inlinePatterns.register(
            CodeAbbreviationProcessor(CodeAbbreviationProcessor.PATTERN, md),
            CodeAbbreviationProcessor.TAG,
            40,
        )


class ReferenceProcessor(markdown.inlinepatterns.InlineProcessor):
    """[class@Widget.Foo] -> :class:`Widget.Foo`"""

    PATTERN = r"\[(?:ctor|class|const|enum|error|flags|func|id|iface|method|struct|type|vfunc)@(.+)\]"
    TAG = "ref"

    def __init__(self, pattern, md, gir):
        super().__init__(pattern, md)
        self.namespace = gir.namespace[0]

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG)
        package = "gi.repository" if "." in m.group(1) else f"gi.repository.{self.namespace}"
        el.attrib["type"] = f"{package}.{m.group(1)}"

        return el, m.start(0), m.end(0)


class SignalOrPropertyProcessor(markdown.inlinepatterns.InlineProcessor):
    """[signal@Widget::sig] -> :obj:`Widget.signals.sig`"""

    PROP_PATTERN = r"\[property@([^:]+?):(.+?)\]"
    SIG_PATTERN = r"\[signal@([^:]+?)::(.+?)\]"
    PROP_TAG = "propref"
    SIG_TAG = "sigref"

    def __init__(self, pattern, md, gir, section):
        super().__init__(pattern, md)
        self.namespace = gir.namespace[0]
        self.section = section

    def handleMatch(self, m, data):
        el = etree.Element("ref")
        package = "gi.repository" if "." in m.group(1) else f"gi.repository.{self.namespace}"
        el.attrib["type"] = f"{package}.{m.group(1)}.{self.section}.{m.group(2).replace('-', '_')}"

        return el, m.start(0), m.end(0)


# (re.compile(r"\[`*(?:alias|callback)@(.+?)`*\]"), r"``\1``"),


class ParameterProcessor(markdown.inlinepatterns.InlineProcessor):
    """@parameter -> ``parameter``"""

    PATTERN = r"@(\w+)"
    TAG = "param"

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG, {"name": m.group(1)})
        return el, m.start(0), m.end(0)


class KbdProcessor(markdown.inlinepatterns.InlineProcessor):
    """<kbd>F1</kbd> -> :kbd:`F1`"""

    PATTERN = r"<kbd>([\w ]+|[↑→↓←]?)</kbd>"
    TAG = "kbd"

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG)
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


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
    "gboolean": ":obj:`bool`",
    "gchar*": ":obj:`str`",
    "gchar**": ":obj:`list[str]`",
    "gdouble": ":obj:`float`",
    "gint": ":obj:`int`",
    "guint": "unsigned :obj:`int`",
}


class CConstantProcessor(markdown.inlinepatterns.InlineProcessor):
    """%TRUE -> :const:`True`"""

    PATTERN = r"%([\w\*]+)"
    TAG = "const"

    def __init__(self, pattern, md, gir):
        super().__init__(pattern, md)
        self.gir = gir

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG)
        g = m.group(1)
        if g in _python_consts:
            el.attrib["raw"] = _python_consts[g]
        elif s := self.gir.c_const(g):
            el.attrib["const"] = f"gi.repository.{s}"
        else:
            el.attrib["raw"] = f"``{g}``"

        return el, m.start(0), m.end(0)


class CSymbolProcessor(markdown.inlinepatterns.InlineProcessor):
    """func_name() -> :func:`namespace.func_name`"""

    PATTERN = r"(\w+)\(\)"
    TAG = "func"

    def __init__(self, pattern, md, gir):
        super().__init__(pattern, md)
        self.gir = gir

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG)
        g = m.group(1)
        el.text = f"{g}()"
        if s := self.gir.c_symbol(g):
            el.attrib["func"] = f"gi.repository.{s}"

        return el, m.start(0), m.end(0)


class CTypeProcessor(markdown.inlinepatterns.InlineProcessor):
    """#guint -> :obj:`int`"""

    PATTERN = r"#(\w+)"
    TAG = "ctype"

    def __init__(self, pattern, md, gir):
        super().__init__(pattern, md)
        self.gir = gir

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG)
        g = m.group(1)
        if g.startswith("gint") or g.startswith("guint"):
            el.text = ":obj:`int`"
        elif g == "gdouble":
            el.text = ":obj:`float`"
        elif t := self.gir.c_type(g):
            el = etree.Element("ref", {"type": f"gi.repository.{t}"})
        else:
            el.text = f"``{g}``"

        return el, m.start(0), m.end(0)


class CodeAbbreviationProcessor(markdown.inlinepatterns.InlineProcessor):
    """func_name_ -> ``func_name_``"""

    PATTERN = r"(?:(?<!\w)|^)(\w+_[\.]*)(?!\w)"
    TAG = "codeabbr"

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG)
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


class DockbookNoteProcessor(markdown.inlinepatterns.InlineProcessor):
    PATTERN = r"<note>([\w ]+)</note>"
    TAG = "note"

    def handleMatch(self, m, data):
        el = etree.Element("span")
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


class DockbookLiteralProcessor(markdown.inlinepatterns.InlineProcessor):
    PATTERN = r"<literal>([\w ]+)</literal>"
    TAG = "literal"

    def handleMatch(self, m, data):
        el = etree.Element(self.TAG)
        el.text = m.group(1)
        return el, m.start(0), m.end(0)


class RemoveMarkdownTagsProcessor(markdown.inlinepatterns.InlineProcessor):
    PATTERN = r" *# +\{#[\w-]+\}$"
    TAG = "md_tags"

    def handleMatch(self, m, data):
        el = etree.Element("span")
        el.text = ""
        return el, m.start(0), m.end(0)


def pipe(obj, *filters):
    for f in filters:
        obj = f(obj)
    return obj


def s_after_inline_code(lines):
    return (re.sub(r"(?<=`)s(?=\W|$)", r"'s", line) for line in lines)


def markdown_images(lines, image_url):
    return (re.sub(r" *!\[.*?\]\((.+?)\)", f"\n.. image:: {image_url}/\\1\n", line) for line in lines)


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
        if not in_code and line.lstrip().startswith("```"):
            lang = line.lstrip()[3:]
            yield f"\n.. code-block:: {lang}\n   :dedent:\n"
            in_code = "md"
        elif not in_code and re.search(r"^ *\|\[", line):
            yield re.sub(
                r' *\|\[ *(<!-- *language="(\w+)" *-->)?', r"\n.. code-block:: \2\n   :dedent:\n", line
            )
            in_code = "gtk-doc"
        elif in_code == "md" and line.lstrip() == "```":
            yield ""
            in_code = False
        elif in_code == "gtk-doc" and re.search(r"^ *\]\|", line):
            yield ""
            in_code = False
        elif in_code:
            yield f"   {line}"
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
            yield f".. image:: {image_url}/{path}" if image_url else ".. error:: No image URL not available. Please `raise an issue <https://gitlab.gnome.org/amolenaar/pygobject-docs/-/issues>`_."
        elif not picture:
            yield line
