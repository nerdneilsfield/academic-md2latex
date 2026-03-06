"""format 子命令的测试。

Tests for the format subcommand.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from wenqiao.cli import cli as main


def test_format_inplace(tmp_path: Path) -> None:
    """format writes back to input file (format 写回输入文件)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    result = CliRunner().invoke(main, ["format", str(src)])
    assert result.exit_code == 0
    # File should still be readable (文件应仍可读)
    content = src.read_text()
    assert "Hello" in content


def test_format_output_to_file(tmp_path: Path) -> None:
    """--output writes to specified path (--output 写入指定路径)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "formatted.md"
    result = CliRunner().invoke(main, ["format", str(src), "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert "Hello" in out.read_text()


def test_format_check_clean(tmp_path: Path) -> None:
    """--check on already-formatted file exits 0 (--check 已格式化文件退出码 0)."""
    src = tmp_path / "doc.mid.md"
    # First format the file (先格式化文件)
    src.write_text("# Hello\n\nWorld.\n")
    CliRunner().invoke(main, ["format", str(src)])
    # Now check — should be clean (检查 — 应该是干净的)
    result = CliRunner().invoke(main, ["format", str(src), "--check"])
    assert result.exit_code == 0


def test_format_check_dirty(tmp_path: Path) -> None:
    """--check on unformatted file exits 1 (--check 未格式化文件退出码 1)."""
    src = tmp_path / "doc.mid.md"
    # First format to get the canonical form (先格式化获取规范形式)
    src.write_text("# Hello\n\nWorld.\n")
    CliRunner().invoke(main, ["format", str(src)])
    canonical = src.read_text()
    # Modify to make it "dirty" (修改使其不同)
    src.write_text(canonical + "\n\n\n")
    result = CliRunner().invoke(main, ["format", str(src), "--check"])
    assert result.exit_code == 1


def test_format_check_no_write(tmp_path: Path) -> None:
    """--check does not modify the file (--check 不修改文件)."""
    src = tmp_path / "doc.mid.md"
    original = "# Hello\n\nWorld.\n"
    src.write_text(original)
    # Get formatted version (获取格式化版本)
    out = tmp_path / "ref.md"
    CliRunner().invoke(main, ["format", str(src), "-o", str(out)])
    formatted = out.read_text()
    # If they differ, --check should not modify src (如果不同，--check 不应修改源文件)
    if original != formatted:
        src.write_text(original)  # reset (重置)
        CliRunner().invoke(main, ["format", str(src), "--check"])
        assert src.read_text() == original


def test_format_diff_shows_changes(tmp_path: Path) -> None:
    """--diff prints unified diff (--diff 打印统一差异)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    # Format once to get canonical (先格式化获取规范形式)
    CliRunner().invoke(main, ["format", str(src)])
    canonical = src.read_text()
    # Make it dirty (弄脏)
    dirty = canonical + "\n\nextra line\n"
    src.write_text(dirty)
    result = CliRunner().invoke(main, ["format", str(src), "--diff"])
    assert result.exit_code == 0
    # Diff output should contain --- and +++ markers (差异输出应含标记)
    if canonical != dirty:
        assert "---" in result.output or "+++" in result.output


def test_format_fixes_math_backslash(tmp_path: Path) -> None:
    """format auto-fixes double backslash in math (自动修复数学双反斜杠)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n公式 $\\\\mathbf{R}$ 在这里。\n")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text()
    assert "$\\mathbf{R}$" in content
    assert "$\\\\mathbf{R}$" not in content


def test_format_fixes_math_spacing(tmp_path: Path) -> None:
    """format auto-fixes missing spaces around inline math (自动修复数学公式两侧空格)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n这是$x^2$公式。\n")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text()
    assert "这是 $x^2$ 公式" in content


def test_format_fixes_bold_spacing(tmp_path: Path) -> None:
    """format auto-fixes bold marker spacing (自动修复加重标记两侧空格)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n这是**重要**结论。\n")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text()
    assert "这是 **重要** 结论" in content


def test_format_no_rumdl_flag(tmp_path: Path) -> None:
    """--no-rumdl skips rumdl step without error (--no-rumdl 跳过 rumdl 无报错)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0


def test_format_stats_printed_when_enabled(tmp_path: Path) -> None:
    """--stats prints formatting statistics (--stats 输出统计信息)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n这是$x^2$公式。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl", "--stats"])
    assert result.exit_code == 0
    assert "[format] Stats" in result.output
    assert "changed=true" in result.output
    assert "diff=+" in result.output


def test_format_stats_with_check_mode(tmp_path: Path) -> None:
    """--check --stats still prints stats output (--check --stats 仍输出统计)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n这是$x^2$公式。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--check", "--stats", "--no-rumdl"])
    assert result.exit_code == 1
    assert "[format] Stats" in result.output
    assert "changed=true" in result.output


def test_format_fixes_unicode_math_symbols_in_text(tmp_path: Path) -> None:
    """format converts Unicode math symbols to LaTeX in plain text."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\na≤b，x≥y，u≠v。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert r"a$\leq$b" in content
    assert r"x$\geq$y" in content
    assert r"u$\neq$v" in content


def test_format_fixes_unicode_math_symbols_inside_math(tmp_path: Path) -> None:
    """format keeps symbols in math spans as bare LaTeX commands."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n关系 $a≤b$ 与 $x→y$。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert r"$a \leq b$" in content
    assert r"$x \to y$" in content
    assert "≤" not in content
    assert "→" not in content


def test_format_fixes_greek_letters_in_text(tmp_path: Path) -> None:
    """format converts bare Greek letters in text to inline LaTeX math."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n方差σ和均值μ。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert r"方差 $\sigma$ 和均值 $\mu$。" in content
    assert "σ" not in content
    assert "μ" not in content


def test_format_fixes_greek_letters_inside_math(tmp_path: Path) -> None:
    """format converts Greek letters in math spans to bare LaTeX commands."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n关系 $σ^2$ 与 $Δx$。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert r"$\sigma^2$" in content
    assert r"$\Delta x$" in content
    assert "σ" not in content
    assert "Δ" not in content


def test_format_does_not_touch_code_blocks_or_inline_code(tmp_path: Path) -> None:
    """format does not rewrite symbols inside code literals."""
    src = tmp_path / "doc.mid.md"
    src.write_text(
        "# 标题\n\n`a≤b`.\n\n```python\nexpr = 'x→y'\n```\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert "`a≤b`" in content
    assert "expr = 'x→y'" in content


def test_format_does_not_touch_greek_inside_code_literals(tmp_path: Path) -> None:
    """format does not rewrite Greek letters inside code literals."""
    src = tmp_path / "doc.mid.md"
    src.write_text(
        "# 标题\n\n`σ`.\n\n```python\nname = 'μ'\n```\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert "`σ`" in content
    assert "name = 'μ'" in content


def test_format_fixes_unicode_scripts_in_text(tmp_path: Path) -> None:
    """format converts Unicode superscripts/subscripts in text to inline math."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\nm² 与 x₀，还有 nⁿ。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert r"$m^2$" in content
    assert r"$x_0$" in content
    assert r"$n^n$" in content
    assert "²" not in content
    assert "₀" not in content
    assert "ⁿ" not in content


def test_format_fixes_unicode_scripts_inside_math(tmp_path: Path) -> None:
    """format converts Unicode scripts inside math spans to ^/_ notation."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# 标题\n\n关系 $x₁$ 和 $a²$。\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert r"$x_1$" in content
    assert r"$a^2$" in content
    assert "₁" not in content
    assert "²" not in content


def test_format_inserts_blank_lines_around_display_math(tmp_path: Path) -> None:
    """Display math block delimited by $$ is separated from surrounding text."""
    src = tmp_path / "doc.mid.md"
    src.write_text(
        "# 标题\n\n前文\n$$\na=b\n$$\n后文\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert "前文\n\n$$\na=b\n$$\n\n后文" in content


def test_format_keeps_display_math_blankline_rule_outside_code_fence(tmp_path: Path) -> None:
    """$$ inside fenced code block is not changed by display-math blankline fixer."""
    src = tmp_path / "doc.mid.md"
    src.write_text(
        "# 标题\n\n```tex\nx\n$$\ny\n$$\nz\n```\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["format", str(src), "--no-rumdl"])
    assert result.exit_code == 0
    content = src.read_text(encoding="utf-8")
    assert "x\n$$\ny\n$$\nz" in content
