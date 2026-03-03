"""Optional AI figure generation helper.

可选 AI 图片生成辅助模块。
Walks the EAST for Figure/Image nodes with ai-generated: true and calls
the nanobanana-compatible runner to generate them.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from md_mid.nodes import Document, Figure, Image, Node


@dataclass
class FigureJob:
    """One figure to generate (待生成的一个图片作业).

    Attributes:
        src: Relative image path from document (相对图片路径)
        output_path: Resolved absolute path to write the image (绝对输出路径)
        prompt: Generation prompt (生成 prompt)
        model: Model name override (模型名覆盖，可选)
        params: Extra generation parameters (额外生成参数，可选)
    """

    src: str
    output_path: Path
    prompt: str
    model: str | None
    params: dict[str, Any] | None


def _walk(node: Node) -> Iterator[Node]:
    """Recursively yield all descendant nodes (递归生成所有后代节点).

    Args:
        node: Root node (根节点)

    Yields:
        All descendant nodes depth-first (深度优先生成所有后代节点)
    """
    yield node
    for child in node.children:
        yield from _walk(child)


def collect_jobs(
    doc: Document,
    base_dir: Path,
    force: bool = False,
) -> list[FigureJob]:
    """Collect figure generation jobs from document EAST.

    从文档 EAST 中收集待生成的图片作业列表。

    Args:
        doc: EAST document to scan (待扫描的 EAST 文档)
        base_dir: Base directory for resolving relative image paths (相对路径解析基目录)
        force: Re-generate even if image file already exists (即使文件存在也重新生成)

    Returns:
        List of FigureJob instances needing generation (需要生成的 FigureJob 列表)
    """
    jobs: list[FigureJob] = []
    resolved_base = base_dir.resolve()
    for node in _walk(doc):
        if not isinstance(node, (Figure, Image)):
            continue
        ai = node.metadata.get("ai")
        if not isinstance(ai, dict):
            continue
        if not ai.get("generated"):
            continue  # ai-generated not set to True (未设置 ai-generated: true)
        prompt = str(ai.get("prompt", "")).strip()
        if not prompt:
            continue  # no prompt, nothing to generate (无 prompt，跳过)

        src = node.src if isinstance(node, (Figure, Image)) else ""
        output_path = (base_dir / src).resolve()

        # Path traversal safety: output must stay within base_dir (路径安全：输出必须在基目录内)
        try:
            output_path.relative_to(resolved_base)
        except ValueError:
            continue  # path escapes base_dir, skip (路径越界，跳过)

        if not force and output_path.exists():
            continue  # image already present, skip (图片已存在，跳过)

        jobs.append(
            FigureJob(
                src=src,
                output_path=output_path,
                prompt=prompt,
                model=ai.get("model") if isinstance(ai.get("model"), str) else None,
                params=ai.get("params") if isinstance(ai.get("params"), dict) else None,
            )
        )
    return jobs


def _load_runner(runner_path: Path) -> Any:
    """Dynamically load the nanobanana-compatible runner module.

    动态加载 nanobanana 兼容的 runner 模块。

    SECURITY WARNING / 安全警告:
        This function executes arbitrary Python code from the specified file.
        Only use runner scripts from trusted sources.
        此函数执行指定文件中的任意 Python 代码，仅使用受信任的 runner 脚本。

    Args:
        runner_path: Path to the runner Python script (runner 脚本路径)

    Returns:
        Loaded module with generate_image callable (含 generate_image 的已加载模块)

    Raises:
        ImportError: If runner cannot be loaded (runner 无法加载时)
    """
    spec = importlib.util.spec_from_file_location("genfig_runner", str(runner_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load runner: {runner_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate_figure_job(
    job: FigureJob,
    runner: Any,
    config: Path | None,
) -> bool:
    """Generate a single figure by calling the runner.

    通过调用 runner 生成单张图片。

    Args:
        job: Figure job to execute (待执行的图片作业)
        runner: Loaded runner module with generate_image (含 generate_image 的 runner 模块)
        config: Path to TOML config for runner (runner 的 TOML 配置路径，可选)

    Returns:
        True if generation succeeded and output file exists (成功生成且输出文件存在则返回 True)
    """
    job.output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build runner kwargs; pass extra params if available (构建 runner 参数)
    kwargs: dict[str, str | None] = {
        "prompt": job.prompt,
        "output": str(job.output_path),
        "config": str(config) if config else None,
        "model": job.model,
    }
    # Forward size from params if present (转发 size 参数)
    if job.params and "size" in job.params:
        kwargs["size"] = str(job.params["size"])

    try:
        returncode: int = runner.generate_image(**kwargs)
    except Exception:
        return False

    if returncode != 0:
        return False
    return job.output_path.exists()


def run_generate_figures(
    doc: Document,
    base_dir: Path,
    runner_path: Path,
    config: Path | None = None,
    force: bool = False,
    echo: Any = None,
) -> tuple[int, int]:
    """Run the generate-figures pipeline on a document.

    对文档运行完整的出图流程。

    Args:
        doc: EAST document (EAST 文档)
        base_dir: Base directory for image paths (图片路径基目录)
        runner_path: Path to nanobanana-compatible runner (runner 脚本路径)
        config: Optional TOML config for the runner (可选的 runner TOML 配置)
        force: Regenerate even if file exists (强制重新生成)
        echo: Optional callable for progress output, e.g. click.echo (进度输出函数，可选)

    Returns:
        (success_count, fail_count) tuple (成功数, 失败数 元组)
    """
    jobs = collect_jobs(doc, base_dir=base_dir, force=force)
    if not jobs:
        if echo:
            echo("[generate-figures] No AI figures to generate (无待生成的 AI 图片).")
        return (0, 0)

    runner = _load_runner(runner_path)
    success = 0
    fail = 0
    for job in jobs:
        ok = generate_figure_job(job, runner=runner, config=config)
        if ok:
            success += 1
            if echo:
                echo(f"[generate-figures] ✓ {job.src}")
        else:
            fail += 1
            if echo:
                echo(f"[generate-figures] ✗ {job.src} (failed)")

    return (success, fail)
