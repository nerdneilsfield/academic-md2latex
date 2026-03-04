"""Tests for optional generate-figures feature (可选出图功能测试)."""

from __future__ import annotations

from pathlib import Path

import pytest

from wenqiao.genfig import FigureJob, FigureRunner, collect_jobs, generate_figure_job
from wenqiao.nodes import Document, Figure, Image, Paragraph

# ── MockRunner (测试用 FigureRunner 子类) ─────────────────────────────────────


class MockRunner(FigureRunner):
    """Test FigureRunner that records calls (记录调用的测试 runner)."""

    def __init__(self, success: bool = True, write_file: bool = True) -> None:
        self.success = success
        self.write_file = write_file
        self.calls: list[FigureJob] = []

    def generate(self, job: FigureJob) -> bool:
        """Record call and optionally write fake output (记录调用并可选写入假输出)."""
        self.calls.append(job)
        if self.write_file:
            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            job.output_path.write_bytes(b"fake image")
        return self.success


class RaisingRunner(FigureRunner):
    """Runner that raises on generate (生成时抛异常的 runner)."""

    def generate(self, job: FigureJob) -> bool:
        """Always raise RuntimeError (总是抛出 RuntimeError)."""
        raise RuntimeError("network error")


# ── helpers (辅助函数) ────────────────────────────────────────────────────────


def _fig(src: str, ai: dict | None = None) -> Figure:
    """Build a Figure node for testing (构建测试用 Figure 节点)."""
    meta: dict = {}
    if ai is not None:
        meta["ai"] = ai
    return Figure(src=src, alt="alt", metadata=meta)


def _img_with_ai(src: str, ai: dict) -> Image:
    """Build an Image with AI metadata (构建含 AI 元数据的 Image 节点)."""
    return Image(src=src, alt="alt", metadata={"ai": ai})


# ── FigureRunner ABC ──────────────────────────────────────────────────────────


class TestFigureRunnerABC:
    """FigureRunner ABC enforcement (FigureRunner ABC 强制测试)."""

    def test_runner_abc_enforced(self) -> None:
        """Cannot instantiate FigureRunner directly (不能直接实例化 FigureRunner)."""
        with pytest.raises(TypeError):
            FigureRunner()  # type: ignore[abstract]

    def test_mock_runner_is_figure_runner(self) -> None:
        """MockRunner is a FigureRunner subclass (MockRunner 是 FigureRunner 子类)."""
        runner = MockRunner()
        assert isinstance(runner, FigureRunner)


# ── collect_jobs ──────────────────────────────────────────────────────────────


class TestCollectJobs:
    """collect_jobs finds figures with ai-generated: true (收集 AI 图作业测试)."""

    def test_figure_with_ai_generated_collected(self) -> None:
        """Figure with ai.generated=True is collected (含 ai.generated=True 的图被收集)."""
        fig = _fig("fig.png", {"generated": True, "prompt": "blue sky"})
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=Path("/tmp"))
        assert len(jobs) == 1
        assert jobs[0].src == "fig.png"
        assert jobs[0].prompt == "blue sky"

    def test_figure_without_ai_skipped(self) -> None:
        """Figure without AI metadata is skipped (无 AI 元数据的图跳过)."""
        fig = _fig("fig.png")
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=Path("/tmp"))
        assert len(jobs) == 0

    def test_figure_ai_generated_false_skipped(self) -> None:
        """Figure with ai.generated=False is skipped (ai.generated=False 的图跳过)."""
        fig = _fig("fig.png", {"generated": False, "prompt": "blue sky"})
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=Path("/tmp"))
        assert len(jobs) == 0

    def test_existing_image_skipped_by_default(self, tmp_path: Path) -> None:
        """Existing image file is skipped unless force=True (已存在图片默认跳过)."""
        img_file = tmp_path / "fig.png"
        img_file.write_bytes(b"fake image")
        fig = _fig("fig.png", {"generated": True, "prompt": "blue sky"})
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=tmp_path, force=False)
        assert len(jobs) == 0

    def test_existing_image_regenerated_with_force(self, tmp_path: Path) -> None:
        """Existing image regenerated when force=True (force=True 时重新生成)."""
        img_file = tmp_path / "fig.png"
        img_file.write_bytes(b"fake image")
        fig = _fig("fig.png", {"generated": True, "prompt": "blue sky"})
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=tmp_path, force=True)
        assert len(jobs) == 1

    def test_image_node_with_ai_collected(self) -> None:
        """Image node with AI metadata is also collected (Image 节点也被收集)."""
        img = _img_with_ai("img.png", {"generated": True, "prompt": "sky"})
        d = Document(children=[Paragraph(children=[img])])
        jobs = collect_jobs(d, base_dir=Path("/tmp"))
        assert len(jobs) == 1

    def test_job_has_model_and_params(self) -> None:
        """Collected job carries model and params (作业携带 model 和 params)."""
        fig = _fig(
            "fig.png",
            {
                "generated": True,
                "prompt": "technical diagram",
                "model": "midjourney-v6",
                "params": {"seed": 42},
            },
        )
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=Path("/tmp"))
        assert jobs[0].model == "midjourney-v6"
        assert jobs[0].params == {"seed": 42}

    def test_empty_src_skipped(self) -> None:
        """Figure with empty src is skipped (空 src 的 Figure 被跳过)."""
        fig = _fig("", {"generated": True, "prompt": "sky"})
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=Path("/tmp"))
        assert len(jobs) == 0

    def test_path_traversal_skipped(self, tmp_path: Path) -> None:
        """src with ../ that escapes base_dir is skipped (路径穿越被跳过)."""
        fig = _fig("../../etc/passwd", {"generated": True, "prompt": "sky"})
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=tmp_path)
        assert len(jobs) == 0

    def test_absolute_path_skipped(self, tmp_path: Path) -> None:
        """Absolute src path outside base_dir is skipped (绝对路径越界被跳过)."""
        fig = _fig("/tmp/evil.png", {"generated": True, "prompt": "sky"})
        d = Document(children=[fig])
        jobs = collect_jobs(d, base_dir=tmp_path)
        assert len(jobs) == 0


# ── generate_figure_job ──────────────────────────────────────────────────────


class TestGenerateFigureJob:
    """generate_figure_job calls runner with correct args (调用 runner 测试)."""

    def test_runner_called_with_prompt(self, tmp_path: Path) -> None:
        """Runner is called with job prompt (runner 以 prompt 调用)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="blue sky",
            model=None,
            params=None,
        )
        runner = MockRunner()
        ok = generate_figure_job(job, runner=runner)
        assert ok is True
        assert len(runner.calls) == 1
        assert runner.calls[0].prompt == "blue sky"

    def test_runner_failure_returns_false(self, tmp_path: Path) -> None:
        """Runner returning False means failure (runner 返回 False 表示失败)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="sky",
            model=None,
            params=None,
        )
        runner = MockRunner(success=False, write_file=False)
        ok = generate_figure_job(job, runner=runner)
        assert ok is False

    def test_missing_output_returns_false(self, tmp_path: Path) -> None:
        """Runner returning True but no output file means failure (无输出文件视为失败)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="sky",
            model=None,
            params=None,
        )
        # Runner returns True but doesn't write file (返回 True 但不写文件)
        runner = MockRunner(success=True, write_file=False)
        ok = generate_figure_job(job, runner=runner)
        # Post-condition: no file on disk means failure despite runner returning True
        # (后置条件：文件不存在则视为失败)
        assert ok is False

    def test_runner_exception_returns_false(self, tmp_path: Path) -> None:
        """Runner that raises exception returns False (runner 抛异常返回 False)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="sky",
            model=None,
            params=None,
        )
        runner = RaisingRunner()
        ok = generate_figure_job(job, runner=runner)
        assert ok is False

    def test_directory_not_counted_as_success(self, tmp_path: Path) -> None:
        """Runner returning False for directory path (目录路径返回 False)."""
        sub = tmp_path / "out_dir"
        sub.mkdir()
        job = FigureJob(
            src="out_dir",
            output_path=sub,
            prompt="sky",
            model=None,
            params=None,
        )
        runner = MockRunner(success=False, write_file=False)
        ok = generate_figure_job(job, runner=runner)
        assert ok is False

    def test_job_passed_to_runner(self, tmp_path: Path) -> None:
        """Full job object is passed to runner.generate (完整作业传递给 runner)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="sky",
            model="dalle-3",
            params={"size": "1024x1024"},
        )
        runner = MockRunner()
        generate_figure_job(job, runner=runner)
        assert runner.calls[0] is job
        assert runner.calls[0].model == "dalle-3"
        assert runner.calls[0].params == {"size": "1024x1024"}
