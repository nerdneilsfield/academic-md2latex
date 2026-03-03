"""Tests for HTML renderer (HTML 渲染器测试)."""

from __future__ import annotations

from md_mid.html import HTMLRenderer
from md_mid.nodes import (
    Blockquote,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    Emphasis,
    HardBreak,
    Heading,
    Link,
    List,
    ListItem,
    MathBlock,
    MathInline,
    Paragraph,
    RawBlock,
    SoftBreak,
    Strong,
    Text,
    ThematicBreak,
)


def doc(*children) -> Document:
    """Convenience: build a Document from nodes (构造含节点的文档)."""
    return Document(children=list(children))


def render(node, **kwargs) -> str:
    """Render a node with HTMLRenderer (用 HTMLRenderer 渲染节点)."""
    return HTMLRenderer(**kwargs).render(node)


# ── Document structure ────────────────────────────────────────────────────────


class TestHtmlDocumentStructure:
    """Full-mode HTML document has proper wrapping (全文模式有完整 HTML 包裹)."""

    def test_full_mode_has_doctype(self) -> None:
        """Full mode starts with DOCTYPE (全文模式以 DOCTYPE 开始)."""
        result = render(doc(Paragraph(children=[Text(content="Hi")])), mode="full")
        assert result.startswith("<!DOCTYPE html>")

    def test_full_mode_has_mathjax(self) -> None:
        """Full mode includes MathJax CDN script (全文模式包含 MathJax 脚本)."""
        result = render(doc(Paragraph(children=[Text(content="Hi")])), mode="full")
        assert "mathjax" in result.lower()

    def test_body_mode_no_doctype(self) -> None:
        """Body mode has no DOCTYPE (body 模式无 DOCTYPE)."""
        result = render(doc(Paragraph(children=[Text(content="Hi")])), mode="body")
        assert "<!DOCTYPE" not in result

    def test_fragment_mode_minimal(self) -> None:
        """Fragment mode produces minimal output (fragment 模式输出最小内容)."""
        result = render(doc(Paragraph(children=[Text(content="Hi")])), mode="fragment")
        assert "<!DOCTYPE" not in result
        assert "<html" not in result


# ── Block nodes ───────────────────────────────────────────────────────────────


class TestHtmlHeading:
    """Heading renders to h1-h6 with id anchor (标题渲染为带 id 的 h 标签)."""

    def test_h1(self) -> None:
        h = Heading(level=1, children=[Text(content="Title")])
        result = render(doc(h))
        assert "<h1" in result
        assert "Title" in result

    def test_heading_has_id(self) -> None:
        h = Heading(level=2, children=[Text(content="My Section")])
        h.metadata["label"] = "sec:intro"
        result = render(doc(h))
        assert 'id="sec:intro"' in result

    def test_h2_through_h6(self) -> None:
        for level in range(2, 7):
            h = Heading(level=level, children=[Text(content="X")])
            result = render(doc(h))
            assert f"<h{level}" in result


class TestHtmlParagraph:
    """Paragraph renders to p tag (段落渲染为 p 标签)."""

    def test_basic_paragraph(self) -> None:
        result = render(doc(Paragraph(children=[Text(content="Hello world")])))
        assert "<p>" in result
        assert "Hello world" in result


class TestHtmlList:
    """Lists render to ul/ol (列表渲染)."""

    def test_unordered_list(self) -> None:
        lst = List(
            ordered=False,
            children=[
                ListItem(children=[Paragraph(children=[Text(content="item")])]),
            ],
        )
        result = render(doc(lst))
        assert "<ul>" in result
        assert "<li>" in result

    def test_ordered_list(self) -> None:
        lst = List(
            ordered=True,
            children=[
                ListItem(children=[Paragraph(children=[Text(content="item")])]),
            ],
        )
        result = render(doc(lst))
        assert "<ol>" in result


class TestHtmlCodeBlock:
    """Code block renders to pre/code (代码块渲染)."""

    def test_code_block(self) -> None:
        cb = CodeBlock(content="x = 1", language="python")
        result = render(doc(cb))
        assert "<pre>" in result
        assert "<code" in result
        assert "x = 1" in result

    def test_code_block_language_class(self) -> None:
        cb = CodeBlock(content="x = 1", language="python")
        result = render(doc(cb))
        assert "python" in result


class TestHtmlBlockQuote:
    """Blockquote renders to blockquote tag (引用渲染)."""

    def test_blockquote(self) -> None:
        bq = Blockquote(children=[Paragraph(children=[Text(content="quote")])])
        result = render(doc(bq))
        assert "<blockquote>" in result
        assert "quote" in result


class TestHtmlMath:
    """Math renders with MathJax delimiters (数学公式使用 MathJax 分隔符)."""

    def test_math_block(self) -> None:
        mb = MathBlock(content="x^2 + y^2 = z^2")
        result = render(doc(Paragraph(children=[mb])))
        assert "x^2 + y^2 = z^2" in result

    def test_math_inline(self) -> None:
        p = Paragraph(
            children=[
                Text(content="See "),
                MathInline(content="E=mc^2"),
            ]
        )
        result = render(doc(p))
        assert "E=mc^2" in result


class TestHtmlThematicBreak:
    """Thematic break renders to hr (分割线渲染)."""

    def test_thematic_break(self) -> None:
        result = render(doc(ThematicBreak()))
        assert "<hr" in result


class TestHtmlRawBlock:
    """Raw block HTML passthrough; LaTeX raw block as details fold (原始块处理)."""

    def test_html_raw_passthrough(self) -> None:
        rb = RawBlock(content="<div>hi</div>", kind="html")
        result = render(doc(rb))
        assert "<div>hi</div>" in result
        assert "<details>" not in result

    def test_latex_raw_details_fold(self) -> None:
        rb = RawBlock(content="\\newcommand{\\myvec}{\\mathbf}", kind="latex")
        result = render(doc(rb))
        assert "<details>" in result
        assert "\\newcommand" in result


# ── Inline nodes ──────────────────────────────────────────────────────────────


class TestHtmlInline:
    """Inline elements render correctly (行内元素渲染)."""

    def test_strong(self) -> None:
        p = Paragraph(children=[Strong(children=[Text(content="bold")])])
        result = render(doc(p))
        assert "<strong>bold</strong>" in result

    def test_emphasis(self) -> None:
        p = Paragraph(children=[Emphasis(children=[Text(content="italic")])])
        result = render(doc(p))
        assert "<em>italic</em>" in result

    def test_code_inline(self) -> None:
        p = Paragraph(children=[CodeInline(content="x = 1")])
        result = render(doc(p))
        assert "<code>x = 1</code>" in result

    def test_link(self) -> None:
        p = Paragraph(children=[Link(url="https://example.com", children=[Text(content="click")])])
        result = render(doc(p))
        assert 'href="https://example.com"' in result
        assert "click" in result

    def test_text_xss_escaped(self) -> None:
        p = Paragraph(children=[Text(content="<script>alert(1)</script>")])
        result = render(doc(p), mode="fragment")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_hard_break(self) -> None:
        p = Paragraph(children=[Text(content="a"), HardBreak(), Text(content="b")])
        result = render(doc(p))
        assert "<br" in result

    def test_soft_break_renders_newline(self) -> None:
        """SoftBreak renders as newline (软换行渲染为换行)."""
        p = Paragraph(children=[Text(content="a"), SoftBreak(), Text(content="b")])
        result = render(doc(p))
        assert "a\nb" in result

    def test_cross_ref_uses_display_text(self) -> None:
        """CrossRef uses display_text, not children (交叉引用使用 display_text)."""
        cr = CrossRef(label="fig:test", display_text="Figure 1")
        result = render(doc(Paragraph(children=[cr])))
        assert "Figure 1" in result
        assert 'href="#fig:test"' in result

    def test_link_javascript_scheme_sanitized(self) -> None:
        """Links with javascript: scheme are sanitized (javascript: 链接被过滤)."""
        p = Paragraph(children=[Link(url="javascript:alert(1)", children=[Text(content="click")])])
        result = render(doc(p))
        assert "javascript:" not in result

    def test_math_inline_html_escaped(self) -> None:
        """Inline math with script is HTML-escaped (数学公式 HTML 转义)."""
        p = Paragraph(children=[MathInline(content="x<script>alert(1)</script>y")])
        result = render(doc(p), mode="fragment")
        assert "<script>" not in result
