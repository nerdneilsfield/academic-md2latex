"""最小化 BibTeX 解析器：从 .bib 文件提取引用信息供 Rich Markdown 脚注使用。

Minimal BibTeX parser for extracting citation metadata for Rich
Markdown footnotes. Only extracts and formats common fields:
author, title, journal/booktitle, year.

仅支持常见字段（author, title, journal/booktitle, year）的提取与格式化。
"""

from __future__ import annotations

import re

# 匹配 @type{key, ...} 条目 (Match @type{key, ...} entries)
_ENTRY_RE = re.compile(
    r"@\w+\{(\w+)\s*,([^@]*)\}",
    re.DOTALL | re.IGNORECASE,
)

# 匹配 field = {value} 或 field = "value" 或 field = bare
# (Match field = {value}, field = "value", or field = bare)
_FIELD_RE = re.compile(
    r"(\w+)\s*=\s*(?:"
    r"\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
    r"|\"([^\"]*)\""
    r"|(\S[^,\n]*))",
    re.DOTALL,
)


def parse_bib(bib_text: str) -> dict[str, str]:
    """解析 .bib 文件内容，返回 key → 格式化引用字符串的映射。

    Parse .bib file content, return key → formatted citation string
    mapping.

    Args:
        bib_text: Raw .bib file content (.bib 文件原始内容)

    Returns:
        Dict mapping cite key → one-line citation string
        (引用键 → 单行引用字符串的字典)
    """
    result: dict[str, str] = {}
    for entry_match in _ENTRY_RE.finditer(bib_text):
        key = entry_match.group(1).strip()
        fields_text = entry_match.group(2)
        fields = _extract_fields(fields_text)
        result[key] = _format_entry(fields)
    return result


def _extract_fields(fields_text: str) -> dict[str, str]:
    """提取条目中的所有字段 (Extract all fields from entry)."""
    fields: dict[str, str] = {}
    for m in _FIELD_RE.finditer(fields_text):
        field_name = m.group(1).lower()
        # 取第一个非 None 的捕获组 (First non-None capture group)
        value = (
            m.group(2) or m.group(3) or m.group(4) or ""
        ).strip()
        fields[field_name] = value
    return fields


def _format_entry(fields: dict[str, str]) -> str:
    """将字段字典格式化为一行引用字符串。

    Format field dict to one-line citation string.
    """
    parts: list[str] = []

    # 作者（取第一作者 last name）(Author: first author last name)
    if author := fields.get("author", ""):
        first_author = author.split(" and ")[0].strip()
        # "Last, First" 或 "First Last" 格式
        # ("Last, First" or "First Last" format)
        if "," in first_author:
            last_name = first_author.split(",")[0].strip()
        else:
            name_parts = first_author.split()
            last_name = (
                name_parts[-1] if name_parts else first_author
            )
        n_authors = len(author.split(" and "))
        suffix = " et al." if n_authors > 1 else ""
        parts.append(f"{last_name}{suffix}")

    # 标题 (Title)
    if title := fields.get("title", ""):
        parts.append(f'"{title}"')

    # 期刊/会议 (Journal or booktitle)
    venue = (
        fields.get("journal") or fields.get("booktitle") or ""
    )
    if venue:
        parts.append(venue)

    # 年份 (Year)
    if year := fields.get("year", ""):
        parts.append(year)

    return ". ".join(parts) + "." if parts else ""
