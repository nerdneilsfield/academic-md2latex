"""lint — 自动修复 .mid.md 常见书写错误。

Auto-fix common writing errors in .mid.md files.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# CJK 字符集（用于所有规则的字符类）
# CJK character set (used in all spacing rules)
# ---------------------------------------------------------------------------

# 覆盖 CJK 统一汉字、扩展 A 区；不含全角标点（全角逗号句号等不需要补空格）
# Covers CJK Unified Ideographs, Extension A; excludes fullwidth punctuation
_CJK = r"\u4e00-\u9fff\u3400-\u4dbf"

# ---------------------------------------------------------------------------
# 规则 1: MATH-BACKSLASH — 数学块内双反斜杠修复
# Rule 1: MATH-BACKSLASH — fix double backslash inside math blocks
# ---------------------------------------------------------------------------

# 匹配块级 $$...$$ 和行内 $...$ (含换行; 先处理块级避免行内规则干扰)
# Match display $$...$$ and inline $...$ (DOTALL; process display first)
_DISPLAY_MATH_RE = re.compile(r"\$\$(.*?)\$\$", re.DOTALL)
_INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", re.DOTALL)

# 双反斜杠后跟字母 = LaTeX 命令双写错误 (double backslash before letter)
_DOUBLE_BS_RE = re.compile(r"\\\\([a-zA-Z])")


def _fix_math_content(m: re.Match[str]) -> str:
    """Replace \\\\cmd with \\cmd inside a matched math span.

    将匹配到的数学块内 \\\\cmd 替换为 \\cmd。
    """
    return _DOUBLE_BS_RE.sub(r"\\\1", m.group(0))


def fix_math_backslash(source: str) -> str:
    """Fix double backslash LaTeX commands inside math spans.

    修复数学块内的双反斜杠 LaTeX 命令（\\\\cmd → \\cmd）。

    Args:
        source: Raw .mid.md source text (原始 .mid.md 源文本)

    Returns:
        Source with double backslashes inside math corrected (修正后的文本)
    """
    # 先处理块级 $$ 避免行内规则干扰 (display first to avoid inline interference)
    result = _DISPLAY_MATH_RE.sub(_fix_math_content, source)
    result = _INLINE_MATH_RE.sub(_fix_math_content, result)
    return result


# ---------------------------------------------------------------------------
# 规则 1.5: MATH-SYMBOLS — Unicode 数学符号转 LaTeX
# Rule 1.5: MATH-SYMBOLS — convert Unicode math symbols to LaTeX
# ---------------------------------------------------------------------------

# Protect code spans/blocks so formatter won't touch literal code.
# 保护代码块与行内代码，避免替换字面量内容。
_FENCED_CODE_RE = re.compile(r"(?ms)^```[^\n]*\n.*?^```[ \t]*\n?")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

# Text context: wrap as inline math (文本环境：包成行内数学)
_TEXT_SYMBOL_MAP: dict[str, str] = {
    "≤": r"$\leq$",
    "≥": r"$\geq$",
    "≠": r"$\neq$",
    "≈": r"$\approx$",
    "±": r"$\pm$",
    "×": r"$\times$",
    "·": r"$\cdot$",
    "÷": r"$\div$",
    "∈": r"$\in$",
    "∉": r"$\notin$",
    "→": r"$\to$",
    "←": r"$\leftarrow$",
    "↔": r"$\leftrightarrow$",
    "⇒": r"$\Rightarrow$",
    "⇔": r"$\Leftrightarrow$",
    "∞": r"$\infty$",
    "∑": r"$\sum$",
    "∏": r"$\prod$",
}

# Math context: plain commands (数学环境：直接命令)
_MATH_SYMBOL_MAP: dict[str, str] = {
    "≤": r" \leq ",
    "≥": r" \geq ",
    "≠": r" \neq ",
    "≈": r" \approx ",
    "±": r" \pm ",
    "×": r" \times ",
    "·": r" \cdot ",
    "÷": r" \div ",
    "∈": r" \in ",
    "∉": r" \notin ",
    "→": r" \to ",
    "←": r" \leftarrow ",
    "↔": r" \leftrightarrow ",
    "⇒": r" \Rightarrow ",
    "⇔": r" \Leftrightarrow ",
    "∞": r"\infty",
    "∑": r"\sum",
    "∏": r"\prod",
}

# Greek letters in plain text and math contexts (希腊字母文本/数学环境映射)
_TEXT_GREEK_MAP: dict[str, str] = {
    "α": r"$\alpha$",
    "β": r"$\beta$",
    "γ": r"$\gamma$",
    "δ": r"$\delta$",
    "ε": r"$\epsilon$",
    "ζ": r"$\zeta$",
    "η": r"$\eta$",
    "θ": r"$\theta$",
    "ι": r"$\iota$",
    "κ": r"$\kappa$",
    "λ": r"$\lambda$",
    "μ": r"$\mu$",
    "ν": r"$\nu$",
    "ξ": r"$\xi$",
    "ο": r"$o$",
    "π": r"$\pi$",
    "ρ": r"$\rho$",
    "ς": r"$\sigma$",
    "σ": r"$\sigma$",
    "τ": r"$\tau$",
    "υ": r"$\upsilon$",
    "φ": r"$\phi$",
    "χ": r"$\chi$",
    "ψ": r"$\psi$",
    "ω": r"$\omega$",
    "Α": r"$A$",
    "Β": r"$B$",
    "Γ": r"$\Gamma$",
    "Δ": r"$\Delta$",
    "Ε": r"$E$",
    "Ζ": r"$Z$",
    "Η": r"$H$",
    "Θ": r"$\Theta$",
    "Ι": r"$I$",
    "Κ": r"$K$",
    "Λ": r"$\Lambda$",
    "Μ": r"$M$",
    "Ν": r"$N$",
    "Ξ": r"$\Xi$",
    "Ο": r"$O$",
    "Π": r"$\Pi$",
    "Ρ": r"$P$",
    "Σ": r"$\Sigma$",
    "Τ": r"$T$",
    "Υ": r"$\Upsilon$",
    "Φ": r"$\Phi$",
    "Χ": r"$X$",
    "Ψ": r"$\Psi$",
    "Ω": r"$\Omega$",
    "ϵ": r"$\varepsilon$",
    "ϑ": r"$\vartheta$",
    "ϕ": r"$\varphi$",
    "ϖ": r"$\varpi$",
    "ϱ": r"$\varrho$",
    "ϰ": r"$\varkappa$",
}

_MATH_GREEK_MAP: dict[str, str] = {
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\epsilon",
    "ζ": r"\zeta",
    "η": r"\eta",
    "θ": r"\theta",
    "ι": r"\iota",
    "κ": r"\kappa",
    "λ": r"\lambda",
    "μ": r"\mu",
    "ν": r"\nu",
    "ξ": r"\xi",
    "ο": "o",
    "π": r"\pi",
    "ρ": r"\rho",
    "ς": r"\sigma",
    "σ": r"\sigma",
    "τ": r"\tau",
    "υ": r"\upsilon",
    "φ": r"\phi",
    "χ": r"\chi",
    "ψ": r"\psi",
    "ω": r"\omega",
    "Α": "A",
    "Β": "B",
    "Γ": r"\Gamma",
    "Δ": r"\Delta",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Θ": r"\Theta",
    "Ι": "I",
    "Κ": "K",
    "Λ": r"\Lambda",
    "Μ": "M",
    "Ν": "N",
    "Ξ": r"\Xi",
    "Ο": "O",
    "Π": r"\Pi",
    "Ρ": "P",
    "Σ": r"\Sigma",
    "Τ": "T",
    "Υ": r"\Upsilon",
    "Φ": r"\Phi",
    "Χ": "X",
    "Ψ": r"\Psi",
    "Ω": r"\Omega",
    "ϵ": r"\varepsilon",
    "ϑ": r"\vartheta",
    "ϕ": r"\varphi",
    "ϖ": r"\varpi",
    "ϱ": r"\varrho",
    "ϰ": r"\varkappa",
}

# Unicode superscript/subscript maps (Unicode 上下标映射)
_SUPERSCRIPT_MAP: dict[str, str] = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "ⁿ": "n",
    "ⁱ": "i",
}

_SUBSCRIPT_MAP: dict[str, str] = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "ₙ": "n",
    "ₖ": "k",
    "ₗ": "l",
    "ₘ": "m",
    "ₜ": "t",
    "ₓ": "x",
}

_SUP_CHARS = "".join(_SUPERSCRIPT_MAP.keys())
_SUB_CHARS = "".join(_SUBSCRIPT_MAP.keys())
_SUP_RUN_RE = re.compile(f"([{re.escape(_SUP_CHARS)}]+)")
_SUB_RUN_RE = re.compile(f"([{re.escape(_SUB_CHARS)}]+)")
_TEXT_BASE_SUP_RE = re.compile(rf"([A-Za-z0-9\u0370-\u03FF])([{re.escape(_SUP_CHARS)}]+)")
_TEXT_BASE_SUB_RE = re.compile(rf"([A-Za-z0-9\u0370-\u03FF])([{re.escape(_SUB_CHARS)}]+)")


def _replace_symbols(text: str, mapping: dict[str, str]) -> str:
    """Apply symbol replacement mapping (应用符号替换映射)."""
    out = text
    for src, dst in mapping.items():
        out = out.replace(src, dst)
    return out


def _replace_math_greek(text: str) -> str:
    """Replace Greek letters in math while guarding command boundaries.

    在数学环境内替换希腊字母，并避免命令与后续字母粘连。
    """
    chars = list(text)
    out: list[str] = []
    total = len(chars)
    for i, ch in enumerate(chars):
        rep = _MATH_GREEK_MAP.get(ch)
        if rep is None:
            out.append(ch)
            continue
        if rep.startswith("\\") and i + 1 < total:
            nxt = chars[i + 1]
            if nxt.isascii() and nxt.isalpha():
                out.append(rep + " ")
                continue
        out.append(rep)
    return "".join(out)


def _script_run_to_latex(run: str, marker: str) -> str:
    """Convert Unicode script run to LaTeX exponent/subscript segment."""
    mapping = _SUPERSCRIPT_MAP if marker == "^" else _SUBSCRIPT_MAP
    converted = "".join(mapping.get(ch, "") for ch in run)
    if not converted:
        return ""
    if len(converted) == 1:
        return f"{marker}{converted}"
    return f"{marker}{{{converted}}}"


def _replace_math_scripts(text: str) -> str:
    """Replace script Unicode chars inside existing math spans."""
    out = _SUP_RUN_RE.sub(lambda m: _script_run_to_latex(m.group(1), "^"), text)
    out = _SUB_RUN_RE.sub(lambda m: _script_run_to_latex(m.group(1), "_"), out)
    return out


def _text_base_to_math(base: str) -> str:
    """Convert text base char to math-safe base (e.g., Greek -> command)."""
    return _MATH_GREEK_MAP.get(base, base)


def _replace_text_scripts(text: str) -> str:
    """Replace script Unicode chars in plain text, wrapping into inline math."""

    def _base_sup(m: re.Match[str]) -> str:
        base = _text_base_to_math(m.group(1))
        sup = _script_run_to_latex(m.group(2), "^")
        return f"${base}{sup}$"

    def _base_sub(m: re.Match[str]) -> str:
        base = _text_base_to_math(m.group(1))
        sub = _script_run_to_latex(m.group(2), "_")
        return f"${base}{sub}$"

    out = _TEXT_BASE_SUP_RE.sub(_base_sup, text)
    out = _TEXT_BASE_SUB_RE.sub(_base_sub, out)
    out = _SUP_RUN_RE.sub(lambda m: f"${_script_run_to_latex(m.group(1), '^')}$", out)
    out = _SUB_RUN_RE.sub(lambda m: f"${_script_run_to_latex(m.group(1), '_')}$", out)
    return out


def _protect_matches(
    source: str, pattern: re.Pattern[str], *, prefix: str
) -> tuple[str, list[str]]:
    """Replace protected matches with placeholders (用占位符保护匹配片段)."""
    slots: list[str] = []

    def _repl(m: re.Match[str]) -> str:
        idx = len(slots)
        slots.append(m.group(0))
        return f"\x00{prefix}{idx}\x00"

    return pattern.sub(_repl, source), slots


def _restore_matches(source: str, slots: list[str], *, prefix: str) -> str:
    """Restore placeholders back to original segments (恢复占位符片段)."""
    out = source
    for idx, seg in enumerate(slots):
        out = out.replace(f"\x00{prefix}{idx}\x00", seg)
    return out


def _fix_math_symbols_in_span(m: re.Match[str]) -> str:
    """Convert symbols inside a single math span (替换单个数学片段内符号)."""
    text = _replace_math_scripts(m.group(0))
    text = _replace_math_greek(text)
    return _replace_symbols(text, _MATH_SYMBOL_MAP)


def fix_math_symbols(source: str) -> str:
    """Convert common Unicode math symbols to LaTeX.

    将常见 Unicode 数学符号转换为 LaTeX：
    - 数学环境内：`≤` → `\\leq`
    - 普通文本中：`≤` → `$\\leq$`
    - 代码块/行内代码中不替换
    """
    # 保护 fenced code (保护代码块)
    protected, fenced_slots = _protect_matches(source, _FENCED_CODE_RE, prefix="FENCE")
    # 保护 inline code (保护行内代码)
    protected, inline_slots = _protect_matches(protected, _INLINE_CODE_RE, prefix="INLINE")

    # 数学环境先替换为裸命令，再替换剩余文本为 $...$
    # Replace in math first as plain commands, then text context as $...$
    protected = _DISPLAY_MATH_RE.sub(_fix_math_symbols_in_span, protected)
    protected = _INLINE_MATH_RE.sub(_fix_math_symbols_in_span, protected)

    # Protect existing math spans, then normalize plain-text symbols/scripts.
    protected, dmath_slots = _protect_matches(protected, _DISPLAY_MATH_RE, prefix="DMATH")
    protected, imath_slots = _protect_matches(protected, _INLINE_MATH_RE, prefix="IMATH")
    protected = _replace_text_scripts(protected)
    protected = _replace_symbols(protected, _TEXT_GREEK_MAP)
    protected = _replace_symbols(protected, _TEXT_SYMBOL_MAP)
    protected = _restore_matches(protected, imath_slots, prefix="IMATH")
    protected = _restore_matches(protected, dmath_slots, prefix="DMATH")

    # 按逆序恢复：先 inline code 后 fenced code
    protected = _restore_matches(protected, inline_slots, prefix="INLINE")
    protected = _restore_matches(protected, fenced_slots, prefix="FENCE")
    return protected


# ---------------------------------------------------------------------------
# 规则 1.6: DISPLAY-MATH-BLANKLINES — $$ 数学块与正文分隔空行
# Rule 1.6: DISPLAY-MATH-BLANKLINES — ensure blank lines around $$ blocks
# ---------------------------------------------------------------------------


def _fix_display_math_blanklines_text(source: str) -> str:
    """Ensure a blank line before opening $$ and after closing $$.

    仅处理“独立一行且内容为 $$”的定界符。
    """
    has_trailing_newline = source.endswith("\n")
    lines = source.splitlines()
    out: list[str] = []
    in_display = False

    for i, line in enumerate(lines):
        if line.strip() == "$$":
            if not in_display:
                # Opening $$: ensure previous line is blank.
                if out and out[-1].strip() != "":
                    out.append("")
                out.append(line)
                in_display = True
            else:
                # Closing $$: emit delimiter then ensure next line is blank.
                out.append(line)
                if i + 1 < len(lines) and lines[i + 1].strip() != "":
                    out.append("")
                in_display = False
            continue

        out.append(line)

    result = "\n".join(out)
    if has_trailing_newline:
        result += "\n"
    return result


def fix_display_math_blanklines(source: str) -> str:
    """Ensure blank lines around display math blocks delimited by $$ lines.

    保证 $$ 数学块前后与正文用空行分隔；代码块和行内代码不处理。
    """
    protected, fenced_slots = _protect_matches(source, _FENCED_CODE_RE, prefix="FENCE")
    protected, inline_slots = _protect_matches(protected, _INLINE_CODE_RE, prefix="INLINE")
    protected = _fix_display_math_blanklines_text(protected)
    protected = _restore_matches(protected, inline_slots, prefix="INLINE")
    protected = _restore_matches(protected, fenced_slots, prefix="FENCE")
    return protected


# ---------------------------------------------------------------------------
# 规则 2: MATH-SPACING — 中文紧贴数学公式两侧补空格
# Rule 2: MATH-SPACING — insert space between CJK and math markers
# ---------------------------------------------------------------------------

# 行内 $（排除 $$）紧贴中文：前补空格 (CJK before inline $)
_BEFORE_INLINE_MATH_RE = re.compile(r"([" + _CJK + r"])(\$(?!\$))")
# 行内 $（排除 $$）紧贴中文：后补空格 (CJK after inline $)
_AFTER_INLINE_MATH_RE = re.compile(r"(?<!\$)(\$(?!\$))([" + _CJK + r"])")


def fix_math_spacing(source: str) -> str:
    """Insert a space between CJK characters and inline math markers.

    在中文字符与行内数学符号之间插入空格。

    Args:
        source: Raw .mid.md source text (原始 .mid.md 源文本)

    Returns:
        Source with spaces inserted around inline math (修正后的文本)
    """
    result = _BEFORE_INLINE_MATH_RE.sub(r"\1 \2", source)
    result = _AFTER_INLINE_MATH_RE.sub(r"\1 \2", result)
    return result


# ---------------------------------------------------------------------------
# 规则 3: BOLD-SPACING — 中文紧贴 **加重** 两侧补空格
# Rule 3: BOLD-SPACING — insert space between CJK and bold spans
# ---------------------------------------------------------------------------

# 匹配完整加重区间 **content**（首尾都不是空白，避免把闭合 ** 误判为开头）
# Match a complete bold span **content** (no leading/trailing spaces in content)
_BOLD_SPAN = r"(?<!\*)\*\*[^\s*\n](?:[^*\n]*?[^\s*\n])?\*\*(?!\*)"

# 中文紧贴加重区间之前（前补空格）(CJK immediately before **span**)
_BOLD_BEFORE_CJK_RE = re.compile(r"([" + _CJK + r"])(" + _BOLD_SPAN + r")")
# 加重区间后紧贴中文（后补空格）(**span** immediately before CJK)
_BOLD_AFTER_CJK_RE = re.compile(r"(" + _BOLD_SPAN + r")([" + _CJK + r"])")


def fix_bold_spacing(source: str) -> str:
    """Insert a space between CJK characters and bold spans (**text**).

    在中文字符与完整加重区间 **text** 之间插入空格（前后两侧）。
    使用完整区间匹配，并限制内容首尾非空白，避免跨区间误匹配。

    Args:
        source: Raw .mid.md source text (原始 .mid.md 源文本)

    Returns:
        Source with spaces inserted around bold spans (修正后的文本)
    """
    result = _BOLD_BEFORE_CJK_RE.sub(r"\1 \2", source)
    result = _BOLD_AFTER_CJK_RE.sub(r"\1 \2", result)
    return result


# ---------------------------------------------------------------------------
# 规则 4: ITALIC-SPACING — 中文紧贴 *斜体* 两侧补空格
# Rule 4: ITALIC-SPACING — insert space between CJK and italic spans
# ---------------------------------------------------------------------------

# 匹配完整斜体区间 *content*（孤立 *，且内容首尾非空白）
# Match a complete italic span *content* (lone * markers, no leading/trailing spaces)
_ITALIC_SPAN = r"(?<!\*)\*(?!\*)[^\s*\n](?:[^*\n]*?[^\s*\n])?(?<!\*)\*(?!\*)"

# 中文紧贴斜体区间之前（前补空格）(CJK immediately before *span*)
_ITALIC_BEFORE_CJK_RE = re.compile(r"([" + _CJK + r"])(" + _ITALIC_SPAN + r")")
# 斜体区间后紧贴中文（后补空格）(*span* immediately before CJK)
_ITALIC_AFTER_CJK_RE = re.compile(r"(" + _ITALIC_SPAN + r")([" + _CJK + r"])")


def fix_italic_spacing(source: str) -> str:
    """Insert a space between CJK characters and italic spans (*text*).

    在中文字符与完整斜体区间 *text* 之间插入空格（前后两侧）。
    使用孤立 * 的完整区间匹配，避免与 ** 加重标记冲突。

    Args:
        source: Raw .mid.md source text (原始 .mid.md 源文本)

    Returns:
        Source with spaces inserted around italic spans (修正后的文本)
    """
    result = _ITALIC_BEFORE_CJK_RE.sub(r"\1 \2", source)
    result = _ITALIC_AFTER_CJK_RE.sub(r"\1 \2", result)
    return result


# ---------------------------------------------------------------------------
# 公共入口：按序应用所有修复 (Public entry: apply all fixes in order)
# ---------------------------------------------------------------------------
#
# 顺序说明 (Order rationale):
#   1. fix_math_backslash   — 修数学内容，不改结构
#   2. fix_math_symbols     — Unicode 数学符号转 LaTeX
#   3. fix_display_math_blanklines — $$ 数学块前后补空行
#   4. fix_math_spacing     — 数学标记周围补空格
#   5. fix_bold_spacing     — ** 周围补空格（先于 italic，防止 ** 被误识别为 *）
#   6. fix_italic_spacing   — * 周围补空格（此时 ** 已有空格，lookahead 安全）


def fix_common_errors(source: str, *, fix_emphasis_spacing: bool = True) -> str:
    """Apply all common-error fixes in order.

    按序应用所有常见错误修复。

    Args:
        source: Raw .mid.md source text (原始 .mid.md 源文本)
        fix_emphasis_spacing: Whether to apply bold/italic spacing fixes.
            (是否应用加重/斜体两侧空格修复)

    Returns:
        Fixed source text (修正后的文本)
    """
    source = fix_math_backslash(source)
    source = fix_math_symbols(source)
    source = fix_display_math_blanklines(source)
    source = fix_math_spacing(source)
    if fix_emphasis_spacing:
        source = fix_bold_spacing(source)
        source = fix_italic_spacing(source)
    return source
