"""HTML renderer — converts EAST to self-contained academic HTML.

HTML 渲染器 — 将 EAST 转换为自包含的学术 HTML。
"""

from __future__ import annotations

import html as _html_lib
import re
from typing import cast

from md_mid.ai_meta import render_ai_details_html
from md_mid.nodes import (
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    Environment,
    Figure,
    FootnoteDef,
    FootnoteRef,
    Heading,
    Image,
    Link,
    List,
    MathBlock,
    MathInline,
    Node,
    RawBlock,
    Table,
    Text,
)
from md_mid.url_check import is_unsafe_url


def _esc(text: str) -> str:
    """HTML-escape text (HTML 转义文本)."""
    return _html_lib.escape(text, quote=True)


# Safe width pattern: digits + CSS units only (安全宽度正则：仅数字 + CSS 单位)
_SAFE_WIDTH_RE = re.compile(r"^\d+(\.\d+)?(px|em|rem|%|cm|mm|pt|vw)$")


# MathJax v3 CDN (MathJax v3 CDN 链接)
_MATHJAX_CDN = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"

# Minimal academic CSS (最小学术 CSS 样式)
_CSS = """\
body { max-width: 800px; margin: 2em auto; font-family: serif; line-height: 1.7;
       padding: 0 1em; color: #222; }
h1, h2, h3, h4 { font-weight: bold; margin-top: 1.5em; }
figure { text-align: center; margin: 1.5em auto; }
figcaption { font-style: italic; margin-top: 0.4em; }
table { border-collapse: collapse; margin: 1em auto; }
th, td { border: 1px solid #bbb; padding: 0.4em 0.8em; }
th { background: #f4f4f4; }
.table-wrap { text-align: center; margin: 1.5em 0; }
.table-caption { font-style: italic; margin-bottom: 0.4em; }
pre { background: #f6f6f6; padding: 1em; overflow-x: auto; border-radius: 4px; }
code { font-family: monospace; font-size: 0.92em; }
blockquote { border-left: 4px solid #ccc; margin-left: 0; padding-left: 1em;
             color: #555; }
.footnotes { border-top: 1px solid #ccc; margin-top: 3em; font-size: 0.9em; }
.bibliography { margin-top: 2em; }
details { background: #fafafa; border: 1px solid #ddd; border-radius: 4px;
          padding: 0.5em 1em; margin: 1em 0; }
summary { cursor: pointer; font-weight: bold; }
"""


class HTMLRenderer:
    """Render EAST to self-contained academic HTML.

    将 EAST 渲染为自包含的学术 HTML。

    Args:
        mode: Output mode — full | body | fragment  (输出模式)
        bib: Bibliography dict key→display string  (参考文献字典)
        locale: Label language zh | en  (标签语言)
        diag: Diagnostic collector  (诊断收集器)
    """

    def __init__(
        self,
        mode: str = "full",
        bib: dict[str, str] | None = None,
        locale: str = "zh",
        diag: object = None,
    ) -> None:
        self._mode = mode
        self._bib: dict[str, str] = bib or {}
        self._locale = locale
        self._diag = diag

        # Figure / table counters (图表计数器)
        self._fig_count: int = 0
        self._tab_count: int = 0

        # Citation tracking: key → sequential number  (引用编号追踪)
        self._cite_order: dict[str, int] = {}
        self._cite_seq: int = 0

        # Native footnote defs (原生脚注定义)
        self._fn_defs: dict[str, str] = {}

        # Footnote ref sequential numbering (脚注引用序号)
        self._fn_ref_order: dict[str, int] = {}
        self._fn_ref_seq: int = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self, node: Node) -> str:
        """Render a node to HTML string (渲染节点为 HTML 字符串)."""
        if isinstance(node, Document):
            return self._render_document(node)
        return self._dispatch(node)

    # ── Document ──────────────────────────────────────────────────────────────

    def _render_document(self, doc: Document) -> str:
        """Render the full document (渲染完整文档)."""
        # Reset state for each render call (每次渲染重置状态)
        self._fig_count = 0
        self._tab_count = 0
        self._cite_order = {}
        self._cite_seq = 0
        self._fn_defs = {}
        self._fn_ref_order = {}
        self._fn_ref_seq = 0

        body = "".join(self._dispatch(child) for child in doc.children)
        footnotes = self._render_footnotes()

        if self._mode == "fragment":
            return body

        if self._mode == "body":
            return body + footnotes

        # Full document mode (全文模式)
        title = str(doc.metadata.get("title", ""))
        title_tag = f"<title>{_esc(title)}</title>" if title else "<title>Document</title>"

        # Map locale to HTML lang attribute (本地化映射为 HTML lang 属性)
        lang = "en" if self._locale == "en" else "zh-CN"

        return (
            "<!DOCTYPE html>\n"
            f'<html lang="{lang}">\n'
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"{title_tag}\n"
            f"<style>\n{_CSS}</style>\n"
            "<script>\n"
            "MathJax = { tex: { inlineMath: [['$','$']] }, "
            "options: { skipHtmlTags: ['script','style'] } };\n"
            "</script>\n"
            f'<script src="{_MATHJAX_CDN}" id="MathJax-script" async></script>\n'
            "</head>\n"
            "<body>\n" + body + footnotes + "</body>\n"
            "</html>\n"
        )

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, node: Node) -> str:
        """Dispatch node to the appropriate render method (分发节点到对应渲染方法)."""
        handlers = {
            "heading": self._render_heading,
            "paragraph": self._render_paragraph,
            "blockquote": self._render_blockquote,
            "list": self._render_list,
            "list_item": self._render_list_item,
            "code_block": self._render_code_block,
            "figure": self._render_figure,
            "image": self._render_image,
            "table": self._render_table,
            "math_block": self._render_math_block,
            "environment": self._render_environment,
            "raw_block": self._render_raw_block,
            "thematic_break": self._render_thematic_break,
            "text": self._render_text,
            "strong": self._render_strong,
            "emphasis": self._render_emphasis,
            "code_inline": self._render_code_inline,
            "math_inline": self._render_math_inline,
            "link": self._render_link,
            "cross_ref": self._render_cross_ref,
            "citation": self._render_citation,
            "footnote_ref": self._render_footnote_ref,
            "footnote_def": self._render_footnote_def,
            "hardbreak": self._render_hard_break,
            "softbreak": self._render_soft_break,
        }
        handler = handlers.get(node.type)
        if handler:
            return handler(node)
        # Unknown node: render children (未知节点：渲染子节点)
        return self._render_children(node)

    def _render_children(self, node: Node) -> str:
        """Render all children and concatenate (渲染所有子节点并拼接)."""
        return "".join(self._dispatch(child) for child in node.children)

    # ── Block nodes ───────────────────────────────────────────────────────────

    def _render_heading(self, node: Node) -> str:
        """Heading → h1-h6 with optional id anchor (标题渲染)."""
        h = cast(Heading, node)
        level = max(1, min(6, h.level))
        label = str(node.metadata.get("label", ""))
        id_attr = f' id="{_esc(label)}"' if label else ""
        content = self._render_children(node)
        return f"<h{level}{id_attr}>{content}</h{level}>\n"

    def _render_paragraph(self, node: Node) -> str:
        """Paragraph → p tag (段落渲染)."""
        content = self._render_children(node)
        if not content.strip():
            return ""
        return f"<p>{content}</p>\n"

    def _render_blockquote(self, node: Node) -> str:
        """Blockquote → blockquote tag (引用渲染)."""
        content = self._render_children(node)
        return f"<blockquote>\n{content}</blockquote>\n"

    def _render_list(self, node: Node) -> str:
        """List → ul or ol (列表渲染)."""
        lst = cast(List, node)
        tag = "ol" if lst.ordered else "ul"
        content = self._render_children(node)
        return f"<{tag}>\n{content}</{tag}>\n"

    def _render_list_item(self, node: Node) -> str:
        """List item → li (列表项渲染)."""
        content = self._render_children(node)
        return f"<li>{content}</li>\n"

    def _render_code_block(self, node: Node) -> str:
        """Code block → pre/code with language class (代码块渲染)."""
        cb = cast(CodeBlock, node)
        lang_attr = f' class="language-{_esc(cb.language)}"' if cb.language else ""
        escaped = _esc(cb.content)
        return f"<pre><code{lang_attr}>{escaped}</code></pre>\n"

    def _render_figure(self, node: Node) -> str:
        """Figure → figure tag with auto-numbering (图渲染，自动编号)."""
        self._fig_count += 1
        fig = cast(Figure, node)
        meta = node.metadata
        label = str(meta.get("label", ""))
        caption = str(meta.get("caption", ""))
        width = str(meta.get("width", ""))
        ai = meta.get("ai")

        # Determine label prefix for caption (确定标签前缀)
        prefix = "Figure" if self._locale == "en" else "图"
        id_attr = f' id="{_esc(label)}"' if label else ""

        # Build img tag (构建 img 标签)
        style = f' style="max-width:{_esc(width)}"' if width and _SAFE_WIDTH_RE.match(width) else ""
        img_tag = f'<img src="{_esc(fig.src)}" alt="{_esc(fig.alt)}"{style} loading="lazy">'

        lines = [f"<figure{id_attr}>", f"  {img_tag}"]

        if caption:
            cap_text = f"{prefix} {self._fig_count}: {_esc(caption)}"
            lines.append(f"  <figcaption>{cap_text}</figcaption>")

        # AI generation info as details fold (AI 生成信息折叠块)
        if isinstance(ai, dict):
            lines.extend(self._render_ai_details(ai))

        lines.append("</figure>")
        return "\n".join(lines) + "\n"

    def _render_image(self, node: Node) -> str:
        """Image → plain img or promoted to figure if it has caption/label.

        有 caption/label 时升级为 figure 环境渲染。
        """
        img = cast(Image, node)
        meta = node.metadata
        if meta.get("caption") or meta.get("label"):
            # Promote: reuse figure rendering logic (升级为 figure 渲染)
            fig_node = Figure(
                src=img.src,
                alt=img.alt,
                children=list(img.children),
                metadata=dict(meta),
            )
            return self._render_figure(fig_node)
        return f'<img src="{_esc(img.src)}" alt="{_esc(img.alt)}" loading="lazy">'

    def _render_table(self, node: Node) -> str:
        """Table → table tag with auto-numbering and caption (表渲染，自动编号)."""
        self._tab_count += 1
        tbl = cast(Table, node)
        meta = node.metadata
        label = str(meta.get("label", ""))
        caption = str(meta.get("caption", ""))
        prefix = "Table" if self._locale == "en" else "表"
        id_attr = f' id="{_esc(label)}"' if label else ""

        lines: list[str] = [f'<div class="table-wrap"{id_attr}>']

        if caption:
            cap_text = f"{prefix} {self._tab_count}: {_esc(caption)}"
            lines.append(f'  <p class="table-caption">{cap_text}</p>')

        lines.append("  <table>")

        # Build alignment style map (构建对齐样式映射)
        def _align_style(col_idx: int) -> str:
            if col_idx < len(tbl.alignments):
                a = tbl.alignments[col_idx]
                if a in ("left", "center", "right"):
                    return f' style="text-align:{a}"'
            return ""

        # Header row (表头行)
        if tbl.headers:
            lines.append("    <tr>")
            for ci, cell_nodes in enumerate(tbl.headers):
                cell_html = "".join(self._dispatch(n) for n in cell_nodes)
                lines.append(f"      <th{_align_style(ci)}>{cell_html}</th>")
            lines.append("    </tr>")

        # Data rows (数据行)
        for row in tbl.rows:
            lines.append("    <tr>")
            for ci, cell_nodes in enumerate(row):
                cell_html = "".join(self._dispatch(n) for n in cell_nodes)
                lines.append(f"      <td{_align_style(ci)}>{cell_html}</td>")
            lines.append("    </tr>")

        lines.append("  </table>")
        lines.append("</div>")
        return "\n".join(lines) + "\n"

    def _render_math_block(self, node: Node) -> str:
        r"""Math block → \[...\] for MathJax, HTML-escaped (块级数学公式，HTML 转义)."""
        mb = cast(MathBlock, node)
        label = str(node.metadata.get("label", ""))
        id_attr = f' id="{_esc(label)}"' if label else ""
        # Escape math content for HTML safety; MathJax reads decoded text (HTML 转义数学内容)
        return f'<div class="math-block"{id_attr}>\n\\[{_esc(mb.content)}\\]\n</div>\n'

    def _render_environment(self, node: Node) -> str:
        """Environment → generic div with class (环境渲染)."""
        env = cast(Environment, node)
        content = self._render_children(node)
        return f'<div class="env-{_esc(env.name)}">\n{content}</div>\n'

    def _render_raw_block(self, node: Node) -> str:
        """Raw block: HTML kind → sanitized; LaTeX → details fold (原始块渲染)."""
        rb = cast(RawBlock, node)
        if rb.kind == "html":
            # Sanitize HTML through allowlist (通过白名单清洗 HTML)
            from md_mid.sanitize import sanitize_html

            return sanitize_html(rb.content) + "\n"
        # LaTeX raw block → collapsible fold (LaTeX 块折叠显示)
        escaped = _esc(rb.content)
        return (
            "<details>\n"
            "<summary>Raw LaTeX</summary>\n"
            f'<pre><code class="language-latex">{escaped}</code></pre>\n'
            "</details>\n"
        )

    def _render_thematic_break(self, node: Node) -> str:
        """Thematic break → hr (分割线渲染)."""
        return "<hr>\n"

    # ── Inline nodes ──────────────────────────────────────────────────────────

    def _render_text(self, node: Node) -> str:
        """Text node → HTML-escaped string (文本节点 HTML 转义)."""
        t = cast(Text, node)
        return _esc(t.content)

    def _render_strong(self, node: Node) -> str:
        """Strong → strong tag (加粗渲染)."""
        return f"<strong>{self._render_children(node)}</strong>"

    def _render_emphasis(self, node: Node) -> str:
        """Emphasis → em tag (斜体渲染)."""
        return f"<em>{self._render_children(node)}</em>"

    def _render_code_inline(self, node: Node) -> str:
        """Inline code → code tag (行内代码渲染)."""
        ci = cast(CodeInline, node)
        return f"<code>{_esc(ci.content)}</code>"

    def _render_math_inline(self, node: Node) -> str:
        """Inline math → $...$ for MathJax (行内数学公式渲染)."""
        mi = cast(MathInline, node)
        return f"${_esc(mi.content)}$"

    def _render_link(self, node: Node) -> str:
        """Link → a tag with scheme validation (链接渲染，含 scheme 校验)."""
        lnk = cast(Link, node)
        text = self._render_children(node)
        url = lnk.url
        # Block dangerous schemes (阻止危险 scheme)
        if is_unsafe_url(url):
            return text  # render text only, drop the link (仅渲染文本，丢弃链接)
        return f'<a href="{_esc(url)}">{text}</a>'

    def _render_cross_ref(self, node: Node) -> str:
        """Cross-ref → a tag using display_text (交叉引用渲染)."""
        cr = cast(CrossRef, node)
        # Parser fills display_text, not children (解析器填充 display_text 而非 children)
        text = _esc(cr.display_text) if cr.display_text else _esc(cr.label)
        return f'<a href="#{_esc(cr.label)}">{text}</a>'

    def _render_citation(self, node: Node) -> str:
        """Citation → superscript numbered reference (文献引用渲染)."""
        cit = cast(Citation, node)
        parts: list[str] = []
        for key in cit.keys:
            if key not in self._cite_order:
                self._cite_seq += 1
                self._cite_order[key] = self._cite_seq
            n = self._cite_order[key]
            parts.append(f'<sup><a href="#cite-{_esc(key)}" class="cite">[{n}]</a></sup>')
        return "".join(parts)

    def _render_footnote_ref(self, node: Node) -> str:
        """Footnote ref → superscript sequential number (脚注引用渲染为上标序号)."""
        fr = cast(FootnoteRef, node)
        if fr.ref_id not in self._fn_ref_order:
            self._fn_ref_seq += 1
            self._fn_ref_order[fr.ref_id] = self._fn_ref_seq
        n = self._fn_ref_order[fr.ref_id]
        return f'<sup><a href="#fn-{_esc(fr.ref_id)}">[{n}]</a></sup>'

    def _render_footnote_def(self, node: Node) -> str:
        """Footnote def → collect for end of document (脚注定义收集)."""
        fd = cast(FootnoteDef, node)
        content = self._render_children(node).strip()
        self._fn_defs[fd.def_id] = content
        return ""

    def _render_hard_break(self, node: Node) -> str:
        """Hard break → br tag (硬换行渲染)."""
        return "<br>\n"

    def _render_soft_break(self, node: Node) -> str:
        """Soft break → newline (preserves Markdown line break semantics) (软换行渲染)."""
        return "\n"

    # ── Footnotes and bibliography ────────────────────────────────────────────

    def _render_footnotes(self) -> str:
        """Render bibliography + footnote definitions at end (渲染文末参考文献和脚注)."""
        if self._mode == "fragment":
            return ""

        parts: list[str] = []

        # Bibliography (参考文献部分)
        if self._cite_order:
            parts.append('<div class="bibliography">\n<h2>References</h2>\n<ol>\n')
            for key, _num in sorted(self._cite_order.items(), key=lambda kv: kv[1]):
                text = _esc(self._bib.get(key, key))
                parts.append(f'  <li id="cite-{_esc(key)}">{text}</li>\n')
            parts.append("</ol>\n</div>\n")

        # Footnotes — sorted by ref encounter order (脚注部分 — 按引用出现顺序排序)
        if self._fn_defs:
            parts.append('<div class="footnotes">\n<hr>\n<ol>\n')
            ordered = sorted(
                self._fn_defs.items(),
                key=lambda kv: self._fn_ref_order.get(kv[0], 999),
            )
            for def_id, content in ordered:
                parts.append(f'  <li id="fn-{_esc(def_id)}">{content}</li>\n')
            parts.append("</ol>\n</div>\n")

        return "".join(parts)

    # ── AI details helper ─────────────────────────────────────────────────────

    def _render_ai_details(self, ai: dict[str, object]) -> list[str]:
        """Render AI generation info as HTML details fold (AI 信息折叠块渲染)."""
        return render_ai_details_html(ai, _esc)
