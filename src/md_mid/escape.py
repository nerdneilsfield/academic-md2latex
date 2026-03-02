"""LaTeX 特殊字符转义。

两层策略：
1. escape_latex: 纯文本转义（逐字符替换）
2. escape_latex_with_protection: 先保护 LaTeX 命令，再转义剩余文本
"""

from __future__ import annotations

import re

LATEX_ESCAPE_MAP = {
    "#": r"\#",
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}

# 匹配 LaTeX 命令及其参数：\cmd, \cmd[opt]{arg}, \cmd{arg1}{arg2}
_CMD_RE = re.compile(
    r"\\[a-zA-Z@]+"          # \commandname
    r"(?:\s*\[[^\]]*\])*"    # 可选 [options] (可多个)
    r"(?:\s*\{[^{}]*\})*"    # 可选 {args} (可多个)
)


def escape_latex(text: str) -> str:
    """对纯文本片段做逐字符转义。"""
    out: list[str] = []
    for ch in text:
        out.append(LATEX_ESCAPE_MAP.get(ch, ch))
    return "".join(out)


def escape_latex_with_protection(text: str) -> str:
    """保护 LaTeX 命令后转义剩余文本（启发式模式）。"""
    protected: list[str] = []

    def _protect(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"\x00CMD{len(protected) - 1}\x00"

    text = _CMD_RE.sub(_protect, text)
    text = escape_latex(text)

    for i, seg in enumerate(protected):
        text = text.replace(f"\x00CMD{i}\x00", seg)

    return text
