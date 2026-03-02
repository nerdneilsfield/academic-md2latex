"""md-mid CLI 入口。"""

from __future__ import annotations

from pathlib import Path

import click

from md_mid import __version__
from md_mid.diagnostic import DiagCollector
from md_mid.parser import parse
from md_mid.comment import process_comments
from md_mid.latex import LaTeXRenderer


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option("-t", "--target", type=click.Choice(["latex", "markdown", "html"]), default="latex")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None)
@click.option("--mode", type=click.Choice(["full", "body", "fragment"]), default="full")
@click.option("--strict", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--dump-east", is_flag=True, default=False)
@click.version_option(version=__version__)
def main(
    input: Path,
    target: str,
    output: Path | None,
    mode: str,
    strict: bool,
    verbose: bool,
    dump_east: bool,
) -> None:
    """md-mid: 学术写作中间格式转换工具"""
    text = input.read_text(encoding="utf-8")
    diag = DiagCollector(str(input))

    doc = parse(text)
    east = process_comments(doc, str(input), diag=diag)

    if verbose:
        for d in diag.diagnostics:
            click.echo(str(d), err=True)

    if strict and diag.has_errors:
        for d in diag.errors:
            click.echo(str(d), err=True)
        raise SystemExit(1)

    if target == "latex":
        renderer = LaTeXRenderer(mode=mode)
        result = renderer.render(east)
    else:
        click.echo(f"Target '{target}' not yet implemented.", err=True)
        raise SystemExit(1)

    if output is None:
        output = input.with_suffix(".tex" if target == "latex" else f".{target}")

    output.write_text(result, encoding="utf-8")
    click.echo(f"Written to {output}")
