"""Tests for optional generate-figures feature (可选出图功能测试)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from md_mid.genfig import FigureJob, collect_jobs, generate_figure_job
from md_mid.nodes import Document, Figure, Image, Paragraph


def _fig(src: str, ai: dict | None = None) -> Figure:
    """Build a Figure node for testing (构建测试用 Figure 节点)."""
    meta: dict = {}
    if ai is not None:
        meta["ai"] = ai
    return Figure(src=src, alt="alt", metadata=meta)


def _img_with_ai(src: str, ai: dict) -> Image:
    """Build an Image with AI metadata (构建含 AI 元数据的 Image 节点)."""
    return Image(src=src, alt="alt", metadata={"ai": ai})


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
        mock_runner = MagicMock()
        mock_runner.generate_image.return_value = 0
        # Simulate successful output (模拟成功输出)
        (tmp_path / "out.png").write_bytes(b"img")

        ok = generate_figure_job(job, runner=mock_runner, config=None)
        assert ok is True
        mock_runner.generate_image.assert_called_once()
        call_kwargs = mock_runner.generate_image.call_args.kwargs
        assert call_kwargs["prompt"] == "blue sky"

    def test_runner_failure_returns_false(self, tmp_path: Path) -> None:
        """Runner returning non-zero means failure (runner 返回非零表示失败)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="sky",
            model=None,
            params=None,
        )
        mock_runner = MagicMock()
        mock_runner.generate_image.return_value = 1  # failure (失败返回码)

        ok = generate_figure_job(job, runner=mock_runner, config=None)
        assert ok is False

    def test_missing_output_returns_false(self, tmp_path: Path) -> None:
        """Runner returning 0 but no output file means failure (无输出文件视为失败)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="sky",
            model=None,
            params=None,
        )
        mock_runner = MagicMock()
        mock_runner.generate_image.return_value = 0  # claims success (声称成功)
        # But output file is NOT created (但未创建输出文件)

        ok = generate_figure_job(job, runner=mock_runner, config=None)
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
        mock_runner = MagicMock()
        mock_runner.generate_image.side_effect = RuntimeError("network error")

        ok = generate_figure_job(job, runner=mock_runner, config=None)
        assert ok is False

    def test_size_forwarded_from_params(self, tmp_path: Path) -> None:
        """Size param is forwarded to runner (size 参数转发给 runner)."""
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="sky",
            model="dalle-3",
            params={"size": "1024x1024"},
        )
        mock_runner = MagicMock()
        mock_runner.generate_image.return_value = 0
        (tmp_path / "out.png").write_bytes(b"img")

        generate_figure_job(job, runner=mock_runner, config=None)
        call_kwargs = mock_runner.generate_image.call_args.kwargs
        assert call_kwargs["size"] == "1024x1024"
        assert call_kwargs["model"] == "dalle-3"
