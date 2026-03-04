"""Tests for shared URL safety check (URL 安全检查测试)."""

from __future__ import annotations

from wenqiao.url_check import is_unsafe_url


class TestIsUnsafeUrl:
    """is_unsafe_url blocks dangerous schemes (阻止危险 scheme 测试)."""

    def test_javascript_blocked(self) -> None:
        """javascript: scheme is blocked (javascript: 被阻止)."""
        assert is_unsafe_url("javascript:alert(1)") is True

    def test_vbscript_blocked(self) -> None:
        """vbscript: scheme is blocked (vbscript: 被阻止)."""
        assert is_unsafe_url("vbscript:MsgBox") is True

    def test_data_text_html_blocked(self) -> None:
        """data:text/html is blocked (data:text/html 被阻止)."""
        assert is_unsafe_url("data:text/html,<script>x</script>") is True

    def test_data_svg_blocked(self) -> None:
        """data:image/svg+xml is blocked (data:image/svg+xml 被阻止)."""
        assert is_unsafe_url("data:image/svg+xml,<svg onload='x'>") is True

    def test_control_chars_bypass_blocked(self) -> None:
        """Control chars in scheme don't bypass check (控制字符不绕过)."""
        assert is_unsafe_url("java\tscript:alert(1)") is True
        assert is_unsafe_url("java\x00script:alert(1)") is True

    def test_whitespace_bypass_blocked(self) -> None:
        """Leading whitespace doesn't bypass check (前导空白不绕过)."""
        assert is_unsafe_url("  javascript:alert(1)") is True

    def test_case_insensitive(self) -> None:
        """Check is case-insensitive (检查不区分大小写)."""
        assert is_unsafe_url("JAVASCRIPT:alert(1)") is True
        assert is_unsafe_url("Data:Image/SVG+XML,<svg>") is True

    def test_safe_https(self) -> None:
        """https URL is safe (https URL 安全)."""
        assert is_unsafe_url("https://example.com") is False

    def test_safe_http(self) -> None:
        """http URL is safe (http URL 安全)."""
        assert is_unsafe_url("http://example.com") is False

    def test_safe_mailto(self) -> None:
        """mailto URL is safe (mailto URL 安全)."""
        assert is_unsafe_url("mailto:user@example.com") is False

    def test_safe_relative(self) -> None:
        """Relative URL is safe (相对 URL 安全)."""
        assert is_unsafe_url("./image.png") is False

    def test_safe_anchor(self) -> None:
        """Anchor URL is safe (锚点 URL 安全)."""
        assert is_unsafe_url("#section-1") is False
