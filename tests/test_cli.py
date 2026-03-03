import json
from pathlib import Path

from click.testing import CliRunner

from md_mid.cli import main


def test_help() -> None:
    """帮助输出正常（Help output works）."""
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "md-mid" in result.output or "input" in result.output.lower()


def test_version() -> None:
    """版本输出正常（Version output works）."""
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_convert_minimal(tmp_path) -> None:
    """基本转换功能（Basic conversion works）."""
    src = tmp_path / "test.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "test.tex"
    result = CliRunner().invoke(main, [str(src), "-o", str(out)])
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\section{Hello}" in content
    assert "World." in content


# ── Task 6: --dump-east ───────────────────────────────────────────────────────


def test_dump_east_outputs_json(tmp_path) -> None:
    """--dump-east 输出合法 JSON（--dump-east outputs valid JSON）."""
    src = tmp_path / "test.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    result = CliRunner().invoke(main, [str(src), "--dump-east"])
    assert result.exit_code == 0
    # 输出应为合法 JSON（Output should be valid JSON）
    data = json.loads(result.output)
    assert data["type"] == "document"
    assert "children" in data


def test_dump_east_contains_heading(tmp_path) -> None:
    """--dump-east JSON 包含标题节点（--dump-east JSON contains heading node）."""
    src = tmp_path / "test.mid.md"
    src.write_text("# My Section\n")
    result = CliRunner().invoke(main, [str(src), "--dump-east"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    children = data.get("children", [])
    heading_types = [c["type"] for c in children]
    assert "heading" in heading_types


def test_dump_east_does_not_write_file(tmp_path) -> None:
    """--dump-east 不写入 .tex 文件（--dump-east does not write .tex file）."""
    src = tmp_path / "test.mid.md"
    src.write_text("# Hello\n")
    CliRunner().invoke(main, [str(src), "--dump-east"])
    # 不应生成 .tex 文件（No .tex file should be generated）
    assert not (tmp_path / "test.tex").exists()


# ── Task 3: --strict mode ─────────────────────────────────────────────────────


def test_strict_mode_exits_on_error(tmp_path) -> None:
    """--strict 模式下有错误时退出码非零（--strict exits non-zero when errors exist）."""
    src = tmp_path / "test.mid.md"
    # 未匹配的 begin 会触发错误（Unmatched begin triggers error）
    src.write_text("<!-- begin: figure -->\nContent\n")
    result = CliRunner().invoke(main, [str(src), "--strict"])
    assert result.exit_code != 0


def test_strict_mode_no_error_exits_zero(tmp_path) -> None:
    """--strict 模式下无错误时退出码为零（--strict exits zero when no errors）."""
    src = tmp_path / "test.mid.md"
    src.write_text("# Clean Doc\n\nNo issues here.\n")
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(main, [str(src), "--strict", "-o", str(out)])
    assert result.exit_code == 0


# ── Task 8: -t markdown CLI ──────────────────────────────────────────────────


def test_markdown_target_basic(tmp_path) -> None:
    """基本 Markdown 转换（Basic markdown conversion works）."""
    src = tmp_path / "test.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "test.rendered.md"
    result = CliRunner().invoke(main, [str(src), "-t", "markdown", "-o", str(out)])
    assert result.exit_code == 0
    content = out.read_text()
    assert "# Hello" in content
    assert "World." in content


def test_markdown_target_citation_footnote(tmp_path) -> None:
    """引用转换为脚注（Citation converted to Markdown footnote）."""
    src = tmp_path / "test.mid.md"
    src.write_text("[Wang](cite:wang2024) says hello.\n")
    out = tmp_path / "test.rendered.md"
    result = CliRunner().invoke(main, [str(src), "-t", "markdown", "-o", str(out)])
    assert result.exit_code == 0
    content = out.read_text()
    assert "[^wang2024]" in content


def test_markdown_target_cross_ref(tmp_path) -> None:
    """交叉引用转换为 HTML 锚点（Cross-ref converted to HTML anchor）."""
    src = tmp_path / "test.mid.md"
    src.write_text("See [Figure 1](ref:fig:a) for details.\n")
    out = tmp_path / "test.rendered.md"
    result = CliRunner().invoke(main, [str(src), "-t", "markdown", "-o", str(out)])
    assert result.exit_code == 0
    content = out.read_text()
    assert '<a href="#fig:a">Figure 1</a>' in content


def test_markdown_default_output_suffix(tmp_path) -> None:
    """Markdown 默认输出 .rendered.md（Default output suffix）."""
    src = tmp_path / "test.mid.md"
    src.write_text("Hello.\n")
    result = CliRunner().invoke(main, [str(src), "-t", "markdown"])
    assert result.exit_code == 0
    # with_suffix replaces last suffix only (仅替换最后一个后缀)
    assert (tmp_path / "test.mid.rendered.md").exists()


def test_markdown_with_bib_file(tmp_path) -> None:
    """--bib 选项从 .bib 文件生成脚注（--bib uses .bib for footnotes）."""
    src = tmp_path / "test.mid.md"
    src.write_text("[Wang](cite:wang2024) says hello.\n")
    bib = tmp_path / "refs.bib"
    bib.write_text(
        '@article{wang2024, author={Wang, Alice},'
        ' title={Registration}, year={2024}}\n'
    )
    out = tmp_path / "out.rendered.md"
    result = CliRunner().invoke(
        main,
        [str(src), "-t", "markdown", "--bib", str(bib), "-o", str(out)],
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "Wang" in content
    assert "Registration" in content


# ── Task 4 (M2): Bad .bib file handling (无效 bib 文件处理) ────────────────────


def test_markdown_with_invalid_bib_no_crash(tmp_path) -> None:
    """无效 bib 不崩溃 (Invalid .bib produces warning, no crash)."""
    src = tmp_path / "t.mid.md"
    src.write_text("[W](cite:w) hello.\n")
    bib = tmp_path / "bad.bib"
    bib.write_bytes(b"\xff\xfe bad \x80")
    out = tmp_path / "out.rendered.md"
    result = CliRunner().invoke(
        main, [str(src), "-t", "markdown", "--bib", str(bib), "-o", str(out)]
    )
    assert result.exit_code == 0


# ── Phase 3 Task 5: --locale CLI option ──────────────────────────────────────


# ── Phase 3 Task 6: stdin/stdout support ─────────────────────────────────────


def test_stdin_input(tmp_path) -> None:
    """stdin 输入 (Read from stdin with -)."""
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(
        main, ["-", "-o", str(out)],
        input="# Hello\n\nWorld.\n",
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\section{Hello}" in content


def test_stdout_output(tmp_path) -> None:
    """stdout 输出 (Write to stdout with -o -)."""
    src = tmp_path / "t.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    result = CliRunner().invoke(main, [str(src), "-o", "-"])
    assert result.exit_code == 0
    assert "\\section{Hello}" in result.output


def test_stdin_stdout_pipe(tmp_path) -> None:
    """stdin→stdout 管道 (stdin to stdout pipe)."""
    result = CliRunner().invoke(
        main, ["-", "-o", "-"],
        input="# Hello\n\nWorld.\n",
    )
    assert result.exit_code == 0
    assert "\\section{Hello}" in result.output


def test_stdout_no_status_message(tmp_path) -> None:
    """-o - 不输出状态信息 (stdout mode suppresses 'Written to...')."""
    src = tmp_path / "t.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    result = CliRunner().invoke(main, [str(src), "-o", "-"])
    assert result.exit_code == 0
    assert "Written to" not in result.output


def test_markdown_locale_english(tmp_path) -> None:
    """--locale en 使用英文标签 (--locale en uses English labels)."""
    src = tmp_path / "t.mid.md"
    src.write_text(
        "![x](a.png)\n<!-- caption: Cap -->\n"
    )
    out = tmp_path / "out.rendered.md"
    result = CliRunner().invoke(
        main, [str(src), "-t", "markdown", "--locale", "en", "-o", str(out)]
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "Figure 1" in content


# ── Task 4 (Config): --template, --config, --bibliography-mode ───────────────


def test_cli_template_option(tmp_path: Path) -> None:
    """--template 加载 LaTeX 模板 (--template loads LaTeX template)."""
    tpl = tmp_path / "my.yaml"
    tpl.write_text("documentclass: IEEEtran\nclassoptions: [conference]\n")
    src = tmp_path / "t.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(
        main, [str(src), "-o", str(out), "--template", str(tpl)]
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\documentclass[conference]{IEEEtran}" in content


def test_cli_config_option_thematic_break(tmp_path: Path) -> None:
    """--config 加载外部配置 (--config loads external config)."""
    cfg = tmp_path / "md-mid.yaml"
    cfg.write_text("latex:\n  thematic-break: hrule\n")
    src = tmp_path / "t.mid.md"
    src.write_text("---\n\n# Section\n")
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(
        main, [str(src), "-o", str(out), "--config", str(cfg)]
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\hrule" in content


def test_cli_latex_locale_english(tmp_path: Path) -> None:
    """--locale en injects LaTeX caption overrides (--locale en 注入 LaTeX 图表名覆盖)."""
    src = tmp_path / "t.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(
        main, [str(src), "-t", "latex", "--locale", "en", "-o", str(out)]
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\renewcommand{\\figurename}{Figure}" in content
    assert "\\renewcommand{\\tablename}{Table}" in content


def test_cli_bibliography_mode_none(tmp_path: Path) -> None:
    """--bibliography-mode none 隐藏参考文献 (--bibliography-mode none suppresses bibliography)."""
    src = tmp_path / "t.mid.md"
    src.write_text("<!-- bibliography: refs.bib -->\n\n# Intro\n\nText.\n")
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(
        main, [str(src), "-o", str(out), "--bibliography-mode", "none"]
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\bibliography" not in content


def test_cli_config_title_author_injected(tmp_path: Path) -> None:
    """Config-file title/author/date/abstract appear in LaTeX output.

    配置文件元数据注入到 LaTeX 输出。
    """
    cfg = tmp_path / "md-mid.yaml"
    cfg.write_text(
        "title: Config Title\n"
        "author: Config Author\n"
        "date: 2026-01-01\n"
        "abstract: Config abstract text.\n"
    )
    src = tmp_path / "t.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(
        main, [str(src), "-o", str(out), "--config", str(cfg)]
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\title{Config Title}" in content
    assert "\\author{Config Author}" in content
    assert "\\date{2026-01-01}" in content
    assert "Config abstract text." in content


def test_cli_default_target_from_config(tmp_path: Path) -> None:
    """default-target in config selects the renderer (配置文件 default-target 选择渲染器).

    When --target is not given on CLI and config says default-target: markdown,
    the markdown renderer should be used. (未指定 --target 时，配置中的 default-target 生效。)
    """
    cfg = tmp_path / "md-mid.yaml"
    cfg.write_text("default-target: markdown\n")
    src = tmp_path / "t.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "out.rendered.md"
    result = CliRunner().invoke(
        main, [str(src), "-o", str(out), "--config", str(cfg)]
    )
    assert result.exit_code == 0
    content = out.read_text()
    # Markdown output, not LaTeX (Markdown 输出而非 LaTeX)
    assert "\\documentclass" not in content
    assert "# Hello" in content


def test_cli_explicit_mode_overrides_config(tmp_path: Path) -> None:
    """CLI --mode 覆盖配置文件 (CLI --mode overrides config file mode)."""
    cfg = tmp_path / "md-mid.yaml"
    cfg.write_text("latex:\n  mode: body\n")
    src = tmp_path / "t.mid.md"
    src.write_text("# Intro\n\nText.\n")
    out = tmp_path / "out.tex"
    result = CliRunner().invoke(
        main, [str(src), "-o", str(out), "--config", str(cfg), "--mode", "full"]
    )
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\documentclass" in content  # full 模式有前言 (full mode has preamble)
