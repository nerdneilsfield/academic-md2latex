"""EAST (Enhanced AST) 节点类型定义。

所有节点均为 dataclass，字段说明见 PRD S11。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """所有 EAST 节点的基类。"""

    children: list[Node] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    position: dict | None = None  # {"start": {"line":, "column":}, "end": ...}

    @property
    def type(self) -> str:
        raise NotImplementedError


# -- 块级节点 ---------------------------------------------------------------

@dataclass
class Document(Node):
    @property
    def type(self) -> str:
        return "document"


@dataclass
class Heading(Node):
    level: int = 1

    @property
    def type(self) -> str:
        return "heading"


@dataclass
class Paragraph(Node):
    @property
    def type(self) -> str:
        return "paragraph"


@dataclass
class Blockquote(Node):
    @property
    def type(self) -> str:
        return "blockquote"


@dataclass
class List(Node):
    ordered: bool = False
    start: int = 1

    @property
    def type(self) -> str:
        return "list"


@dataclass
class ListItem(Node):
    @property
    def type(self) -> str:
        return "list_item"


@dataclass
class CodeBlock(Node):
    content: str = ""
    language: str = ""

    @property
    def type(self) -> str:
        return "code_block"


@dataclass
class MathBlock(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "math_block"


@dataclass
class Figure(Node):
    src: str = ""
    alt: str = ""

    @property
    def type(self) -> str:
        return "figure"


@dataclass
class Table(Node):
    headers: list[str] = field(default_factory=list)
    alignments: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "table"


@dataclass
class Environment(Node):
    name: str = ""

    @property
    def type(self) -> str:
        return "environment"


@dataclass
class RawBlock(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "raw_block"


@dataclass
class ThematicBreak(Node):
    @property
    def type(self) -> str:
        return "thematic_break"


# -- 行内节点 ---------------------------------------------------------------

@dataclass
class Text(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "text"


@dataclass
class Strong(Node):
    @property
    def type(self) -> str:
        return "strong"


@dataclass
class Emphasis(Node):
    @property
    def type(self) -> str:
        return "emphasis"


@dataclass
class CodeInline(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "code_inline"


@dataclass
class MathInline(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "math_inline"


@dataclass
class Link(Node):
    url: str = ""
    title: str = ""

    @property
    def type(self) -> str:
        return "link"


@dataclass
class Image(Node):
    src: str = ""
    alt: str = ""
    title: str = ""

    @property
    def type(self) -> str:
        return "image"


@dataclass
class Citation(Node):
    keys: list[str] = field(default_factory=list)
    display_text: str = ""
    cmd: str = "cite"

    @property
    def type(self) -> str:
        return "citation"


@dataclass
class CrossRef(Node):
    label: str = ""
    display_text: str = ""

    @property
    def type(self) -> str:
        return "cross_ref"


@dataclass
class FootnoteRef(Node):
    ref_id: str = ""

    @property
    def type(self) -> str:
        return "footnote_ref"


@dataclass
class FootnoteDef(Node):
    def_id: str = ""

    @property
    def type(self) -> str:
        return "footnote_def"


@dataclass
class SoftBreak(Node):
    @property
    def type(self) -> str:
        return "softbreak"


@dataclass
class HardBreak(Node):
    @property
    def type(self) -> str:
        return "hardbreak"
