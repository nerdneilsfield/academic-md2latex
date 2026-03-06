"""generate 子命令：并发生成 AI 图片。

Generate subcommand: concurrent AI figure generation from .mid.md files.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from wenqiao.diagnostic import DiagCollector
from wenqiao.genfig import FigureRunner, collect_jobs, run_generate_figures_async
from wenqiao.genfig_openai import OpenAIFigureRunner
from wenqiao.pipeline import parse_and_process


@click.command("generate")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--figures-config",
    "figures_config",
    type=click.Path(path_type=Path),
    default=None,
    help="TOML config for AI backend (AI 后端 TOML 配置: API key, model 等)",
)
@click.option(
    "--model",
    default=None,
    help="Override model name from config (覆盖 TOML 配置中的模型名)",
)
@click.option(
    "--base-url",
    "base_url",
    default=None,
    help="Override API base URL (覆盖 API 基础 URL)",
)
@click.option(
    "--api-key",
    "api_key",
    default=None,
    envvar="WENQIAO_API_KEY",
    help="API key; also reads WENQIAO_API_KEY env var (API 密钥；也读取 WENQIAO_API_KEY 环境变量)",
)
@click.option(
    "--type",
    "backend_type",
    type=click.Choice(["openai"]),
    default="openai",
    help="Backend type (后端类型; default: openai)",
)
@click.option(
    "--concurrency",
    default=4,
    show_default=True,
    help="Max concurrent generations (最大并发生成数)",
)
@click.option(
    "--start-id",
    "start_id",
    default=1,
    show_default=True,
    help="Start figure index, 1-based inclusive (起始图片序号，1-based，含)",
)
@click.option(
    "--end-id",
    "end_id",
    default=None,
    type=int,
    help="End figure index, 1-based inclusive; default: last (结束图片序号，1-based，含；默认末尾)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Re-generate even if output file exists (强制重新生成已有图片)",
)
@click.option(
    "--no-writeback",
    "no_writeback",
    is_flag=True,
    default=False,
    help="Skip writing <!-- ai-done: true --> to source file (跳过 ai-done 写回)",
)
def generate_cmd(
    input: Path,
    figures_config: Path | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    backend_type: str,
    concurrency: int,
    start_id: int,
    end_id: int | None,
    force: bool,
    no_writeback: bool,
) -> None:
    """Generate AI figures in a .mid.md file (生成 .mid.md 文件中的 AI 图片).

    Scans the file for figures with <!-- ai-generated: true --> and generates
    them concurrently using the configured AI backend.

    扫描文件中含 <!-- ai-generated: true --> 的图片，并发调用 AI 后端生成。
    """
    text = input.read_text(encoding="utf-8")
    filename = str(input)
    diag = DiagCollector(filename)
    doc = parse_and_process(text, filename, diag)

    base_dir = input.parent

    # Collect all jobs (force=True so skip logic is handled in async runner)
    # (force=True 采集所有，跳过逻辑交由异步 runner 处理)
    all_jobs = collect_jobs(doc, base_dir=base_dir, force=True)

    if not all_jobs:
        click.echo("[generate] No AI figures found (未找到 AI 图片).", err=True)
        return

    # Slice by start_id / end_id (1-based, inclusive) (按序号切片)
    start = max(0, start_id - 1)
    # No adjustment needed: 1-based inclusive end_id == Python exclusive slice bound.
    # (无需调整：1-based 含末端 end_id 恰好等于 Python 0-based 开区间切片上界)
    # e.g. end_id=2 → all_jobs[start:2] → indices 0..1 = figures 1..2 (1-based)
    end = end_id
    jobs = all_jobs[start:end]

    if not jobs:
        click.echo(
            f"[generate] No figures in range [{start_id}, {end_id}] "
            f"(序号范围内无图片).",
            err=True,
        )
        return

    # Set source_file for writeback (设置源文件路径用于写回)
    writeback = not no_writeback
    if writeback:
        for job in jobs:
            job.source_file = input

    # Build runner based on backend type (根据后端类型构建 runner)
    runner: FigureRunner
    if backend_type == "openai":
        runner = OpenAIFigureRunner(
            api_key=api_key,
            base_url=base_url,
            model=model,
            config=figures_config,
        )
    else:
        # Should never reach here given Click Choice constraint (Click 约束保证不会到达此处)
        click.echo(f"[generate] Unsupported backend type: {backend_type}", err=True)
        raise SystemExit(1)

    click.echo(
        f"[generate] {len(jobs)} figure(s) to generate "
        f"(concurrency={concurrency}) ...",
        err=True,
    )

    success, fail = asyncio.run(
        run_generate_figures_async(
            jobs,
            runner,
            concurrency=concurrency,
            force=force,
            writeback=writeback,
            echo=lambda msg: click.echo(msg, err=True),
        )
    )

    click.echo(
        f"[generate] Done: {success} succeeded, {fail} failed "
        f"(完成：{success} 成功，{fail} 失败).",
        err=True,
    )

    if fail > 0:
        raise SystemExit(1)
