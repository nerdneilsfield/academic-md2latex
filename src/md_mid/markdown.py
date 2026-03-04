"""Rich Markdown Renderer: EAST → GitHub/Obsidian/Typora-compatible Markdown.

两次扫描架构 (Two-pass architecture):
  Pass 1 (Index): 预扫描，收集引用键 (Pre-scan to collect cite keys)
  Pass 2 (Render): 使用索引数据渲染 (Render using index data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from md_mid.diagnostic import DiagCollector, Position
from md_mid.markdown_blocks import MarkdownBlockMixin, _esc
from md_mid.nodes import (
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    FootnoteDef,
    FootnoteRef,
    Heading,
    Image,
    Link,
    List,
    MathBlock,
    MathInline,
    Node,
    Paragraph,
    RawBlock,
    Text,
)


def _yaml_safe_scalar(val: str) -> str:
    """Wrap YAML scalar in quotes if it contains unsafe characters (按需引号包裹 YAML 标量).

    Args:
        val: Raw scalar value (原始标量值)

    Returns:
        Quoted string if needed, else val unchanged (需要时返回引号包裹的字符串)
    """
    # Characters that make a bare YAML scalar ambiguous (使裸标量产生歧义的字符)
    UNSAFE = ("#", "[", "{", "!", "&", "*", "?", "|", ">", "'", '"')
    if any(val.startswith(c) for c in UNSAFE) or ":" in val:
        escaped = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return val


@dataclass
class MarkdownIndex:
    """Pass 1 收集结果 (Pass 1 results)."""

    # 按出现顺序排列的唯一引用键 (ordered unique citation keys)
    cite_keys: list[str] = field(default_factory=list)
    # O(1) 去重用集合 (O(1) dedup set for cite_keys)
    _cite_key_set: set[str] = field(default_factory=set)


# 标签本地化 (Label localization)
_LABEL_STRINGS: dict[str, dict[str, str]] = {
    "zh": {"figure": "图", "table": "表"},
    "en": {"figure": "Figure", "table": "Table"},
}


class MarkdownRenderer(MarkdownBlockMixin):
    """EAST → Rich Markdown 渲染器 (EAST to Rich Markdown renderer)."""

    def __init__(
        self,
        bib: dict[str, str] | None = None,
        heading_id_style: str = "attr",
        locale: str = "zh",
        mode: str = "full",
        diag: DiagCollector | None = None,
    ) -> None:
        """初始化渲染器 (Initialize renderer).

        Args:
            bib: BibTeX key → formatted citation string
                 (BibTeX 键 → 格式化引用字符串)
            heading_id_style: Anchor style for headings:
                'attr' ({#id}) or 'html' (<hN id=...>)
                (标题锚点风格)
            locale: Label language: 'zh' or 'en' (标签语言)
            mode: Output mode: 'full', 'body', or 'fragment'
                  (输出模式：full 含前言和脚注，body 无前言但有脚注，fragment 纯正文)
            diag: Optional diagnostic collector (可选诊断收集器)
        """
        self._bib = bib or {}
        self._heading_id_style = heading_id_style
        self._locale = locale
        self._mode = mode
        self._labels = _LABEL_STRINGS.get(locale, _LABEL_STRINGS["zh"])
        self._diag = diag or DiagCollector("unknown")
        self._index: MarkdownIndex = MarkdownIndex()
        self._fig_count: int = 0  # 图计数器 (figure counter)
        self._tab_count: int = 0  # 表计数器 (table counter)
        self._list_depth: int = 0  # 列表嵌套深度 (list nesting depth)
        self._native_fn_defs: dict[str, str] = {}  # native footnote defs (原生脚注定义)

    def render(self, doc: Document) -> str:
        """渲染文档为 Rich Markdown (Render document to Rich Markdown).

        Args:
            doc: EAST Document node (EAST 文档节点)

        Returns:
            Rich Markdown string (Rich Markdown 字符串)
        """
        # 重置计数器和状态 (Reset counters and state for fresh render)
        self._fig_count = 0
        self._tab_count = 0
        self._list_depth = 0
        self._native_fn_defs = {}  # 清除上次渲染残留脚注 (Clear stale footnote defs)

        # Pass 1: 收集引用键 (Collect citation keys)
        self._index = self._build_index(doc)

        # Pass 2: 渲染 (Render)
        parts: list[str] = []

        # full 模式才输出前言 (Only full mode renders front matter)
        if self._mode == "full":
            front_matter = self._render_front_matter(doc)
            if front_matter:
                parts.append(front_matter)

        body = self._render_children(doc)
        parts.append(body)

        # full 和 body 模式输出脚注 (full and body modes render footnotes)
        if self._mode in ("full", "body"):
            footnotes = self._render_footnotes()
            if footnotes:
                parts.append(footnotes)

        return "\n".join(p for p in parts if p)

    # ── Pass 1: Index ────────────────────────────────────────────

    def _build_index(self, root: Node) -> MarkdownIndex:
        """构建索引 (Build index from tree walk)."""
        index = MarkdownIndex()
        self._index_node(root, index)
        return index

    def _index_node(self, node: Node, index: MarkdownIndex) -> None:
        """递归收集引用键 (Recursively collect citation keys)."""
        if isinstance(node, Citation):
            for key in node.keys:
                if key not in index._cite_key_set:
                    index._cite_key_set.add(key)
                    index.cite_keys.append(key)
        for child in node.children:
            self._index_node(child, index)

    # ── Pass 2: Render helpers ───────────────────────────────────

    def _dispatch(self, node: Node) -> str:
        """分发到对应渲染方法 (Dispatch to render method)."""
        method_name = f"_render_{node.type}"
        method = getattr(self, method_name, None)
        if method is None:
            # 从节点提取位置信息 (Extract position from node for diagnostic)
            pos: Position | None = None
            if node.position and isinstance(node.position, dict):
                start = node.position.get("start", {})
                if isinstance(start, dict):
                    pos = Position(
                        line=int(start.get("line", 0)),
                        column=int(start.get("column", 1)),
                    )
            self._diag.warning(
                f"Unhandled node type '{node.type}', rendering children only",
                pos,
            )
            return self._render_children(node)
        result: str = method(node)
        return result

    def _render_children(self, node: Node) -> str:
        """渲染所有子节点并拼接 (Render and concat children)."""
        return "".join(self._dispatch(c) for c in node.children)

    # ── Front matter & footnotes ─────────────────────────────────

    def _render_front_matter(self, doc: Document) -> str:
        """文档元数据 → YAML front matter (Metadata → YAML front matter)."""
        keys = ["title", "author", "date", "abstract"]
        lines: list[str] = []
        for key in keys:
            val = doc.metadata.get(key)
            if val is not None:
                val_str = str(val)
                if "\n" in val_str:
                    # Use YAML block scalar for multi-line values (多行值使用 YAML 块标量)
                    indented = "\n".join(f"  {line}" for line in val_str.split("\n"))
                    lines.append(f"{key}: |\n{indented}")
                else:
                    lines.append(f"{key}: {_yaml_safe_scalar(val_str)}")
        if not lines:
            return ""
        return "---\n" + "\n".join(lines) + "\n---\n"

    def _render_footnotes(self) -> str:
        """渲染脚注定义 (Render footnote definitions at end)."""
        defs: list[str] = []
        for key in self._index.cite_keys:
            content = self._bib.get(key, key)
            defs.append(f"[^{key}]: {content}")
        for def_id, content in self._native_fn_defs.items():
            defs.append(f"[^{def_id}]: {content}")
        return ("\n".join(defs) + "\n") if defs else ""

    # ── Block nodes ──────────────────────────────────────────────

    def _render_document(self, node: Document) -> str:
        """渲染文档 (Render document — called by render())."""
        return self._render_children(node)

    def _render_heading(self, node: Node) -> str:
        """标题渲染 (Heading rendering)."""
        h = cast(Heading, node)
        prefix = "#" * h.level
        text = self._render_children(h)
        label = str(h.metadata.get("label", ""))
        if label:
            if self._heading_id_style == "html":
                # Escape id attribute and heading text content (转义 id 属性和标题文本内容)
                return f'<h{h.level} id="{_esc(label)}">{_esc(text)}</h{h.level}>\n\n'
            else:
                # attr style: ## Heading {#id}
                return f"{prefix} {text} {{#{label}}}\n\n"
        return f"{prefix} {text}\n\n"

    def _render_paragraph(self, node: Node) -> str:
        """段落渲染，检测图片上下文 (Paragraph, detect figure)."""
        p = cast(Paragraph, node)
        # 图片段落穿透 (Image-in-paragraph figure promotion)
        if len(p.children) == 1 and isinstance(p.children[0], Image):
            img = p.children[0]
            if "caption" in img.metadata or "label" in img.metadata:
                return self._render_image_as_figure(img) + "\n\n"
        return self._render_children(p) + "\n\n"

    def _render_blockquote(self, node: Node) -> str:
        """引用块渲染 (Blockquote rendering)."""
        inner = self._render_children(node).strip()
        lines = inner.split("\n")
        return "\n".join(f"> {line}" for line in lines) + "\n\n"

    def _render_list(self, node: Node) -> str:
        """列表渲染，支持嵌套缩进 (List rendering with nesting indentation)."""
        lst = cast(List, node)
        indent = "  " * self._list_depth
        parts: list[str] = []
        self._list_depth += 1
        for i, item in enumerate(lst.children, start=lst.start):
            marker = f"{i}." if lst.ordered else "-"
            content = self._render_list_item_content(item)
            parts.append(f"{indent}{marker} {content}")
        self._list_depth -= 1
        return "\n".join(parts) + "\n\n"

    def _render_list_item_content(self, node: Node) -> str:
        """列表项内容渲染，嵌套子内容缩进 (List item content with nested indentation)."""
        parts: list[str] = []
        for child in node.children:
            rendered = self._dispatch(child)
            parts.append(rendered)
        return "".join(parts).strip()

    def _render_list_item(self, node: Node) -> str:
        """列表项渲染 (List item rendering)."""
        return self._render_children(node).strip()

    def _render_code_block(self, node: Node) -> str:
        """代码块渲染 (Code block rendering)."""
        c = cast(CodeBlock, node)
        lang = c.language or ""
        return f"```{lang}\n{c.content}\n```\n\n"

    def _render_math_block(self, node: Node) -> str:
        """数学块渲染 (Math block rendering)."""
        m = cast(MathBlock, node)
        label = str(m.metadata.get("label", ""))
        # Escape id attribute value (转义 id 属性值)
        anchor = f'<a id="{_esc(label)}"></a>\n' if label else ""
        return f"{anchor}$$\n{m.content}\n$$\n\n"

    def _render_image(self, node: Node) -> str:
        """普通行内图片渲染 (Plain inline image rendering)."""
        img = cast(Image, node)
        return f"![{img.alt}]({img.src})"

    def _render_environment(self, node: Node) -> str:
        """环境节点渲染 (Environment: render children)."""
        return self._render_children(node)

    def _render_raw_block(self, node: Node) -> str:
        """原始块渲染 (Raw block: sanitized HTML or LaTeX details fold)."""
        rb = cast(RawBlock, node)
        if rb.kind == "html":
            # Sanitize raw HTML to prevent XSS (清洗原始 HTML 防止 XSS)
            from md_mid.sanitize import sanitize_html

            return sanitize_html(rb.content)
        # LaTeX raw block: wrap in details fold (LaTeX 块：折叠显示)
        return (
            "<details>\n"
            "<summary>📄 Raw LaTeX</summary>\n\n"
            f"```latex\n{rb.content}\n```\n\n"
            "</details>\n\n"
        )

    def _render_thematic_break(self, node: Node) -> str:
        """分隔线渲染 (Thematic break rendering)."""
        return "---\n\n"

    # ── Inline nodes ─────────────────────────────────────────────

    def _render_text(self, node: Node) -> str:
        """文本渲染 (Text rendering)."""
        return cast(Text, node).content

    def _render_strong(self, node: Node) -> str:
        """加粗渲染 (Bold rendering)."""
        return f"**{self._render_children(node)}**"

    def _render_emphasis(self, node: Node) -> str:
        """斜体渲染 (Italic rendering)."""
        return f"*{self._render_children(node)}*"

    def _render_code_inline(self, node: Node) -> str:
        """行内代码渲染 (Inline code rendering)."""
        return f"`{cast(CodeInline, node).content}`"

    def _render_math_inline(self, node: Node) -> str:
        """行内公式渲染 (Inline math rendering)."""
        return f"${cast(MathInline, node).content}$"

    def _render_link(self, node: Node) -> str:
        """链接渲染 (Link rendering)."""
        lnk = cast(Link, node)
        text = self._render_children(lnk)
        return f"[{text}]({lnk.url})"

    def _render_citation(self, node: Node) -> str:
        """引用 → Markdown 脚注引用 (Citation → footnote ref)."""
        c = cast(Citation, node)
        refs = "".join(f"[^{key}]" for key in c.keys)
        if c.display_text:
            return f"{c.display_text}{refs}"
        return refs

    def _render_cross_ref(self, node: Node) -> str:
        """交叉引用 → HTML 锚点 (Cross-ref → HTML anchor link)."""
        r = cast(CrossRef, node)
        # Escape href attribute value and link text (转义 href 属性值和链接文本)
        return f'<a href="#{_esc(r.label)}">{_esc(r.display_text)}</a>'

    def _render_softbreak(self, node: Node) -> str:
        """软换行 (Soft break)."""
        return "\n"

    def _render_hardbreak(self, node: Node) -> str:
        """硬换行 (Hard break — two trailing spaces + newline)."""
        return "  \n"

    def _render_footnote_ref(self, node: Node) -> str:
        """脚注引用渲染 (Footnote reference rendering)."""
        fr = cast(FootnoteRef, node)
        return f"[^{fr.ref_id}]"

    def _render_footnote_def(self, node: Node) -> str:
        """脚注定义 — 收集备用 (Footnote def — collect for end-of-doc output)."""
        fd = cast(FootnoteDef, node)
        # Render children as text and store for end-of-doc emission (渲染子节点为文本并存储)
        content = self._render_children(node).strip()
        self._native_fn_defs[fd.def_id] = content
        return ""
