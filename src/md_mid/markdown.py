"""Rich Markdown Renderer: EAST → GitHub/Obsidian/Typora-compatible Markdown.

两次扫描架构 (Two-pass architecture):
  Pass 1 (Index): 预扫描，收集引用键 (Pre-scan to collect cite keys)
  Pass 2 (Render): 使用索引数据渲染 (Render using index data)
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from typing import cast

from md_mid.diagnostic import DiagCollector
from md_mid.nodes import (
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    Figure,
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
    Table,
    Text,
)


def _esc(text: str) -> str:
    """Escape HTML special characters for attributes and content (HTML 特殊字符转义)."""
    return _html.escape(text, quote=True)


@dataclass
class MarkdownIndex:
    """Pass 1 收集结果 (Pass 1 results)."""

    # 按出现顺序排列的唯一引用键 (ordered unique citation keys)
    cite_keys: list[str] = field(default_factory=list)


class MarkdownRenderer:
    """EAST → Rich Markdown 渲染器 (EAST to Rich Markdown renderer)."""

    def __init__(
        self,
        bib: dict[str, str] | None = None,
        heading_id_style: str = "attr",
        diag: DiagCollector | None = None,
    ) -> None:
        """初始化渲染器 (Initialize renderer).

        Args:
            bib: BibTeX key → formatted citation string
                 (BibTeX 键 → 格式化引用字符串)
            heading_id_style: Anchor style for headings:
                'attr' ({#id}) or 'html' (<hN id=...>)
                (标题锚点风格)
            diag: Optional diagnostic collector (可选诊断收集器)
        """
        self._bib = bib or {}
        self._heading_id_style = heading_id_style
        self._diag = diag or DiagCollector("unknown")
        self._index: MarkdownIndex = MarkdownIndex()
        self._fig_count: int = 0  # 图计数器 (figure counter)
        self._tab_count: int = 0  # 表计数器 (table counter)

    def render(self, doc: Document) -> str:
        """渲染文档为 Rich Markdown (Render document to Rich Markdown).

        Args:
            doc: EAST Document node (EAST 文档节点)

        Returns:
            Rich Markdown string (Rich Markdown 字符串)
        """
        # 重置计数器 (Reset counters for fresh render)
        self._fig_count = 0
        self._tab_count = 0

        # Pass 1: 收集引用键 (Collect citation keys)
        self._index = self._build_index(doc)

        # Pass 2: 渲染 (Render)
        parts: list[str] = []

        front_matter = self._render_front_matter(doc)
        if front_matter:
            parts.append(front_matter)

        body = self._render_children(doc)
        parts.append(body)

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
                if key not in index.cite_keys:
                    index.cite_keys.append(key)
        for child in node.children:
            self._index_node(child, index)

    # ── Pass 2: Render helpers ───────────────────────────────────

    def _dispatch(self, node: Node) -> str:
        """分发到对应渲染方法 (Dispatch to render method)."""
        method_name = f"_render_{node.type}"
        method = getattr(self, method_name, None)
        if method is None:
            self._diag.warning(
                f"Unhandled node type '{node.type}',"
                " rendering children only"
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
                    lines.append(f"{key}: {val_str}")
        if not lines:
            return ""
        return "---\n" + "\n".join(lines) + "\n---\n"

    def _render_footnotes(self) -> str:
        """渲染脚注定义 (Render footnote definitions at end)."""
        if not self._index.cite_keys:
            return ""
        defs: list[str] = []
        for key in self._index.cite_keys:
            content = self._bib.get(key, key)
            defs.append(f"[^{key}]: {content}")
        return "\n".join(defs) + "\n"

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
                return (
                    f'<h{h.level} id="{_esc(label)}">'
                    f"{_esc(text)}</h{h.level}>\n\n"
                )
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
        """列表渲染 (List rendering)."""
        lst = cast(List, node)
        parts: list[str] = []
        for i, item in enumerate(lst.children, start=lst.start):
            marker = f"{i}." if lst.ordered else "-"
            content = self._dispatch(item).strip()
            parts.append(f"{marker} {content}")
        return "\n".join(parts) + "\n\n"

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

    def _render_figure(self, node: Node) -> str:
        """Figure 节点渲染 (Figure node rendering)."""
        f = cast(Figure, node)
        return self._render_figure_block(
            f.src, f.alt, f.metadata
        ) + "\n\n"

    def _render_image(self, node: Node) -> str:
        """普通行内图片渲染 (Plain inline image rendering)."""
        img = cast(Image, node)
        return f"![{img.alt}]({img.src})"

    def _render_image_as_figure(self, img: Image) -> str:
        """Image 节点 → HTML figure 块 (Image as HTML figure block)."""
        return self._render_figure_block(
            img.src, img.alt, img.metadata
        )

    def _render_figure_block(
        self,
        src: str,
        alt: str,
        metadata: dict[str, object],
    ) -> str:
        """生成 HTML figure 块 (Generate HTML figure block)."""
        self._fig_count += 1
        n = self._fig_count
        label = str(metadata.get("label", ""))
        caption = str(metadata.get("caption", ""))
        # Escape id attribute and img attributes (转义 id 属性和 img 属性)
        id_attr = f' id="{_esc(label)}"' if label else ""
        lines: list[str] = [
            f"<figure{id_attr}>",
            f'  <img src="{_esc(src)}" alt="{_esc(alt)}"'
            ' style="max-width:100%">',
        ]
        if caption:
            lines.append(
                f"  <figcaption><strong>图 {n}</strong>"
                f": {_esc(caption)}</figcaption>"
            )
        else:
            lines.append(
                f"  <figcaption><strong>图 {n}</strong>"
                "</figcaption>"
            )

        # AI 信息折叠块 (AI info details block)
        ai = metadata.get("ai")
        if isinstance(ai, dict):
            lines.append("  <details>")
            lines.append(
                "    <summary>🎨 AI Generation Info</summary>"
            )
            if model := ai.get("model"):
                lines.append(
                    f"    <p><strong>Model</strong>: {_esc(str(model))}</p>"
                )
            if prompt := ai.get("prompt"):
                lines.append(
                    f"    <p><strong>Prompt</strong>: {_esc(str(prompt))}</p>"
                )
            if neg := ai.get("negative_prompt"):
                lines.append(
                    f"    <p><strong>Negative</strong>: {_esc(str(neg))}</p>"
                )
            if params := ai.get("params"):
                lines.append(
                    f"    <p><strong>Params</strong>: {_esc(str(params))}</p>"
                )
            lines.append("  </details>")

        lines.append("</figure>")
        return "\n".join(lines)

    def _render_table(self, node: Node) -> str:
        """表格 → HTML table + caption (Table as HTML table)."""
        t = cast(Table, node)
        self._tab_count += 1
        n = self._tab_count
        label = str(t.metadata.get("label", ""))
        caption = str(t.metadata.get("caption", ""))
        # Escape id attribute value (转义 id 属性值)
        id_attr = f' id="{_esc(label)}"' if label else ""

        # 表头 (Table headers)
        th_cells = "".join(f"<th>{_esc(h)}</th>" for h in t.headers)
        header_row = f"      <tr>{th_cells}</tr>"

        # 数据行 (Data rows)
        data_rows: list[str] = []
        for row in t.rows:
            td_cells = "".join(
                f"<td>{_esc(cell)}</td>" for cell in row
            )
            data_rows.append(f"      <tr>{td_cells}</tr>")

        lines: list[str] = [
            f"<figure{id_attr}>",
            "  <table>",
            "    <thead>",
            header_row,
            "    </thead>",
            "    <tbody>",
            *data_rows,
            "    </tbody>",
            "  </table>",
        ]
        if caption:
            lines.append(
                f"  <figcaption><strong>表 {n}</strong>"
                f": {_esc(caption)}</figcaption>"
            )
        else:
            lines.append(
                f"  <figcaption><strong>表 {n}</strong>"
                "</figcaption>"
            )
        lines.append("</figure>")
        return "\n".join(lines) + "\n\n"

    def _render_environment(self, node: Node) -> str:
        """环境节点渲染 (Environment: render children)."""
        return self._render_children(node)

    def _render_raw_block(self, node: Node) -> str:
        """原始 LaTeX 块 → 折叠块 (Raw LaTeX → details fold)."""
        rb = cast(RawBlock, node)
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
        """脚注定义 — 跳过 (Footnote def — skipped, at end)."""
        return ""
