"""generate subcommand tests (generate 子命令测试)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from wenqiao.cli import cli as main
from wenqiao.genfig import FigureJob

_SAMPLE_MD = """\
# Test

<!-- label: fig:test -->
<!-- ai-generated: true -->
<!-- ai-prompt: a blue circle -->
![test](fig-test.png)
"""


class TestGenerateCmd:
    """Tests for the generate CLI command (generate 命令测试)."""

    def test_no_ai_figures_exits_0(self, tmp_path: Path) -> None:
        """generate on file with no AI figures exits 0 (无 AI 图片时退出码 0)."""
        src = tmp_path / "doc.mid.md"
        src.write_text("# Hello\n\nNo figures here.\n")
        result = CliRunner().invoke(main, ["generate", str(src)])
        assert result.exit_code == 0

    def test_generate_with_mock_runner(self, tmp_path: Path) -> None:
        """generate calls runner and exits 0 on success (调用 runner 成功退出 0)."""
        src = tmp_path / "doc.mid.md"
        # Use multi-figure inline format that the parser resolves into FigureJobs
        # (使用解析器可识别的多图内联格式生成 FigureJob)
        md = ""
        for i in range(1, 3):
            md += (
                f"<!-- label: fig:f{i} -->\n"
                f"<!-- ai-generated: true -->\n"
                f"<!-- ai-prompt: fig {i} -->\n"
                f"![f{i}](fig-{i}.png)\n\n"
            )
        src.write_text(f"# Test\n\n{md}")

        def fake_generate(job: FigureJob) -> bool:
            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            job.output_path.write_bytes(b"PNG")
            return True

        with patch("wenqiao.generate_cmd.OpenAIFigureRunner") as MockRunner:
            instance = MockRunner.return_value
            instance.generate.side_effect = fake_generate
            instance.async_generate = AsyncMock(side_effect=fake_generate)

            result = CliRunner().invoke(
                main,
                [
                    "generate", str(src),
                    "--api-key", "sk-test",
                    "--base-url", "http://localhost",
                    "--no-writeback",
                ],
            )

        assert result.exit_code == 0
        instance.async_generate.assert_called()

    def test_start_end_id_slices_jobs(self, tmp_path: Path) -> None:
        """--start-id / --end-id slices jobs by 1-based index (范围切片)."""
        md = ""
        for i in range(1, 4):
            md += (
                f"<!-- label: fig:f{i} -->\n"
                f"<!-- ai-generated: true -->\n"
                f"<!-- ai-prompt: fig {i} -->\n"
                f"![f{i}](fig-{i}.png)\n\n"
            )
        src = tmp_path / "doc.mid.md"
        src.write_text(f"# T\n\n{md}")

        generated: list[str] = []

        def fake_generate(job: FigureJob) -> bool:
            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            job.output_path.write_bytes(b"PNG")
            generated.append(str(job.src))
            return True

        with patch("wenqiao.generate_cmd.OpenAIFigureRunner") as MockRunner:
            instance = MockRunner.return_value
            instance.generate.side_effect = fake_generate
            instance.async_generate = AsyncMock(side_effect=fake_generate)

            CliRunner().invoke(
                main,
                [
                    "generate", str(src),
                    "--start-id", "2", "--end-id", "2",
                    "--api-key", "sk-test", "--base-url", "http://localhost",
                    "--no-writeback",
                ],
            )

        assert len(generated) == 1
        assert "fig-2.png" in generated[0]

    def test_no_writeback_flag(self, tmp_path: Path) -> None:
        """--no-writeback skips ai-done insertion (--no-writeback 跳过写回)."""
        src = tmp_path / "doc.mid.md"
        src.write_text(_SAMPLE_MD)

        def fake_generate(job: FigureJob) -> bool:
            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            job.output_path.write_bytes(b"PNG")
            return True

        with patch("wenqiao.generate_cmd.OpenAIFigureRunner") as MockRunner:
            instance = MockRunner.return_value
            instance.generate.side_effect = fake_generate
            instance.async_generate = AsyncMock(side_effect=fake_generate)

            result = CliRunner().invoke(
                main,
                [
                    "generate", str(src),
                    "--no-writeback",
                    "--api-key", "sk-test",
                    "--base-url", "http://localhost",
                ],
            )

        assert result.exit_code == 0
        assert "ai-done" not in src.read_text(encoding="utf-8")

    def test_help_shows_options(self) -> None:
        """generate --help shows all key options (--help 显示所有关键选项)."""
        result = CliRunner().invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        opts = [
            "--figures-config", "--concurrency", "--start-id",
            "--end-id", "--force", "--no-writeback",
        ]
        for opt in opts:
            assert opt in result.output, f"Missing option: {opt}"
