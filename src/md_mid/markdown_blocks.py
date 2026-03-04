"""Block-level Markdown rendering: figures, tables, cell HTML.

块级 Markdown 渲染：图片、表格、单元格 HTML。
Extracted from markdown.py to keep modules under 500 lines.
(从 markdown.py 提取以保持模块在 500 行以内。)
"""

from __future__ import annotations

import html as _html
from typing import TYPE_CHECKING, cast

from md_mid.nodes import (
    Citation,
    CodeInline,
    CrossRef,
    Emphasis,
    Figure,
    HardBreak,
    Image,
    Link,
    MathInline,
    Node,
    SoftBreak,
    Strong,
    Table,
    Text,
)

if TYPE_CHECKING:
    from md_mid.diagnostic import DiagCollector


def _esc(text: str) -> str:
    """Escape HTML special characters for attributes and content (HTML 特殊字符转义)."""
    return _html.escape(text, quote=True)


class MarkdownBlockMixin:
    """Block-level Markdown rendering mixin (块级 Markdown 渲染混入).

    Provides render methods for figures, tables, and cell HTML rendering.
    Mixed into MarkdownRenderer.
    (提供图片、表格、单元格 HTML 渲染方法。混入 MarkdownRenderer。)
    """

    # These attributes are defined on MarkdownRenderer (由 MarkdownRenderer 定义)
    _fig_count: int
    _tab_count: int
    _labels: dict[str, str]
    _diag: DiagCollector

    def _render_children(self, node: Node) -> str:
        """Render children (由子类实现)."""
        return ""

    def _render_figure(self, node: Node) -> str:
        """Figure 节点渲染 (Figure node rendering)."""
        f = cast(Figure, node)
        return self._render_figure_block(f.src, f.alt, f.metadata) + "\n\n"

    def _render_image_as_figure(self, img: Image) -> str:
        """Image 节点 → HTML figure 块 (Image as HTML figure block)."""
        return self._render_figure_block(img.src, img.alt, img.metadata)

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
            f'  <img src="{_esc(src)}" alt="{_esc(alt)}" style="max-width:100%">',
        ]
        fig_label = self._labels["figure"]
        if caption:
            lines.append(
                f"  <figcaption><strong>{fig_label} {n}</strong>: {_esc(caption)}</figcaption>"
            )
        else:
            lines.append(f"  <figcaption><strong>{fig_label} {n}</strong></figcaption>")

        # AI 信息折叠块 (AI info details block)
        ai = metadata.get("ai")
        if isinstance(ai, dict):
            from md_mid.ai_meta import render_ai_details_html

            lines.extend(render_ai_details_html(ai, _esc, summary="\U0001f3a8 AI Generation Info"))

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

        # 表头 (Table headers) — render inline nodes as HTML
        th_cells = "".join(f"<th>{self._render_cell_html(h)}</th>" for h in t.headers)
        header_row = f"      <tr>{th_cells}</tr>"

        # 数据行 (Data rows) — render inline nodes as HTML
        data_rows: list[str] = []
        for row in t.rows:
            td_cells = "".join(f"<td>{self._render_cell_html(cell)}</td>" for cell in row)
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
        tab_label = self._labels["table"]
        if caption:
            lines.append(
                f"  <figcaption><strong>{tab_label} {n}</strong>: {_esc(caption)}</figcaption>"
            )
        else:
            lines.append(f"  <figcaption><strong>{tab_label} {n}</strong></figcaption>")
        lines.append("</figure>")
        return "\n".join(lines) + "\n\n"

    def _render_cell_html(self, nodes: list[Node]) -> str:
        """Render inline nodes as HTML for table cell content (表格单元格 HTML 渲染)."""
        return "".join(self._render_node_html(n) for n in nodes)

    def _render_node_html(self, node: Node) -> str:
        """Render single inline node as HTML (单个行内节点 HTML 渲染)."""
        if isinstance(node, Text):
            return _esc(node.content)
        if isinstance(node, Strong):
            inner = self._render_cell_html(node.children)
            return f"<strong>{inner}</strong>"
        if isinstance(node, Emphasis):
            inner = self._render_cell_html(node.children)
            return f"<em>{inner}</em>"
        if isinstance(node, CodeInline):
            return f"<code>{_esc(node.content)}</code>"
        if isinstance(node, MathInline):
            return f"${_esc(node.content)}$"
        if isinstance(node, Link):
            text = self._render_cell_html(node.children)
            # Block dangerous schemes in table cell links (阻止表格单元格中的危险 scheme)
            from md_mid.url_check import is_unsafe_url

            if is_unsafe_url(node.url):
                return text
            return f'<a href="{_esc(node.url)}">{text}</a>'
        if isinstance(node, Citation):
            refs = "".join(f"[^{key}]" for key in node.keys)
            return f"{_esc(node.display_text)}{refs}" if node.display_text else refs
        if isinstance(node, CrossRef):
            return f'<a href="#{_esc(node.label)}">{_esc(node.display_text)}</a>'
        if isinstance(node, SoftBreak):
            return " "
        if isinstance(node, HardBreak):
            return "<br>"
        # Fallback: render children (回退：渲染子节点)
        return self._render_cell_html(node.children)
