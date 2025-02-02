"""Translate gtk-doc text to reStructuredText.

TODO:

- replace #\\w+ (type ref); #guint64 -> :obj:int
  else lookup Type.ctype or some field/member and provide official type
- replace \\w+() -> look up Callable.identifier in GIR repo and return official type
- convert tables to list-tables. https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table

See also https://gitlab.gnome.org/GNOME/gi-docgen/-/blob/main/gidocgen/utils.py

"""

import logging
import re
import textwrap
import typing
import xml.etree.ElementTree as etree
from functools import partial

import markdown
import markdown.blockprocessors
import markdown.inlinepatterns
import markdown.preprocessors
import markdown.util

log = logging.getLogger(__name__)


def rstify(text, gir, *, image_base_url=""):
    """Convert gtk-doc to rst."""
    if not text:
        return ""

    return GtkDocMarkdown(partial(to_rst, image_base_url=image_base_url), GtkDocExtension(gir)).convert(text)


def strip_none(iterable):
    for i in iterable:
        if i is not None:
            yield i


def to_rst(element, image_base_url):
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
                    yield f".. image:: {image_base_url}/{el.attrib['src']}\n"
                case "blockquote":
                    yield textwrap.indent(to_rst(el, image_base_url), "    ")
                case "pre":
                    if lang := el.attrib.get("language", ""):
                        yield f"\n.. code-block:: {lang}\n    :dedent:\n"
                    else:
                        yield "\n.. code-block::\n    :dedent:\n"
                    for t in el.itertext():
                        yield textwrap.indent(t, "    ")
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

    return "".join(strip_none(_to_rst(element)))


class GtkDocMarkdown(markdown.Markdown):
    def __init__(self, serializer, *extensions):
        super().__init__(extensions=extensions)
        self.stripTopLevelTags = False
        self.inlinePatterns.deregister("html")
        self.postprocessors.deregister("amp_substitute")
        self.postprocessors.deregister("raw_html")

        self.serializer = serializer

    def set_output_format(self, _format: str) -> typing.Self:
        # Do nothing, we have a custom serializer
        return self


class GtkDocExtension(markdown.Extension):
    def __init__(self, gir):
        super().__init__()
        self.gir = gir

    def extendMarkdown(self, md):
        # Ensure code blocks start with a blank line
        md.preprocessors.register(CodeBlockPreprocessor(md), "pre_code_block", 50)

        # We want a space after the hash, so we can distinguish between a C type and a header
        markdown.blockprocessors.HashHeaderProcessor.RE = re.compile(
            r"(?:^|\n)(?P<level>#{1,6}) (?P<header>(?:\\.|[^\\])*?)#*(?:\n|$)"
        )
        md.parser.blockprocessors.register(CodeBlockProcessor(md.parser), "code_block", 120)
        md.parser.blockprocessors.register(PictureProcessor(md.parser), "picture", 80)

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


class PictureProcessor(markdown.blockprocessors.BlockProcessor):
    RE = re.compile(r"^[ \t]*\<picture\>.*?\<\/picture\>", re.MULTILINE | re.DOTALL)

    def test(self, parent: etree.Element, block: str) -> bool:
        return bool(self.RE.search(block))

    def run(self, parent: etree.Element, blocks: list[str]) -> bool | None:
        text = ""
        while "</picture>" not in text:
            text += blocks.pop(0)

        path = re.sub(r'^.* src="([^"]+)".*$', r"\1", text, flags=re.DOTALL)

        e = etree.SubElement(parent, "img", {"src": path})
        e.tail = "\n"

        return True


class CodeBlockPreprocessor(markdown.preprocessors.Preprocessor):
    def run(self, lines: list[str]) -> list[str]:
        def insert_blank_lines_before_code_blocks(lines):
            for line in lines:
                if line.strip().startswith("```") or line.strip().startswith("|["):
                    yield ""
                yield line

        a = list(insert_blank_lines_before_code_blocks(lines))
        return a


class CodeBlockProcessor(markdown.blockprocessors.BlockProcessor):
    def test(self, _parent: etree.Element, block: str) -> bool:
        return block.strip().startswith("```") or block.strip().startswith("|[")

    def run(self, parent: etree.Element, blocks: list[str]) -> bool | None:
        code_block = []
        lang = ""
        in_code = ""
        while 1:
            block = blocks.pop(0)
            if not in_code and block.lstrip().startswith("```"):
                lines = block.lstrip().split("\n")
                lang = lines[0].lstrip()[3:]
                code_block.extend(lines[1:])
                in_code = "md"
            elif not in_code and block.lstrip().startswith("|["):
                lines = block.lstrip().split("\n")
                lang = re.sub(r' *\|\[ *(<!-- *language="(\w+)" *-->)?', r"\2", lines[0])
                code_block.extend(lines[1:])
                in_code = "gtk-doc"
            elif in_code == "md" and block.rstrip().endswith("```"):
                code_block.append(block.rstrip()[:-3])
                break
            elif in_code == "gtk-doc" and block.rstrip().endswith("]|"):
                code_block.append(block.rstrip()[:-2])
                break
            elif in_code:
                code_block.append(block)
            else:
                raise ValueError("Cannot find a code block in {line}")

            # Add extra newline after every block
            code_block.append("")

        pre = etree.SubElement(parent, "pre", {"language": lang})
        code = etree.SubElement(pre, "code")
        code.text = markdown.util.AtomicString("\n".join(code_block))
        pre.tail = "\n"

        return True


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
