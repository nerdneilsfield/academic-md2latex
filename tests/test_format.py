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
