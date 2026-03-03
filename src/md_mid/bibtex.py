"""最小化 BibTeX 解析器：从 .bib 文件提取引用信息供 Rich Markdown 脚注使用。

Minimal BibTeX parser for extracting citation metadata for Rich
Markdown footnotes. Only extracts and formats common fields:
author, title, journal/booktitle, year.

仅支持常见字段（author, title, journal/booktitle, year）的提取与格式化。
"""

from __future__ import annotations

import re

# 匹配条目起始 @type{key, (Match entry start @type{key,)
_ENTRY_START_RE = re.compile(
    r"@(\w+)\{([^\s,{}]+)\s*,",
    re.IGNORECASE,
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


def _find_entry_body(text: str, start: int) -> str | None:
    """大括号平衡的条目体查找 (Find balanced-brace entry body).

    Starting after the opening ``{`` that follows the cite-key comma,
    scan forward keeping a brace depth counter and return everything
    up to the matching closing ``}``.

    从引用键逗号之后的 ``{`` 开始，向前扫描并保持大括号深度计数器，
    返回到匹配的闭合 ``}`` 之前的所有内容。

    Note: does not handle unbalanced braces inside quotes or comments.
    (注意：不处理引号或注释中的不平衡大括号。)

    Args:
        text: Full bib text (完整 bib 文本)
        start: Position right after the comma (逗号之后的位置)

    Returns:
        Body text or None if unbalanced (条目体文本，不平衡时为 None)
    """
    depth = 1
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
        i += 1
    return None


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
    for entry_match in _ENTRY_START_RE.finditer(bib_text):
        key = entry_match.group(2).strip()
        # 从逗号之后开始查找条目体 (Find body starting after comma)
        body = _find_entry_body(bib_text, entry_match.end())
        if body is None:
            continue
        fields = _extract_fields(body)
        result[key] = _format_entry(fields)
    return result


def _extract_fields(fields_text: str) -> dict[str, str]:
    """提取条目中的所有字段 (Extract all fields from entry)."""
    fields: dict[str, str] = {}
    for m in _FIELD_RE.finditer(fields_text):
        field_name = m.group(1).lower()
        # 取第一个非 None 的捕获组 (First non-None capture group)
        value = (m.group(2) or m.group(3) or m.group(4) or "").strip()
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
            last_name = name_parts[-1] if name_parts else first_author
        n_authors = len(author.split(" and "))
        suffix = " et al." if n_authors > 1 else ""
        parts.append(f"{last_name}{suffix}")

    # 标题 (Title)
    if title := fields.get("title", ""):
        parts.append(f'"{title}"')

    # 期刊/会议 (Journal or booktitle)
    venue = fields.get("journal") or fields.get("booktitle") or ""
    if venue:
        parts.append(venue)

    # 年份 (Year)
    if year := fields.get("year", ""):
        parts.append(year)

    # 去除末尾句号以避免 "et al.." 双句号 (Strip trailing period to avoid double period)
    cleaned = [p.rstrip(".") for p in parts]
    return ". ".join(cleaned) + "." if cleaned else ""
