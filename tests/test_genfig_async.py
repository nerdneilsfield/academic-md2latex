"""Async figure generation tests (异步图片生成测试)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from wenqiao.genfig import (
    FigureJob,
    FigureRunner,
    _write_ai_done,
    run_generate_figures_async,
)


class _FakeRunner(FigureRunner):
    """Synchronous fake runner for testing (同步假 runner，用于测试)."""

    def generate(self, job: FigureJob) -> bool:
        """Generate fake image by writing placeholder bytes (写占位字节生成假图片)."""
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        job.output_path.write_bytes(b"PNG")
        return True


def _make_job(tmp_path: Path, label: str = "fig:test", exists: bool = False) -> FigureJob:
    """Create a FigureJob for testing (创建测试用 FigureJob)."""
    out = tmp_path / f"{label}.png"
    if exists:
        out.write_bytes(b"PNG")
    return FigureJob(
        src=f"{label}.png",
        output_path=out,
        prompt="a test figure",
        model=None,
        params=None,
        label=label,
        source_file=None,
    )


class TestAsyncGenerate:
    """Tests for async_generate default and run_generate_figures_async (异步生成测试)."""

    def test_async_generate_default_wraps_sync(self, tmp_path: Path) -> None:
        """Default async_generate wraps sync generate via to_thread (默认包装同步方法)."""
        runner = _FakeRunner()
        job = _make_job(tmp_path)
        result = asyncio.run(runner.async_generate(job))
        assert result is True
        assert job.output_path.exists()

    def test_run_async_generates_all_jobs(self, tmp_path: Path) -> None:
        """run_generate_figures_async generates all jobs (生成所有作业)."""
        jobs = [_make_job(tmp_path, f"fig:test{i}") for i in range(3)]
        runner = _FakeRunner()
        success, fail = asyncio.run(
            run_generate_figures_async(jobs, runner, concurrency=2)
        )
        assert success == 3
        assert fail == 0

    def test_run_async_skips_existing(self, tmp_path: Path) -> None:
        """Existing output files are skipped unless force=True (已存在文件跳过)."""
        job = _make_job(tmp_path, exists=True)
        runner = _FakeRunner()
        success, fail = asyncio.run(
            run_generate_figures_async([job], runner, force=False)
        )
        assert success == 0  # skipped, not counted as success or fail (跳过，不计入)
        assert fail == 0

    def test_run_async_force_regenerates(self, tmp_path: Path) -> None:
        """force=True re-generates even if file exists (force=True 强制重新生成)."""
        job = _make_job(tmp_path, exists=True)
        runner = _FakeRunner()
        success, fail = asyncio.run(
            run_generate_figures_async([job], runner, force=True)
        )
        assert success == 1
        assert fail == 0

    def test_run_async_respects_concurrency(self, tmp_path: Path) -> None:
        """Semaphore limits concurrency correctly (信号量正确限制并发)."""
        import asyncio as _asyncio

        peak: list[int] = []
        active: list[int] = []

        class _CountingRunner(FigureRunner):
            def generate(self, job: FigureJob) -> bool:
                """Unused sync stub (未使用的同步存根)."""
                return True

            async def async_generate(self, job: FigureJob) -> bool:
                """Count concurrent executions (计数并发执行数)."""
                active.append(1)
                peak.append(len(active))
                await _asyncio.sleep(0)
                job.output_path.parent.mkdir(parents=True, exist_ok=True)
                job.output_path.write_bytes(b"X")
                active.pop()
                return True

        jobs = [_make_job(tmp_path, f"fig:c{i}") for i in range(6)]
        asyncio.run(run_generate_figures_async(jobs, _CountingRunner(), concurrency=2))
        assert max(peak) <= 2

    def test_run_async_empty_jobs(self, tmp_path: Path) -> None:
        """Empty job list returns (0, 0) (空作业列表返回 (0, 0))."""
        runner = _FakeRunner()
        success, fail = asyncio.run(run_generate_figures_async([], runner))
        assert success == 0
        assert fail == 0


class TestWriteAiDone:
    """Tests for _write_ai_done (ai-done 写回测试)."""

    def test_inserts_marker_after_label(self, tmp_path: Path) -> None:
        """_write_ai_done inserts ai-done comment after label line (在标签行后插入标记)."""
        src = tmp_path / "doc.mid.md"
        src.write_text(
            "# Title\n\n<!-- label: fig:test -->\n![img](fig.png)\n",
            encoding="utf-8",
        )
        _write_ai_done(src, "fig:test")
        content = src.read_text(encoding="utf-8")
        assert "<!-- ai-done: true -->" in content
        lines = content.splitlines()
        label_idx = next(i for i, ln in enumerate(lines) if "label: fig:test" in ln)
        done_idx = next(i for i, ln in enumerate(lines) if "ai-done: true" in ln)
        assert done_idx == label_idx + 1

    def test_idempotent(self, tmp_path: Path) -> None:
        """_write_ai_done is idempotent — does not duplicate marker (幂等性)."""
        src = tmp_path / "doc.mid.md"
        src.write_text(
            "<!-- label: fig:test -->\n<!-- ai-done: true -->\n![img](fig.png)\n",
            encoding="utf-8",
        )
        _write_ai_done(src, "fig:test")
        content = src.read_text(encoding="utf-8")
        assert content.count("ai-done: true") == 1

    def test_writeback_triggered_on_success(self, tmp_path: Path) -> None:
        """run_generate_figures_async writes ai-done when writeback=True (writeback=True 时写回)."""
        src = tmp_path / "doc.mid.md"
        src.write_text("<!-- label: fig:wb -->\n![img](wb.png)\n", encoding="utf-8")
        job = _make_job(tmp_path, label="fig:wb")
        job.source_file = src
        runner = _FakeRunner()
        asyncio.run(run_generate_figures_async([job], runner, writeback=True))
        assert "ai-done: true" in src.read_text(encoding="utf-8")

    def test_no_writeback_skips_ai_done(self, tmp_path: Path) -> None:
        """writeback=False skips ai-done write (writeback=False 时跳过写回)."""
        src = tmp_path / "doc.mid.md"
        src.write_text("<!-- label: fig:nwb -->\n![img](nwb.png)\n", encoding="utf-8")
        job = _make_job(tmp_path, label="fig:nwb")
        job.source_file = src
        runner = _FakeRunner()
        asyncio.run(run_generate_figures_async([job], runner, writeback=False))
        assert "ai-done" not in src.read_text(encoding="utf-8")

    def test_writeback_failure_does_not_count_as_fail(self, tmp_path: Path) -> None:
        """Writeback OSError does not mark successful generation as fail (写回错误不计入失败)."""
        job = _make_job(tmp_path, label="fig:safe")
        # Set source_file to a path that does not exist (设置不存在的源文件路径)
        job.source_file = tmp_path / "nonexistent.mid.md"
        runner = _FakeRunner()
        success, fail = asyncio.run(
            run_generate_figures_async([job], runner, writeback=True)
        )
        # Generation succeeded, writeback warned — not a fail (生成成功，写回警告，不计失败)
        assert success == 1
        assert fail == 0


class TestOpenAIRunnerAsync:
    """Tests for OpenAIFigureRunner.async_generate (OpenAI 异步生成测试)."""

    def test_has_async_generate_override(self) -> None:
        """OpenAIFigureRunner defines async_generate (方法定义在类本身)."""
        from wenqiao.genfig_openai import OpenAIFigureRunner

        assert "async_generate" in OpenAIFigureRunner.__dict__

    def test_async_generate_returns_false_without_auth(self, tmp_path: Path) -> None:
        """async_generate returns False when no auth configured (无认证信息时返回 False)."""
        import os

        from wenqiao.genfig_openai import OpenAIFigureRunner

        runner = OpenAIFigureRunner()  # No api_key, no config, no env vars set
        job = FigureJob(
            src="fig.png",
            output_path=tmp_path / "fig.png",
            prompt="a dog",
            model=None,
            params=None,
            label="fig:dog",
            source_file=None,
        )
        # Patch out env vars to ensure no auth resolves (清空环境变量确保无认证)
        env_backup = {
            k: os.environ.pop(k, None)
            for k in [
                "OPENAI_API_KEY",
                "OPENAI_BASE_URL",
                "POE_API_KEY",
                "POE_BASE_URL",
                "NANO_BANANA_API_KEY",
                "NANO_BANANA_BASE_URL",
                "WENQIAO_API_KEY",
            ]
        }
        try:
            result = asyncio.run(runner.async_generate(job))
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v
        assert result is False
