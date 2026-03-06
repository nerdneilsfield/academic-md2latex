"""Optional AI figure generation helper.

可选 AI 图片生成辅助模块。
Walks the EAST for Figure/Image nodes with ai-generated: true and calls
a FigureRunner implementation to generate them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wenqiao.nodes import Document, Figure, Image, Node


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
    label: str = ""  # Figure label for writeback matching (用于 writeback 匹配的标签)
    source_file: Path | None = None  # Source .mid.md path for ai-done writeback (源文件路径，可选)


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
        if not src:
            continue  # empty src, skip (空 src，跳过)
        output_path = (base_dir / src).resolve()

        # Path traversal safety: output must stay within base_dir (路径安全：输出必须在基目录内)
        try:
            output_path.relative_to(resolved_base)
        except ValueError:
            continue  # path escapes base_dir, skip (路径越界，跳过)

        if not force and output_path.is_file():
            continue  # image already present, skip (图片已存在，跳过)

        jobs.append(
            FigureJob(
                src=src,
                output_path=output_path,
                prompt=prompt,
                model=ai.get("model") if isinstance(ai.get("model"), str) else None,
                params=ai.get("params") if isinstance(ai.get("params"), dict) else None,
                label=str(node.metadata.get("label", src)),  # Label for writeback matching (writeback 匹配标签)
                source_file=None,  # Caller sets this if writeback is needed (调用方按需设置)
            )
        )
    return jobs


class FigureRunner(ABC):
    """Base class for figure generation runners (图片生成 runner 基类).

    Subclass and implement generate() to provide custom image generation.
    (子类化并实现 generate() 以提供自定义图片生成。)
    """

    @abstractmethod
    def generate(self, job: FigureJob) -> bool:
        """Generate a single figure (生成单张图片).

        Args:
            job: Figure generation job (图片生成作业)

        Returns:
            True if generation succeeded and output file exists (成功返回 True)
        """
        ...


def generate_figure_job(
    job: FigureJob,
    runner: FigureRunner,
) -> bool:
    """Generate a single figure by calling the runner.

    通过调用 runner 生成单张图片。

    Args:
        job: Figure job to execute (待执行的图片作业)
        runner: FigureRunner implementation (FigureRunner 实现)

    Returns:
        True if generation succeeded and output file exists (成功生成且输出文件存在则返回 True)
    """
    job.output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        ok = runner.generate(job)
    except Exception:
        return False
    # Post-condition: file must exist on disk (后置条件：文件必须存在)
    return ok and job.output_path.is_file()


def run_generate_figures(
    doc: Document,
    base_dir: Path,
    runner: FigureRunner,
    force: bool = False,
    echo: Callable[[str], object] | None = None,
) -> tuple[int, int]:
    """Run the generate-figures pipeline on a document.

    对文档运行完整的出图流程。

    Args:
        doc: EAST document (EAST 文档)
        base_dir: Base directory for image paths (图片路径基目录)
        runner: FigureRunner implementation (FigureRunner 实现)
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

    success = 0
    fail = 0
    for job in jobs:
        ok = generate_figure_job(job, runner=runner)
        if ok:
            success += 1
            if echo:
                echo(f"[generate-figures] ✓ {job.src}")
        else:
            fail += 1
            if echo:
                echo(f"[generate-figures] ✗ {job.src} (failed)")

    return (success, fail)
