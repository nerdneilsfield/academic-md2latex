"""md-mid CLI 入口。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from md_mid import __version__
from md_mid.comment import process_comments
from md_mid.config import load_config_file, load_template, resolve_config
from md_mid.diagnostic import DiagCollector
from md_mid.latex import LaTeXRenderer
from md_mid.markdown import MarkdownRenderer
from md_mid.parser import parse


@click.command()
@click.argument("input", type=click.Path(path_type=Path))  # No exists=True: allow "-" for stdin
@click.option(
    "-t", "--target",
    type=click.Choice(["latex", "markdown", "html"]),
    default="latex",
)
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None)
@click.option("--mode", type=click.Choice(["full", "body", "fragment"]), default=None,
              help="Output mode: full | body | fragment  (默认: full)")
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
    default=None,
    help="Heading anchor style: attr ({#id}) | html (<h2 id>)",
)
@click.option(
    "--locale",
    type=click.Choice(["zh", "en"]),
    default=None,
    help="Label language: zh | en  (默认: zh)",
)
@click.option(
    "--template", "template_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="LaTeX template file (.yaml)",
)
@click.option(
    "--config", "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="External config file (md-mid.yaml)",
)
@click.option(
    "--bibliography-mode",
    type=click.Choice(["auto", "standalone", "external", "none"]),
    default=None,
    help="Bibliography output strategy",
)
@click.version_option(version=__version__)
def main(
    input: Path,
    target: str,
    output: Path | None,
    mode: str | None,
    strict: bool,
    verbose: bool,
    dump_east: bool,
    bib_path: Path | None,
    heading_id_style: str | None,
    locale: str | None,
    template_path: Path | None,
    config_path: Path | None,
    bibliography_mode: str | None,
) -> None:
    """md-mid: 学术写作中间格式转换工具"""
    # 读取输入：stdin 或文件 (Read input: stdin or file)
    if str(input) == "-":
        text = sys.stdin.read()
        filename = "<stdin>"
    else:
        if not input.exists():
            click.echo(f"Error: Path '{input}' does not exist.", err=True)
            raise SystemExit(2)
        text = input.read_text(encoding="utf-8")
        filename = str(input)

    diag = DiagCollector(filename)

    # 解析并处理注释指令（Parse and process comment directives）
    doc = parse(text, diag=diag)
    east = process_comments(doc, filename, diag=diag)

    # 构建 CLI 覆盖字典 — 仅非 None 值参与覆盖
    # (Build CLI override dict — only non-None values participate)
    cli_dict: dict[str, object] = {}
    if mode is not None:
        cli_dict["mode"] = mode
    if locale is not None:
        cli_dict["locale"] = locale
    if heading_id_style is not None:
        cli_dict["heading_id_style"] = heading_id_style
    if bibliography_mode is not None:
        cli_dict["bibliography_mode"] = bibliography_mode

    # 加载配置层 (Load config layers)
    tpl_dict = load_template(template_path) if template_path else None
    cfg_dict = load_config_file(config_path) if config_path else None

    # 解析最终配置 (Resolve final config)
    cfg = resolve_config(
        cli_overrides=cli_dict if cli_dict else None,
        east_meta=east.metadata,
        config_dict=cfg_dict,
        template_dict=tpl_dict,
    )

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
        # Inject resolved preamble metadata into EAST for renderer use
        # (将解析后的元数据回注 EAST 供渲染器使用)
        east.metadata.update({
            "documentclass": cfg.documentclass,
            "classoptions": cfg.classoptions,
            "packages": cfg.packages,
            "package_options": cfg.package_options,
            "bibliography": cfg.bibliography,
            "bibstyle": cfg.bibstyle,
            "preamble": cfg.preamble,
            "bibliography_mode": cfg.bibliography_mode,
        })

        renderer = LaTeXRenderer(
            mode=cfg.mode,
            ref_tilde=cfg.ref_tilde,
            code_style=cfg.code_style,
            thematic_break=cfg.thematic_break,
            locale=cfg.locale,
            diag=diag,
        )
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
            heading_id_style=cfg.heading_id_style,
            locale=cfg.locale,
            mode=cfg.mode,
            diag=diag,
        )
        result = renderer_md.render(east)
        suffix = ".rendered.md"
    else:
        click.echo(
            f"Target '{target}' not yet implemented.", err=True
        )
        raise SystemExit(1)

    # 写入输出：stdout 或文件 (Write output: stdout or file)
    write_to_stdout = (output is not None and str(output) == "-") or (
        output is None and str(input) == "-"
    )
    if write_to_stdout:
        # stdout 模式不输出状态信息，避免污染管道 (No status message for pipe)
        click.echo(result, nl=False)
    else:
        if output is None:
            output = input.with_suffix(suffix)
        output.write_text(result, encoding="utf-8")
        click.echo(f"Written to {output}")
