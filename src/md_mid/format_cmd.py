"""format 子命令：规范化学术 Markdown 源文件。

Format subcommand: normalize academic Markdown source files by
round-tripping through the parser and Markdown renderer.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

import click

from md_mid.diagnostic import DiagCollector
from md_mid.markdown import MarkdownRenderer
from md_mid.pipeline import parse_and_process


@click.command("format")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path (输出路径; default: overwrite input file)",
)
@click.option(
    "--check",
    is_flag=True,
    default=False,
    help="Check if file is formatted, exit 1 if not (检查格式化状态，未格式化时退出码 1)",
)
@click.option(
    "--diff",
    "show_diff",
    is_flag=True,
    default=False,
    help="Show unified diff of changes (显示统一差异)",
)
def format_cmd(
    input: Path,
    output: Path | None,
    check: bool,
    show_diff: bool,
) -> None:
    """Format an academic Markdown file (格式化学术 Markdown 文件).

    Round-trips through parser and Markdown renderer to normalize formatting.
    (通过解析器和 Markdown 渲染器往返以规范格式。)
    """
    original = input.read_text(encoding="utf-8")
    filename = str(input)
    diag = DiagCollector(filename)

    # Parse → process comments → render (解析 → 处理注释 → 渲染)
    east = parse_and_process(original, filename, diag)
    renderer = MarkdownRenderer(mode="full", diag=diag)
    formatted = renderer.render(east)

    # Compare original and formatted (比较原文与格式化结果)
    is_clean = original == formatted

    # Show diff if requested (按需显示差异)
    if show_diff and not is_clean:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            formatted.splitlines(keepends=True),
            fromfile=f"a/{input.name}",
            tofile=f"b/{input.name}",
        )
        sys.stdout.writelines(diff)

    # Check mode: exit 0 if clean, exit 1 if dirty, no write (检查模式)
    if check:
        if is_clean:
            click.echo(f"{input}: ok", err=True)
        else:
            click.echo(f"{input}: needs formatting (需要格式化)", err=True)
            raise SystemExit(1)
        return

    # Write output (写入输出)
    target = output if output is not None else input
    target.write_text(formatted, encoding="utf-8")
    click.echo(f"Formatted {target}")
