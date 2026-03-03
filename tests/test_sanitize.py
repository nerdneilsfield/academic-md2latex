"""Tests for HTML sanitizer module (HTML 清洗器模块测试)."""

from __future__ import annotations

from md_mid.sanitize import sanitize_html


class TestSanitizeScriptTag:
    """Script tags and their content are fully stripped (script 标签及内容完全剥离)."""

    def test_sanitize_strips_script_tag_and_content(self) -> None:
        """Script tag and its body are removed (script 标签和内容被移除)."""
        result = sanitize_html("<script>alert('xss')</script><p>safe</p>")
        assert "<script>" not in result
        assert "alert" not in result
        assert "<p>safe</p>" in result

    def test_sanitize_strips_style_tag_and_content(self) -> None:
        """Style tag and its body are removed (style 标签和内容被移除)."""
        result = sanitize_html("<style>body{display:none}</style><p>ok</p>")
        assert "<style>" not in result
        assert "display:none" not in result
        assert "<p>ok</p>" in result


class TestSanitizePreservesSafeTags:
    """Safe tags pass through unchanged (安全标签原样保留)."""

    def test_sanitize_preserves_safe_tags(self) -> None:
        """Common safe tags are preserved (常见安全标签保留)."""
        html = '<div class="note"><p>hello</p><em>world</em></div>'
        result = sanitize_html(html)
        assert '<div class="note">' in result
        assert "<p>hello</p>" in result
        assert "<em>world</em>" in result

    def test_sanitize_preserves_table_structure(self) -> None:
        """Table tags are preserved (表格标签保留)."""
        html = "<table><tr><th>H</th></tr><tr><td>V</td></tr></table>"
        result = sanitize_html(html)
        assert "<table>" in result
        assert "<th>H</th>" in result
        assert "<td>V</td>" in result

    def test_sanitize_preserves_void_tags(self) -> None:
        """Void tags like br and hr are preserved (自闭合标签保留)."""
        result = sanitize_html("<p>line1<br>line2</p><hr>")
        assert "<br>" in result
        assert "<hr>" in result


class TestSanitizeEventHandlers:
    """Event handler attributes are stripped (事件处理器属性被剥离)."""

    def test_sanitize_strips_event_handlers(self) -> None:
        """onclick and similar on* attributes are removed (onclick 等 on* 属性移除)."""
        result = sanitize_html('<div onclick="evil()" onload="bad()">text</div>')
        assert "onclick" not in result
        assert "onload" not in result
        assert "<div>text</div>" in result

    def test_sanitize_strips_onmouseover(self) -> None:
        """onmouseover is removed (onmouseover 被移除)."""
        result = sanitize_html('<span onmouseover="steal()">hover</span>')
        assert "onmouseover" not in result
        assert "<span>hover</span>" in result


class TestSanitizeHrefScheme:
    """href/src with dangerous schemes are stripped (危险 scheme 的 href/src 被剥离)."""

    def test_sanitize_validates_href_scheme(self) -> None:
        """javascript: href is stripped from anchor (javascript: href 被移除)."""
        result = sanitize_html('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in result
        assert "<a>click</a>" in result

    def test_sanitize_allows_safe_href(self) -> None:
        """https: href is preserved (https: href 保留)."""
        result = sanitize_html('<a href="https://example.com">link</a>')
        assert 'href="https://example.com"' in result

    def test_sanitize_blocks_vbscript_href(self) -> None:
        """vbscript: href is stripped (vbscript: href 被移除)."""
        result = sanitize_html('<a href="vbscript:MsgBox">click</a>')
        assert "vbscript:" not in result

    def test_sanitize_blocks_data_text_html_src(self) -> None:
        """data:text/html src is stripped (data:text/html src 被移除)."""
        result = sanitize_html('<img src="data:text/html,<script>alert(1)</script>">')
        assert "data:text/html" not in result

    def test_sanitize_blocks_control_char_in_href(self) -> None:
        """Control chars in href scheme are stripped before check (href 中控制字符先清除再校验)."""
        result = sanitize_html('<a href="java\tscript:alert(1)">click</a>')
        assert "javascript" not in result.lower()
        assert "<a>click</a>" in result


class TestSanitizeStyleAttribute:
    """Style attribute is stripped entirely (style 属性完全被剥离)."""

    def test_sanitize_strips_style_attribute(self) -> None:
        """style attribute is removed from tags (标签的 style 属性被移除)."""
        result = sanitize_html('<p style="color:red;background:url(evil)">text</p>')
        assert "style=" not in result
        assert "<p>text</p>" in result


class TestSanitizeUnsafeTags:
    """Unsafe tags like iframe, form, object are stripped (不安全标签被剥离)."""

    def test_sanitize_strips_iframe(self) -> None:
        """iframe tag is removed, content preserved (iframe 标签移除，内容保留)."""
        result = sanitize_html("<iframe src='evil.com'>inside</iframe><p>ok</p>")
        assert "<iframe" not in result
        assert "<p>ok</p>" in result

    def test_sanitize_strips_form(self) -> None:
        """form tag is removed (form 标签移除)."""
        result = sanitize_html("<form action='evil'><p>text</p></form>")
        assert "<form" not in result
        assert "<p>text</p>" in result

    def test_sanitize_strips_input(self) -> None:
        """input tag is removed (input 标签移除)."""
        result = sanitize_html('<input type="text" value="x"><p>ok</p>')
        assert "<input" not in result
        assert "<p>ok</p>" in result


class TestSanitizeEntityRefs:
    """Entity and character references are preserved (实体和字符引用保留)."""

    def test_sanitize_preserves_entity_ref(self) -> None:
        """Named entities like &amp; are preserved (命名实体保留)."""
        result = sanitize_html("<p>&amp; &lt; &gt;</p>")
        assert "&amp;" in result
        assert "&lt;" in result

    def test_sanitize_preserves_char_ref(self) -> None:
        """Numeric char refs like &#123; are preserved (数字字符引用保留)."""
        result = sanitize_html("<p>&#60;&#62;</p>")
        assert "&#60;" in result
        assert "&#62;" in result
