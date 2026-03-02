"""md-mid CLI 入口。"""

from __future__ import annotations

import json
from pathlib import Path

import click

from md_mid import __version__
from md_mid.comment import process_comments
from md_mid.diagnostic import DiagCollector
from md_mid.latex import LaTeXRenderer
from md_mid.markdown import MarkdownRenderer
from md_mid.parser import parse


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-t", "--target",
    type=click.Choice(["latex", "markdown", "html"]),
    default="latex",
)
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None)
@click.option("--mode", type=click.Choice(["full", "body", "fragment"]), default="full")
@click.option("--strict", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--dump-east", is_flag=True, default=False)
@click.option(
    "--bib", "bib_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
)
@click.option(
    "--heading-id-style",
    type=click.Choice(["attr", "html"]),
    default="attr",
)
@click.option(
    "--locale",
    type=click.Choice(["zh", "en"]),
    default="zh",
)
@click.version_option(version=__version__)
def main(
    input: Path,
    target: str,
    output: Path | None,
    mode: str,
    strict: bool,
    verbose: bool,
    dump_east: bool,
    bib_path: Path | None,
    heading_id_style: str,
    locale: str,
) -> None:
    """md-mid: 学术写作中间格式转换工具"""
    text = input.read_text(encoding="utf-8")
    diag = DiagCollector(str(input))

    # 解析并处理注释指令（Parse and process comment directives）
    doc = parse(text, diag=diag)
    east = process_comments(doc, str(input), diag=diag)

    # 转储 EAST JSON 并退出（Dump EAST as JSON and exit）
    if dump_east:
        click.echo(json.dumps(east.to_dict(), ensure_ascii=False, indent=2))
        return

    if verbose:
        for d in diag.diagnostics:
            click.echo(str(d), err=True)

    if strict and diag.has_errors:
        for d in diag.errors:
            click.echo(str(d), err=True)
        raise SystemExit(1)

    if target == "latex":
        renderer = LaTeXRenderer(mode=mode, diag=diag)
        result = renderer.render(east)
        suffix = ".tex"
    elif target == "markdown":
        # 解析 .bib 文件（Parse .bib file if provided）
        bib: dict[str, str] = {}
        if bib_path is not None:
            from md_mid.bibtex import parse_bib

            # 优雅处理无效 bib 文件 (Gracefully handle invalid .bib files)
            try:
                bib = parse_bib(bib_path.read_text(encoding="utf-8"))
            except Exception as exc:
                click.echo(
                    f"[WARNING] Failed to parse {bib_path}: {exc}", err=True
                )
        renderer_md = MarkdownRenderer(
            bib=bib,
            heading_id_style=heading_id_style,
            locale=locale,
            diag=diag,
        )
        result = renderer_md.render(east)
        suffix = ".rendered.md"
    else:
        click.echo(
            f"Target '{target}' not yet implemented.", err=True
        )
        raise SystemExit(1)

    if output is None:
        output = input.with_suffix(suffix)

    output.write_text(result, encoding="utf-8")
    click.echo(f"Written to {output}")
