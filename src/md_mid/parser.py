"""markdown-it-py 解析器：Markdown → EAST 节点树。

使用 commonmark preset + html + table + dollarmath + footnote 插件，
将 token stream 折叠为 SyntaxTreeNode 后递归转换为 EAST 节点。
"""

from __future__ import annotations

from collections.abc import Callable

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin

from md_mid.diagnostic import DiagCollector
from md_mid.nodes import (
    Blockquote,
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    Emphasis,
    FootnoteDef,
    FootnoteRef,
    HardBreak,
    Heading,
    Image,
    Link,
    List,
    ListItem,
    MathBlock,
    MathInline,
    Node,
    Paragraph,
    RawBlock,
    SoftBreak,
    Strong,
    Table,
    Text,
    ThematicBreak,
)


def _create_md() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    dollarmath_plugin(md)
    footnote_plugin(md)
    return md


_md = _create_md()

# 合法的引用命令集（Valid citation commands per PRD）
VALID_CITE_CMDS = frozenset(
    {
        "cite",
        "citep",
        "citet",
        "citeauthor",
        "citeyear",
        "textcite",
        "parencite",
        "autocite",
    }
)


def parse(text: str, *, diag: DiagCollector | None = None) -> Document:
    """解析 Markdown 文本，返回 EAST Document 节点。

    Parse Markdown text and return an EAST Document node.

    Args:
        text: Markdown source text (Markdown 源文本)
        diag: Optional diagnostic collector for validation warnings (可选诊断收集器)

    Returns:
        EAST Document node (EAST 文档节点)
    """
    tokens = _md.parse(text)
    tree = SyntaxTreeNode(tokens)
    children = _build_children(tree)
    doc = Document(children=children)
    if diag is not None:
        _validate_citations(doc, diag)
    return doc


def _validate_citations(node: Node, diag: DiagCollector) -> None:
    """验证引用节点的合法性（Validate citation node validity）.

    递归遍历树（Recursively traverses the tree）.
    """
    if isinstance(node, Citation):
        # 检查空键（Check for empty citation keys）
        if any(not k for k in node.keys):
            diag.warning(
                "Empty citation key in citation",
            )
        # 检查未知命令（Check for unknown citation command）
        if node.cmd not in VALID_CITE_CMDS:
            valid = ", ".join(sorted(VALID_CITE_CMDS))
            diag.warning(
                f"Unknown citation command '{node.cmd}', valid: {valid}",
            )
    for child in node.children:
        _validate_citations(child, diag)


def _build_children(node: SyntaxTreeNode) -> list[Node]:
    """递归构建子节点列表。"""
    result: list[Node] = []
    for child in node.children:
        built = _build_node(child)
        if built is not None:
            if isinstance(built, list):
                result.extend(built)
            else:
                result.append(built)
    return result


def _build_node(node: SyntaxTreeNode) -> Node | list[Node] | None:
    """将 SyntaxTreeNode 转换为 EAST Node。"""
    ntype = node.type

    # inline 中间节点：提升其子节点
    if ntype == "inline":
        return _build_children(node)

    builder = _NODE_MAP.get(ntype)
    if builder is not None:
        return builder(node)

    # 未知节点类型：尝试递归处理子节点
    children = _build_children(node)
    if children:
        return children
    return None


def _position_from_map(node: SyntaxTreeNode) -> dict[str, object] | None:
    m = node.map
    if m is None:
        return None
    return {"start": {"line": m[0] + 1, "column": 1}, "end": {"line": m[1], "column": 1}}


# -- 块级构建器 --------------------------------------------------------------


def _build_heading(node: SyntaxTreeNode) -> Heading:
    level = int(node.tag[1:])  # h1 → 1, h2 → 2, ...
    children = _build_children(node)
    return Heading(level=level, children=children, position=_position_from_map(node))


def _build_paragraph(node: SyntaxTreeNode) -> Paragraph:
    children = _build_children(node)
    return Paragraph(children=children, position=_position_from_map(node))


def _build_blockquote(node: SyntaxTreeNode) -> Blockquote:
    children = _build_children(node)
    return Blockquote(children=children, position=_position_from_map(node))


def _build_list(node: SyntaxTreeNode, ordered: bool) -> List:
    children = _build_children(node)
    start = 1
    if ordered and node.attrs:
        start = int(node.attrs.get("start", 1))
    return List(ordered=ordered, start=start, children=children, position=_position_from_map(node))


def _build_list_item(node: SyntaxTreeNode) -> ListItem:
    children = _build_children(node)
    return ListItem(children=children, position=_position_from_map(node))


def _build_code_block(node: SyntaxTreeNode) -> CodeBlock:
    content = node.content or ""
    language = (node.info or "").strip()
    return CodeBlock(
        content=content.rstrip("\n"), language=language, position=_position_from_map(node)
    )


def _build_math_block(node: SyntaxTreeNode) -> MathBlock:
    content = (node.content or "").strip()
    return MathBlock(content=content, position=_position_from_map(node))


def _build_html_block(node: SyntaxTreeNode) -> RawBlock:
    content = (node.content or "").strip()
    return RawBlock(content=content, position=_position_from_map(node))


def _build_table(node: SyntaxTreeNode) -> Table:
    headers: list[list[Node]] = []
    alignments: list[str] = []
    rows: list[list[list[Node]]] = []

    for section in node.children:
        if section.type == "thead":
            for tr in section.children:
                for cell in tr.children:
                    # 构建行内节点列表 (Build inline node list for cell)
                    cell_nodes = _build_children(cell)
                    headers.append(cell_nodes)
                    # 对齐信息不变 (Alignment extraction unchanged)
                    style: str = str(cell.attrGet("style") or "")
                    if "left" in style:
                        alignments.append("left")
                    elif "right" in style:
                        alignments.append("right")
                    elif "center" in style:
                        alignments.append("center")
                    else:
                        alignments.append("left")
        elif section.type == "tbody":
            for tr in section.children:
                row: list[list[Node]] = []
                for cell in tr.children:
                    row.append(_build_children(cell))
                rows.append(row)

    return Table(
        headers=headers, alignments=alignments, rows=rows, position=_position_from_map(node)
    )


def _build_hr(node: SyntaxTreeNode) -> ThematicBreak:
    return ThematicBreak(position=_position_from_map(node))


# -- 行内构建器 --------------------------------------------------------------


def _build_text(node: SyntaxTreeNode) -> Text:
    return Text(content=node.content or "")


def _build_code_inline(node: SyntaxTreeNode) -> CodeInline:
    return CodeInline(content=node.content or "")


def _build_math_inline(node: SyntaxTreeNode) -> MathInline:
    return MathInline(content=node.content or "")


def _build_softbreak(node: SyntaxTreeNode) -> SoftBreak:
    return SoftBreak()


def _build_hardbreak(node: SyntaxTreeNode) -> HardBreak:
    return HardBreak()


def _build_emphasis(node: SyntaxTreeNode) -> Emphasis:
    children = _build_children(node)
    return Emphasis(children=children)


def _build_strong(node: SyntaxTreeNode) -> Strong:
    children = _build_children(node)
    return Strong(children=children)


def _build_link(node: SyntaxTreeNode) -> Node:
    # attrGet 可能返回非字符串类型，统一转换为 str（attrGet may return non-str, cast to str）
    url: str = str(node.attrGet("href") or "")
    children = _build_children(node)
    display_text = _extract_text_from_nodes(children)

    if url.startswith("cite:"):
        raw = url[5:]
        cmd = "cite"
        if "?cmd=" in raw:
            raw, cmd = raw.split("?cmd=", 1)
        # 过滤空键（Filter empty keys from comma-separated list）
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        return Citation(keys=keys, display_text=display_text, cmd=cmd)

    if url.startswith("ref:"):
        label = url[4:]
        return CrossRef(label=label, display_text=display_text)

    title: str = str(node.attrGet("title") or "")
    return Link(url=url, title=title, children=children)


def _build_image(node: SyntaxTreeNode) -> Image:
    # attrGet 可能返回非字符串类型，统一转换为 str（attrGet may return non-str, cast to str）
    src: str = str(node.attrGet("src") or "")
    alt: str = str(node.attrGet("alt") or node.content or "")
    title: str = str(node.attrGet("title") or "")
    return Image(src=src, alt=alt, title=title)


def _build_html_inline(node: SyntaxTreeNode) -> RawBlock:
    content = (node.content or "").strip()
    return RawBlock(content=content)


def _build_footnote_ref(node: SyntaxTreeNode) -> FootnoteRef:
    ref_id = str(node.meta.get("id", "")) if node.meta else ""
    return FootnoteRef(ref_id=ref_id)


def _build_footnote_block(node: SyntaxTreeNode) -> list[Node]:
    result: list[Node] = []
    for child in node.children:
        if child.type == "footnote":
            def_id = str(child.meta.get("id", "")) if child.meta else ""
            children = _build_children(child)
            result.append(FootnoteDef(def_id=def_id, children=children))
    return result


# -- 辅助函数 ----------------------------------------------------------------


def _extract_text_from_tree(node: SyntaxTreeNode) -> str:
    """从 SyntaxTreeNode 中提取纯文本。"""
    if node.content:
        return node.content
    parts: list[str] = []
    for child in node.children:
        parts.append(_extract_text_from_tree(child))
    return "".join(parts)


def _extract_text_from_nodes(nodes: list[Node]) -> str:
    """从 EAST 节点列表中提取纯文本。"""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text):
            parts.append(node.content)
        elif hasattr(node, "children"):
            parts.append(_extract_text_from_nodes(node.children))
    return "".join(parts)


# -- 映射表 ------------------------------------------------------------------

# 节点构建器函数类型别名（Node builder function type alias）
_BuilderFn = Callable[[SyntaxTreeNode], Node | list[Node] | None]

_NODE_MAP: dict[str, _BuilderFn] = {
    # 块级
    "heading": _build_heading,
    "paragraph": _build_paragraph,
    "blockquote": _build_blockquote,
    "bullet_list": lambda n: _build_list(n, ordered=False),
    "ordered_list": lambda n: _build_list(n, ordered=True),
    "list_item": _build_list_item,
    "fence": _build_code_block,
    "code_block": _build_code_block,
    "math_block": _build_math_block,
    "math_block_eqno": _build_math_block,
    "hr": _build_hr,
    "html_block": _build_html_block,
    "table": _build_table,
    # 行内
    "text": _build_text,
    "code_inline": _build_code_inline,
    "math_inline": _build_math_inline,
    "softbreak": _build_softbreak,
    "hardbreak": _build_hardbreak,
    "em": _build_emphasis,
    "strong": _build_strong,
    "link": _build_link,
    "image": _build_image,
    "html_inline": _build_html_inline,
    "footnote_ref": _build_footnote_ref,
    "footnote_block": _build_footnote_block,
}
