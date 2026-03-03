"""Lightweight HTML sanitizer using stdlib html.parser.

基于标准库 html.parser 的轻量 HTML 清洗器。

Uses a tag/attribute allowlist to strip dangerous elements and attributes
while preserving safe academic HTML structures.
使用标签/属性白名单剥离危险元素和属性，同时保留安全的学术 HTML 结构。
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

from md_mid.url_check import is_unsafe_url

# Safe HTML tags — normal and self-closing (安全 HTML 标签白名单)
_SAFE_TAGS: frozenset[str] = frozenset({
    "div", "span", "p", "br", "hr",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "ul", "ol", "li", "dl", "dt", "dd",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "pre", "code",
    "em", "strong", "sub", "sup",
    "figure", "figcaption",
    "details", "summary",
    "abbr", "mark", "del", "ins", "s", "b", "i", "u", "small",
    "caption", "colgroup", "col",
})

# Self-closing / void HTML tags (自闭合标签)
_VOID_TAGS: frozenset[str] = frozenset({
    "br", "hr", "img", "col",
})

# Tags whose content is stripped entirely (标签及内容全部剥离)
_STRIP_CONTENT_TAGS: frozenset[str] = frozenset({"script", "style"})

# Safe global attributes (安全全局属性白名单)
_SAFE_ATTRS: frozenset[str] = frozenset({
    "class", "id", "alt", "title",
    "colspan", "rowspan", "align", "valign",
    "width", "height",
    "role", "aria-label", "aria-hidden",
    "lang", "dir",
})

# Attributes that contain URLs — validated against scheme (URL 类属性 — 需校验 scheme)
_URL_ATTRS: frozenset[str] = frozenset({"href", "src"})


def _is_safe_url(url: str) -> bool:
    """Check whether a URL is safe (not using a dangerous scheme).

    检查 URL 是否安全（未使用危险 scheme）。

    Args:
        url: The URL string to validate (待校验的 URL 字符串)

    Returns:
        True if URL is safe (URL 安全则返回 True)
    """
    return not is_unsafe_url(url)


class _Sanitizer(HTMLParser):
    """HTMLParser subclass that builds allowlisted output.

    HTMLParser 子类，构建白名单过滤后的输出。
    """

    def __init__(self) -> None:
        """Initialize sanitizer state (初始化清洗器状态)."""
        super().__init__(convert_charrefs=False)
        self._out: list[str] = []
        # Depth counter for content-stripping tags (内容剥离标签深度计数器)
        self._strip_depth: int = 0

    def get_output(self) -> str:
        """Return the sanitized HTML string (返回清洗后的 HTML 字符串)."""
        return "".join(self._out)

    # -- Parser callbacks (解析器回调) --

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle opening tag — allow safe tags only (处理开始标签 — 仅允许安全标签)."""
        tag_lower = tag.lower()

        # Enter content-stripping mode for script/style (进入内容剥离模式)
        if tag_lower in _STRIP_CONTENT_TAGS:
            self._strip_depth += 1
            return

        # Suppress output while inside stripped tags (在剥离标签内部时抑制输出)
        if self._strip_depth > 0:
            return

        if tag_lower not in _SAFE_TAGS:
            return

        # Filter attributes (过滤属性)
        safe_attrs: list[str] = []
        for name, value in attrs:
            name_lower = name.lower()
            # Block event handlers (阻止事件处理器)
            if name_lower.startswith("on"):
                continue
            # Block style attribute entirely (完全阻止 style 属性)
            if name_lower == "style":
                continue
            # URL attributes — validate scheme (URL 属性 — 校验 scheme)
            if name_lower in _URL_ATTRS:
                url_val = value or ""
                if not _is_safe_url(url_val):
                    continue
                safe_attrs.append(f' {name_lower}="{escape(url_val, quote=True)}"')
                continue
            # General safe attributes (通用安全属性)
            if name_lower in _SAFE_ATTRS:
                attr_val = escape(value or "", quote=True)
                safe_attrs.append(f' {name_lower}="{attr_val}"')

        attr_str = "".join(safe_attrs)

        if tag_lower in _VOID_TAGS:
            self._out.append(f"<{tag_lower}{attr_str}>")
        else:
            self._out.append(f"<{tag_lower}{attr_str}>")

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tag (处理结束标签)."""
        tag_lower = tag.lower()

        if tag_lower in _STRIP_CONTENT_TAGS:
            if self._strip_depth > 0:
                self._strip_depth -= 1
            return

        if self._strip_depth > 0:
            return

        if tag_lower not in _SAFE_TAGS or tag_lower in _VOID_TAGS:
            return

        self._out.append(f"</{tag_lower}>")

    def handle_data(self, data: str) -> None:
        """Handle text data — suppress inside stripped tags (处理文本数据)."""
        if self._strip_depth > 0:
            return
        self._out.append(data)

    def handle_entityref(self, name: str) -> None:
        """Handle named entity reference like &amp; (处理命名实体引用)."""
        if self._strip_depth > 0:
            return
        self._out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """Handle numeric character reference like &#123; (处理数字字符引用)."""
        if self._strip_depth > 0:
            return
        self._out.append(f"&#{name};")


def sanitize_html(raw: str) -> str:
    """Sanitize HTML through tag/attribute allowlist.

    通过标签/属性白名单清洗 HTML。

    Args:
        raw: Raw HTML string to sanitize (待清洗的原始 HTML 字符串)

    Returns:
        Sanitized HTML string (清洗后的 HTML 字符串)
    """
    parser = _Sanitizer()
    parser.feed(raw)
    return parser.get_output()
