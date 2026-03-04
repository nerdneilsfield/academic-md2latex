"""wenqiao CLI 入口 — 支持 convert / validate / format 子命令。

CLI entry point with subcommands: convert, validate, format.
Backward-compatible: ``wenqiao file.mid.md`` defaults to ``convert``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from wenqiao import __version__
from wenqiao.diagnostic import DiagCollector
from wenqiao.format_cmd import format_cmd
from wenqiao.pipeline import (
    build_config,
    create_renderer,
    inject_metadata,
    parse_and_process,
    resolve_bib,
)
from wenqiao.validate import validate_cmd

# ---------------------------------------------------------------------------
# DefaultGroup: implicit "convert" when first arg is not a subcommand
# (默认分组：首个参数非子命令时隐式使用 convert)
# ---------------------------------------------------------------------------


class DefaultGroup(click.Group):
    """Click Group that falls back to a default subcommand.

    If the first argument is not a known subcommand and does not start with
    ``-``, prepend ``convert`` so the single-command ``wenqiao FILE`` invocation
    still works (implicit convert).

    当首个参数不是已知子命令且不以 ``-`` 开头时，自动插入 ``convert``，
    保持 ``wenqiao FILE`` 的隐式 convert 调用方式兼容。
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Inject 'convert' default subcommand when needed (需要时注入默认子命令).

        Routes all args to ``convert`` unless the first token is a known
        subcommand name or a group-level option (--help / --version).
        This preserves option-first invocations like ``wenqiao -o out file``.
        (将所有参数路由到 convert，除非首个 token 是已知子命令或组级选项。)
        """
        if args and args[0] not in self.commands and args[0] not in ("--help", "--version"):
            args = ["convert", *args]
        return super().parse_args(ctx, args)


# ---------------------------------------------------------------------------
# Top-level CLI group (顶层 CLI 分组)
# ---------------------------------------------------------------------------


@click.group(cls=DefaultGroup, invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """wenqiao (文桥): Academic Markdown writing tool (学术 Markdown 写作工具)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# convert subcommand — the original main() body
# (convert 子命令 — 原 main() 函数体)
# ---------------------------------------------------------------------------


@cli.command("convert")
@click.argument("input", type=click.Path(path_type=Path))  # No exists=True: allow "-" for stdin
@click.option(
    "-t",
    "--target",
    type=click.Choice(["latex", "markdown", "html"]),
    default=None,
)
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None)
@click.option(
    "--mode",
    type=click.Choice(["full", "body", "fragment"]),
    default=None,
    help="Output mode (输出模式): full | body | fragment  [default: full]",
)
@click.option("--strict", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--dump-east", is_flag=True, default=False)
@click.option(
    "--bib",
    "bib_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
)
@click.option(
    "--heading-id-style",
    type=click.Choice(["attr", "html"]),
    default=None,
    help="Heading anchor style (标题锚点样式): attr ({#id}) | html (<h2 id>)",
)
@click.option(
    "--locale",
    type=click.Choice(["zh", "en"]),
    default=None,
    help="Label language (标签语言): zh | en  [default: zh]",
)
@click.option(
    "--preset",
    type=click.Choice(["zh", "en"]),
    default=None,
    help="Built-in preset (内置预设): zh | en",
)
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="LaTeX template file (LaTeX 模板文件, .yaml)",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="External config file (外部配置文件, wenqiao.yaml)",
)
@click.option(
    "--bibliography-mode",
    type=click.Choice(["auto", "standalone", "external", "none"]),
    default=None,
    help="Bibliography output strategy (参考文献输出策略)",
)
@click.option(
    "--generate-figures",
    "generate_figures",
    is_flag=True,
    default=False,
    help="Generate AI figures via runner before rendering (渲染前通过 runner 生成 AI 图片)",
)
@click.option(
    "--figures-config",
    "figures_config",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="TOML config for runner (runner 的 TOML 配置: API key, model 等)",
)
@click.option(
    "--force-regenerate",
    "force_regenerate",
    is_flag=True,
    default=False,
    help="Re-generate AI figures even if image files already exist (强制重新生成已有图片)",
)
def convert_cmd(
    input: Path,
    target: str | None,
    output: Path | None,
    mode: str | None,
    strict: bool,
    verbose: bool,
    dump_east: bool,
    bib_path: Path | None,
    heading_id_style: str | None,
    locale: str | None,
    preset: str | None,
    template_path: Path | None,
    config_path: Path | None,
    bibliography_mode: str | None,
    generate_figures: bool,
    figures_config: Path | None,
    force_regenerate: bool,
) -> None:
    """Convert academic Markdown to LaTeX/Markdown/HTML.

    转换学术 Markdown 为 LaTeX/Markdown/HTML。
    """
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
    east = parse_and_process(text, filename, diag)

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

    # 解析最终配置 (Resolve final config)
    try:
        cfg = build_config(
            east.metadata,
            cli_overrides=cli_dict if cli_dict else None,
            config_path=config_path,
            template_path=template_path,
            preset_name=preset,    # Built-in preset (内置预设)
            diag=diag,
        )
    except TypeError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise SystemExit(1)

    # Effective target: CLI > config > default (有效输出目标：CLI > 配置 > 默认 latex)
    effective_target: str = target if target is not None else cfg.target

    # Validate target before side effects (先校验目标再执行副作用)
    if effective_target not in ("latex", "markdown", "html"):
        click.echo(f"Target '{effective_target}' not yet implemented.", err=True)
        raise SystemExit(1)

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

    # Optional AI figure generation (可选 AI 图片生成)
    if generate_figures:
        from wenqiao.genfig import run_generate_figures
        from wenqiao.genfig_openai import OpenAIFigureRunner

        base_dir = Path(filename).parent if filename != "<stdin>" else Path.cwd()
        runner = OpenAIFigureRunner(config=figures_config)

        try:
            success, fail = run_generate_figures(
                east,
                base_dir=base_dir,
                runner=runner,
                force=force_regenerate,
                echo=lambda msg: click.echo(msg, err=True),
            )
        except (ImportError, OSError) as e:
            click.echo(f"[generate-figures] Runner failed: {e}", err=True)
            raise SystemExit(1)
        if fail > 0:
            click.echo(
                f"[generate-figures] {fail} figure(s) failed to generate.",
                err=True,
            )

    # Resolve bibliography (解析参考文献)
    bib: dict[str, str] = {}
    if bib_path is not None:
        try:
            bib = resolve_bib(bib_path)
        except Exception as exc:
            click.echo(f"[WARNING] Failed to parse {bib_path}: {exc}", err=True)

    # Inject metadata and render (注入元数据并渲染)
    inject_metadata(east, cfg, effective_target)
    renderer_obj = create_renderer(effective_target, cfg, bib, diag)
    result = renderer_obj.render(east)

    # Determine output suffix (确定输出后缀)
    suffix_map = {"latex": ".tex", "markdown": ".rendered.md", "html": ".html"}
    suffix = suffix_map[effective_target]
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


# Register subcommands (注册子命令)
cli.add_command(validate_cmd)
cli.add_command(format_cmd)

# Backward-compat alias (向后兼容别名)
main = cli
