"""EAST (Enhanced AST) 节点类型定义。

所有节点均为 dataclass，字段说明见 PRD S11。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass
class Node:
    """所有 EAST 节点的基类。"""

    children: list[Node] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    position: dict[str, object] | None = None  # {"start": {"line":, "column":}, "end": ...}

    @property
    def type(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> dict[str, object]:
        """序列化节点为可 JSON 化的字典（Serialize node to JSON-serializable dict）.

        使用 dataclasses.fields() 自动包含所有字段（Uses dataclasses.fields()）.
        """
        result: dict[str, object] = {"type": self.type}
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if f.name == "children":
                if val:
                    result["children"] = [c.to_dict() for c in val]
            elif f.name == "metadata":
                if val:
                    result["metadata"] = val
            elif f.name == "position":
                if val is not None:
                    result["position"] = val
            else:
                # 额外字段如 content、level、name 等（Extra fields: content, level, name, etc.）
                result[f.name] = val
        return result


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


# 表格单元格类型别名 (Table cell type aliases for readability)
CellContent = list["Node"]  # 单元格内容：行内节点列表 (Cell: list of inline nodes)
TableRow = list[CellContent]  # 表格行：单元格列表 (Row: list of cells)


@dataclass
class Table(Node):
    headers: list[CellContent] = field(default_factory=list)
    alignments: list[str] = field(default_factory=list)
    rows: list[TableRow] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "table"

    def to_dict(self) -> dict[str, object]:
        """Serialize table with inline node cells (序列化含行内节点的表格单元格)."""
        result: dict[str, object] = {"type": self.type}
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        if self.metadata:
            result["metadata"] = self.metadata
        if self.position is not None:
            result["position"] = self.position
        result["headers"] = [
            [n.to_dict() for n in cell] for cell in self.headers
        ]
        result["alignments"] = self.alignments
        result["rows"] = [
            [[n.to_dict() for n in cell] for cell in row]
            for row in self.rows
        ]
        return result


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
