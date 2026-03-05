# Generate Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `wenqiao generate` subcommand that generates AI figures concurrently with range selection and ai-done writeback; `convert --generate-figures` calls the same async backend.

**Architecture:** Extend `FigureJob` with `label`/`source_file` fields; add `async_generate()` to the `FigureRunner` ABC (default wraps sync via `asyncio.to_thread`, `OpenAIFigureRunner` overrides with true async); add `run_generate_figures_async()` to `genfig.py`; create `generate_cmd.py`; update `cli.py`.

**Tech Stack:** Python asyncio, openai SDK (AsyncOpenAI), Click, tomllib (stdlib Python ≥ 3.11)

---

## Context: Key Files

Before starting, skim these to understand the existing code (do NOT copy paste into your context — just read to orient):

- `src/wenqiao/genfig.py` — `FigureJob` dataclass, `collect_jobs()`, `FigureRunner` ABC, `run_generate_figures()` (sequential)
- `src/wenqiao/genfig_openai.py` — `OpenAIFigureRunner.generate()` uses `openai.OpenAI` (sync) + `client.chat.completions.create`
- `src/wenqiao/cli.py` — `convert_cmd` already has `--generate-figures`, `--figures-config`, `--force-regenerate`; calls `run_generate_figures()` (sync)
- `tests/test_genfig.py` — existing tests for sync path (do NOT break these)

Run tests first to establish baseline:
```bash
uv run pytest tests/test_genfig.py -v --tb=short
```

---

### Task 1: Extend FigureJob with label and source_file

**Files:**
- Modify: `src/wenqiao/genfig.py:19-36` (FigureJob dataclass and collect_jobs)

**Background:** `_write_ai_done()` (Task 2) needs the figure's label to locate the right comment block in the source `.mid.md`. `collect_jobs()` must populate `label` from `node.metadata.get("label", node.src)`. `source_file` is `None` here — the generate command sets it after collection.

**Step 1: Write the failing test**

Add to `tests/test_genfig.py`:

```python
def test_figure_job_has_label_field() -> None:
    """FigureJob exposes label and source_file fields (FigureJob 含 label/source_file 字段)."""
    job = FigureJob(
        src="fig1.png",
        output_path=Path("/tmp/fig1.png"),
        prompt="a cat",
        model=None,
        params=None,
        label="fig:cat",
        source_file=None,
    )
    assert job.label == "fig:cat"
    assert job.source_file is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_genfig.py::test_figure_job_has_label_field -v
```
Expected: FAIL — `TypeError: FigureJob.__init__() got unexpected keyword argument 'label'`

**Step 3: Add fields to FigureJob**

In `src/wenqiao/genfig.py`, update the `FigureJob` dataclass (add fields after `params`):

```python
@dataclass
class FigureJob:
    """One figure to generate (待生成的一个图片作业).

    Attributes:
        src: Relative image path from document (相对图片路径)
        output_path: Resolved absolute path to write the image (绝对输出路径)
        prompt: Generation prompt (生成 prompt)
        model: Model name override (模型名覆盖，可选)
        params: Extra generation parameters (额外生成参数，可选)
        label: Figure label for writeback matching (用于 writeback 匹配的标签，可选)
        source_file: Source .mid.md path for ai-done writeback (源文件路径，可选)
    """

    src: str
    output_path: Path
    prompt: str
    model: str | None
    params: dict[str, Any] | None
    label: str = ""
    source_file: Path | None = None
```

Also update `collect_jobs()` to populate `label`. In the `jobs.append(FigureJob(...))` call, add:

```python
        jobs.append(
            FigureJob(
                src=src,
                output_path=output_path,
                prompt=prompt,
                model=ai.get("model") if isinstance(ai.get("model"), str) else None,
                params=ai.get("params") if isinstance(ai.get("params"), dict) else None,
                label=str(node.metadata.get("label", src)),
                source_file=None,  # Caller sets this if writeback is needed (调用方按需设置)
            )
        )
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_genfig.py -v --tb=short
```
Expected: All pass.

**Step 5: Commit**

```bash
git add src/wenqiao/genfig.py tests/test_genfig.py
git commit -m "feat: add label and source_file fields to FigureJob"
```

---

### Task 2: Add async infrastructure to genfig.py

**Files:**
- Modify: `src/wenqiao/genfig.py` (add imports, `async_generate`, `run_generate_figures_async`, `_write_ai_done`)

**Background:**
- `FigureRunner.async_generate()` is a default async method; subclasses override for true async.
- `run_generate_figures_async()` collects jobs, slices by `start_id`/`end_id`, runs under a `Semaphore`, gathers results.
- `_write_ai_done()` does a line scan for `<!-- label: LABEL -->` and inserts `<!-- ai-done: true -->` immediately after, only if not already present.

**Step 1: Write failing tests**

Create `tests/test_genfig_async.py`:

```python
"""Async figure generation tests (异步图片生成测试)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wenqiao.genfig import (
    FigureJob,
    FigureRunner,
    _write_ai_done,
    run_generate_figures_async,
)


class _FakeRunner(FigureRunner):
    """Synchronous fake runner for testing (同步假 runner，用于测试)."""

    def generate(self, job: FigureJob) -> bool:
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        job.output_path.write_bytes(b"PNG")
        return True


def _make_job(tmp_path: Path, label: str = "fig:test", exists: bool = False) -> FigureJob:
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


def test_async_generate_default_wraps_sync(tmp_path: Path) -> None:
    """Default async_generate wraps sync generate via to_thread (默认包装同步方法)."""
    runner = _FakeRunner()
    job = _make_job(tmp_path)
    result = asyncio.run(runner.async_generate(job))
    assert result is True
    assert job.output_path.exists()


def test_run_async_generates_all_jobs(tmp_path: Path) -> None:
    """run_generate_figures_async generates all jobs (生成所有作业)."""
    jobs = [_make_job(tmp_path, f"fig:test{i}") for i in range(3)]
    runner = _FakeRunner()
    success, fail = asyncio.run(
        run_generate_figures_async(jobs, runner, concurrency=2)
    )
    assert success == 3
    assert fail == 0


def test_run_async_skips_existing(tmp_path: Path) -> None:
    """Existing output files are skipped unless force=True (已存在文件跳过)."""
    job = _make_job(tmp_path, exists=True)
    runner = _FakeRunner()
    success, fail = asyncio.run(
        run_generate_figures_async([job], runner, force=False)
    )
    assert success == 0  # skipped, not counted as success or fail (跳过，不计入)
    assert fail == 0


def test_run_async_force_regenerates(tmp_path: Path) -> None:
    """force=True re-generates even if file exists (force=True 强制重新生成)."""
    job = _make_job(tmp_path, exists=True)
    runner = _FakeRunner()
    success, fail = asyncio.run(
        run_generate_figures_async([job], runner, force=True)
    )
    assert success == 1
    assert fail == 0


def test_run_async_respects_concurrency(tmp_path: Path) -> None:
    """Semaphore limits concurrency correctly (信号量正确限制并发)."""
    import asyncio as _asyncio

    active: list[int] = []
    peak: list[int] = []

    class _CountingRunner(FigureRunner):
        def generate(self, job: FigureJob) -> bool:
            return True

        async def async_generate(self, job: FigureJob) -> bool:
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


def test_write_ai_done_inserts_marker(tmp_path: Path) -> None:
    """_write_ai_done inserts ai-done comment after label line (_write_ai_done 在标签行后插入标记)."""
    src = tmp_path / "doc.mid.md"
    src.write_text(
        "# Title\n\n<!-- label: fig:test -->\n![img](fig.png)\n",
        encoding="utf-8",
    )
    _write_ai_done(src, "fig:test")
    content = src.read_text(encoding="utf-8")
    assert "<!-- ai-done: true -->" in content
    # Marker appears after label line (标记出现在标签行后)
    lines = content.splitlines()
    label_idx = next(i for i, l in enumerate(lines) if "label: fig:test" in l)
    done_idx = next(i for i, l in enumerate(lines) if "ai-done: true" in l)
    assert done_idx == label_idx + 1


def test_write_ai_done_idempotent(tmp_path: Path) -> None:
    """_write_ai_done is idempotent — does not duplicate marker (幂等性)."""
    src = tmp_path / "doc.mid.md"
    src.write_text(
        "<!-- label: fig:test -->\n<!-- ai-done: true -->\n![img](fig.png)\n",
        encoding="utf-8",
    )
    _write_ai_done(src, "fig:test")
    content = src.read_text(encoding="utf-8")
    assert content.count("ai-done: true") == 1


def test_run_async_writeback(tmp_path: Path) -> None:
    """run_generate_figures_async writes ai-done when writeback=True (writeback=True 时写回)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("<!-- label: fig:wb -->\n![img](wb.png)\n", encoding="utf-8")
    job = _make_job(tmp_path, label="fig:wb")
    job.source_file = src
    runner = _FakeRunner()
    asyncio.run(run_generate_figures_async([job], runner, writeback=True))
    assert "ai-done: true" in src.read_text(encoding="utf-8")


def test_run_async_no_writeback(tmp_path: Path) -> None:
    """writeback=False skips ai-done write (writeback=False 时跳过写回)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("<!-- label: fig:nwb -->\n![img](nwb.png)\n", encoding="utf-8")
    job = _make_job(tmp_path, label="fig:nwb")
    job.source_file = src
    runner = _FakeRunner()
    asyncio.run(run_generate_figures_async([job], runner, writeback=False))
    assert "ai-done" not in src.read_text(encoding="utf-8")
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_genfig_async.py -v --tb=short
```
Expected: ImportError — `cannot import name '_write_ai_done'` and `run_generate_figures_async`

**Step 3: Implement in genfig.py**

Add to the imports at the top of `src/wenqiao/genfig.py`:

```python
import asyncio
```

Add `async_generate()` default to `FigureRunner` ABC (after the `generate` abstractmethod):

```python
    async def async_generate(self, job: FigureJob) -> bool:
        """Async generate — default wraps sync generate() in a thread.

        默认实现：在线程中调用同步 generate()，子类可覆盖以使用真正的异步客户端。

        Args:
            job: Figure generation job (图片生成作业)

        Returns:
            True if generation succeeded (成功返回 True)
        """
        return await asyncio.to_thread(self.generate, job)
```

Add `_write_ai_done()` as a module-level function (after `run_generate_figures`):

```python
def _write_ai_done(source_path: Path, label: str) -> None:
    """Insert ai-done marker after the label comment line in source file.

    在源文件的标签注释行后插入 ai-done 标记。幂等：已存在则不重复插入。

    Args:
        source_path: Path to .mid.md source file (源文件路径)
        label: Figure label to locate in file (用于定位的图片标签)
    """
    marker = "<!-- ai-done: true -->"
    lines = source_path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        # Locate the label comment (定位标签注释行)
        if f"label: {label}" in line and "<!--" in line:
            # Check next line is not already the marker (检查下一行是否已有标记)
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if marker not in next_line:
                out.append(marker + "\n")
        i += 1
    source_path.write_text("".join(out), encoding="utf-8")
```

Add `run_generate_figures_async()` (after `run_generate_figures`):

```python
async def run_generate_figures_async(
    jobs: list[FigureJob],
    runner: FigureRunner,
    concurrency: int = 4,
    force: bool = False,
    writeback: bool = True,
    echo: Callable[[str], object] | None = None,
) -> tuple[int, int]:
    """Run figure generation concurrently with a semaphore.

    使用信号量并发运行图片生成流程。

    Args:
        jobs: List of figure jobs (图片作业列表)
        runner: FigureRunner implementation (FigureRunner 实现)
        concurrency: Max concurrent generations (最大并发数)
        force: Re-generate even if file exists (强制重新生成)
        writeback: Write ai-done marker to source file on success (成功后写回 ai-done 标记)
        echo: Optional progress callback, e.g. click.echo (进度输出函数，可选)

    Returns:
        (success_count, fail_count) tuple (成功数, 失败数 元组)
    """
    if not jobs:
        if echo:
            echo("[generate-figures] No AI figures to generate (无待生成的 AI 图片).")
        return (0, 0)

    sem = asyncio.Semaphore(concurrency)
    success_count = 0
    fail_count = 0

    async def _run(job: FigureJob) -> bool:
        # Skip if output exists and not forcing (已存在且不强制时跳过)
        if not force and job.output_path.is_file():
            if echo:
                echo(f"[generate-figures] skip {job.src} (exists)")
            return True  # Skipped = not a failure (跳过不算失败)

        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        async with sem:
            try:
                ok = await runner.async_generate(job)
            except Exception as exc:
                if echo:
                    echo(f"[generate-figures] ✗ {job.src} ({exc})")
                return False

        # Post-condition: output file must exist (后置条件：输出文件必须存在)
        if not (ok and job.output_path.is_file()):
            if echo:
                echo(f"[generate-figures] ✗ {job.src} (no output)")
            return False

        if echo:
            echo(f"[generate-figures] ✓ {job.src}")

        # Writeback ai-done to source file (写回 ai-done 到源文件)
        if writeback and job.source_file is not None and job.label:
            _write_ai_done(job.source_file, job.label)

        return True

    results = await asyncio.gather(*[_run(j) for j in jobs], return_exceptions=True)
    for r in results:
        if r is True:
            success_count += 1
        else:
            fail_count += 1
    return (success_count, fail_count)
```

Wait — look at `test_run_async_skips_existing`: it expects `success=0, fail=0` for a skipped file. But the `_run` function above returns `True` for skipped files, so they'd count as success. Fix: return a sentinel `None` for skipped files and count differently.

Actually re-read the test: `success == 0, fail == 0` — skips are neither. So we need a 3-way return. Simplest fix: use `None` for skipped:

```python
    async def _run(job: FigureJob) -> bool | None:
        if not force and job.output_path.is_file():
            if echo:
                echo(f"[generate-figures] skip {job.src} (exists)")
            return None  # Skipped — not success, not fail (跳过)
        ...
        return True  # or False

    results = await asyncio.gather(*[_run(j) for j in jobs], return_exceptions=True)
    for r in results:
        if r is True:
            success_count += 1
        elif r is False or isinstance(r, Exception):
            fail_count += 1
        # None = skipped, not counted (None 表示跳过，不计入)
    return (success_count, fail_count)
```

Use this version in the implementation above (replace the `return True` in the skip block with `return None`, and update the results loop).

**Step 4: Run tests**

```bash
uv run pytest tests/test_genfig_async.py tests/test_genfig.py -v --tb=short
```
Expected: All pass.

**Step 5: Commit**

```bash
git add src/wenqiao/genfig.py tests/test_genfig_async.py
git commit -m "feat: add async_generate, run_generate_figures_async, _write_ai_done to genfig"
```

---

### Task 3: Add async_generate override to OpenAIFigureRunner

**Files:**
- Modify: `src/wenqiao/genfig_openai.py`

**Background:** `OpenAIFigureRunner.generate()` uses `openai.OpenAI` (sync) and `client.chat.completions.create`. The async override does the same with `openai.AsyncOpenAI` and `await client.chat.completions.create(...)`. Auth resolution (`_resolve_auth`, `_resolve_model`) is sync and reused as-is.

**Step 1: Write failing test**

Add to `tests/test_genfig_async.py`:

```python
def test_openai_runner_has_async_generate() -> None:
    """OpenAIFigureRunner has async_generate override (有 async_generate 覆盖)."""
    from wenqiao.genfig_openai import OpenAIFigureRunner

    runner = OpenAIFigureRunner(api_key="sk-test", base_url="http://localhost")
    # Verify it has an override (not the ABC default) by checking it's defined on the class
    # (验证该方法定义在类本身，而非继承自 ABC 默认)
    assert "async_generate" in OpenAIFigureRunner.__dict__


def test_openai_runner_async_generate_calls_async_client(tmp_path: Path) -> None:
    """async_generate uses AsyncOpenAI client (使用 AsyncOpenAI 客户端)."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    from wenqiao.genfig_openai import OpenAIFigureRunner

    job = FigureJob(
        src="fig.png",
        output_path=tmp_path / "fig.png",
        prompt="a dog",
        model=None,
        params=None,
        label="fig:dog",
        source_file=None,
    )

    # Mock openai.AsyncOpenAI and its chat.completions.create
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "https://example.com/img.png"
    mock_response.choices[0].delta = None
    mock_response.choices[0].message.images = None

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with (
        patch("wenqiao.genfig_openai.openai") as mock_openai,
        patch("wenqiao.genfig_openai._extract_image_url", return_value=None),
    ):
        mock_openai.AsyncOpenAI.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_openai.AsyncOpenAI.return_value.__aexit__ = AsyncMock(return_value=False)
        runner = OpenAIFigureRunner(api_key="sk-test", base_url="http://localhost")
        # Just verify it doesn't crash and calls AsyncOpenAI (验证不崩溃且调用了 AsyncOpenAI)
        # Since _extract_image_url returns None, generate returns False — that's ok for this test
        result = asyncio.run(runner.async_generate(job))
        assert isinstance(result, bool)
```

Note: This test is more of a smoke test. If mocking AsyncOpenAI context manager is complex, simplify to just checking `"async_generate" in OpenAIFigureRunner.__dict__` and do an integration test that mocks at a higher level.

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_genfig_async.py::test_openai_runner_has_async_generate -v
```
Expected: FAIL — `AssertionError` (method not in `__dict__` yet)

**Step 3: Add async_generate to OpenAIFigureRunner**

In `src/wenqiao/genfig_openai.py`, add after the `generate()` method:

```python
    async def async_generate(self, job: FigureJob) -> bool:
        """Generate image asynchronously via AsyncOpenAI client.

        使用 AsyncOpenAI 客户端异步生成图片。

        Args:
            job: Figure generation job (图片生成作业)

        Returns:
            True if generation succeeded and output file exists (成功返回 True)
        """
        api_key, base_url = self._resolve_auth()
        if not api_key or not base_url:
            import sys
            sys.stderr.write(
                "Missing API key or base URL. (缺少 API key 或 base URL)\n"
            )
            return False

        model = self._resolve_model()

        try:
            import openai
        except ImportError as exc:
            import sys
            sys.stderr.write(f"Missing dependency: openai ({exc}).\n")
            return False

        extra_params: dict[str, Any] = dict(job.params) if job.params else {}

        try:
            client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            chat = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": job.prompt}],
                **extra_params,
            )
            image_url = _extract_image_url(chat)
            if not image_url:
                import sys
                sys.stderr.write("No image URL or data found in model output.\n")
                _dump_response(chat)
                return False
        except Exception as exc:
            import sys
            sys.stderr.write(f"Async API call failed: {exc}\n")
            return False

        try:
            _save_image(image_url, job.output_path)
        except Exception as exc:
            import sys
            sys.stderr.write(f"Failed to save image: {exc}\n")
            return False

        return job.output_path.is_file()
```

Note: `Any` is already imported. The `sys` import at top of file is already there — remove the inline imports and use the module-level one.

**Step 4: Run tests**

```bash
uv run pytest tests/test_genfig_async.py -v --tb=short
```
Expected: All pass.

**Step 5: Commit**

```bash
git add src/wenqiao/genfig_openai.py tests/test_genfig_async.py
git commit -m "feat: add async_generate to OpenAIFigureRunner"
```

---

### Task 4: Create generate_cmd.py

**Files:**
- Create: `src/wenqiao/generate_cmd.py`
- Create: `tests/test_generate_cmd.py`

**Background:**

The command:
1. Reads the `.mid.md` file
2. Parses it with `parse_and_process()`
3. Calls `collect_jobs(doc, base_dir, force=True)` (always collect all, skip logic is in async runner)
4. Slices jobs by `--start-id`/`--end-id` (1-based, inclusive)
5. Sets `job.source_file = input_path` for each job if `writeback=True`
6. Builds runner from config/CLI flags
7. Calls `asyncio.run(run_generate_figures_async(...))`

**Step 1: Write failing tests**

Create `tests/test_generate_cmd.py`:

```python
"""generate subcommand tests (generate 子命令测试)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from wenqiao.cli import cli as main


_SAMPLE_MD = """\
# Test

<!-- label: fig:test -->
<!-- ai-generated: true -->
<!-- ai-prompt: a blue circle -->
![test](fig-test.png)
"""


def test_generate_no_figures(tmp_path: Path) -> None:
    """generate on file with no AI figures exits 0 (无 AI 图片时退出码 0)."""
    src = tmp_path / "doc.mid.md"
    src.write_text("# Hello\n\nNo figures here.\n")
    result = CliRunner().invoke(main, ["generate", str(src)])
    assert result.exit_code == 0


def test_generate_with_mock_runner(tmp_path: Path) -> None:
    """generate calls runner and writes output (调用 runner 并写出文件)."""
    src = tmp_path / "doc.mid.md"
    src.write_text(_SAMPLE_MD)

    def fake_generate(job: object) -> bool:
        import pathlib
        j = job  # type: ignore[assignment]
        pathlib.Path(j.output_path).parent.mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
        pathlib.Path(j.output_path).write_bytes(b"PNG")  # type: ignore[attr-defined]
        return True

    with patch("wenqiao.generate_cmd.OpenAIFigureRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.generate.side_effect = fake_generate
        instance.async_generate = AsyncMock(side_effect=fake_generate)

        result = CliRunner().invoke(
            main,
            ["generate", str(src), "--figures-config", str(tmp_path / "nonexistent.toml"),
             "--api-key", "sk-test", "--base-url", "http://localhost"],
        )

    assert result.exit_code == 0


def test_generate_start_end_id(tmp_path: Path) -> None:
    """--start-id / --end-id slices jobs by 1-based index (范围切片)."""
    # Make 3 figures in the doc (文档包含 3 个图片)
    md = ""
    for i in range(1, 4):
        md += f"<!-- label: fig:f{i} -->\n<!-- ai-generated: true -->\n<!-- ai-prompt: fig {i} -->\n![f{i}](fig-{i}.png)\n\n"
    src = tmp_path / "doc.mid.md"
    src.write_text(f"# T\n\n{md}")

    generated: list[str] = []

    def fake_generate(job: object) -> bool:
        import pathlib
        j = job  # type: ignore[assignment]
        pathlib.Path(j.output_path).parent.mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
        pathlib.Path(j.output_path).write_bytes(b"PNG")  # type: ignore[attr-defined]
        generated.append(str(j.src))  # type: ignore[attr-defined]
        return True

    with patch("wenqiao.generate_cmd.OpenAIFigureRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.generate.side_effect = fake_generate
        instance.async_generate = AsyncMock(side_effect=fake_generate)

        CliRunner().invoke(
            main,
            ["generate", str(src), "--start-id", "2", "--end-id", "2",
             "--api-key", "sk-test", "--base-url", "http://localhost"],
        )

    # Only the second figure should be generated (只有第 2 个图片被生成)
    assert len(generated) == 1
    assert "fig-2.png" in generated[0]


def test_generate_no_writeback(tmp_path: Path) -> None:
    """--no-writeback skips ai-done insertion (--no-writeback 跳过写回)."""
    src = tmp_path / "doc.mid.md"
    src.write_text(_SAMPLE_MD)

    def fake_generate(job: object) -> bool:
        import pathlib
        j = job  # type: ignore[assignment]
        pathlib.Path(j.output_path).parent.mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
        pathlib.Path(j.output_path).write_bytes(b"PNG")  # type: ignore[attr-defined]
        return True

    with patch("wenqiao.generate_cmd.OpenAIFigureRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.generate.side_effect = fake_generate
        instance.async_generate = AsyncMock(side_effect=fake_generate)

        CliRunner().invoke(
            main,
            ["generate", str(src), "--no-writeback",
             "--api-key", "sk-test", "--base-url", "http://localhost"],
        )

    assert "ai-done" not in src.read_text(encoding="utf-8")
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_generate_cmd.py -v --tb=short
```
Expected: FAIL — `No such command 'generate'`

**Step 3: Create generate_cmd.py**

Create `src/wenqiao/generate_cmd.py`:

```python
"""generate 子命令：并发生成 AI 图片。

Generate subcommand: concurrent AI figure generation from .mid.md files.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from wenqiao.diagnostic import DiagCollector
from wenqiao.genfig import collect_jobs, run_generate_figures_async
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
    end = end_id  # Python slice end is exclusive, but end_id is inclusive (Python 切片末为开区间)
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

    # Build runner (构建 runner)
    runner = OpenAIFigureRunner(
        api_key=api_key,
        base_url=base_url,
        model=model,
        config=figures_config,
    )

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
```

**Step 4: Register in cli.py**

In `src/wenqiao/cli.py`, add the import:

```python
from wenqiao.generate_cmd import generate_cmd
```

And at the bottom with the other registrations:

```python
cli.add_command(generate_cmd)
```

**Step 5: Run tests**

```bash
uv run pytest tests/test_generate_cmd.py -v --tb=short
```
Expected: All pass.

**Step 6: Commit**

```bash
git add src/wenqiao/generate_cmd.py tests/test_generate_cmd.py src/wenqiao/cli.py
git commit -m "feat: add generate subcommand for concurrent AI figure generation"
```

---

### Task 5: Update convert_cmd to use async and add --concurrency

**Files:**
- Modify: `src/wenqiao/cli.py:139-265` (convert_cmd figure generation block)

**Background:** `convert_cmd` currently calls `run_generate_figures()` (sync, sequential). Replace with `asyncio.run(run_generate_figures_async(...))`. Add `--concurrency` option. Keep `--figures-config` and `--force-regenerate` unchanged.

**Step 1: Write failing test**

Add to `tests/test_generate_cmd.py`:

```python
def test_convert_generates_figures_async(tmp_path: Path) -> None:
    """convert --generate-figures uses async runner (convert 使用异步 runner)."""
    src = tmp_path / "doc.mid.md"
    src.write_text(_SAMPLE_MD)

    def fake_generate(job: object) -> bool:
        import pathlib
        j = job  # type: ignore[assignment]
        pathlib.Path(j.output_path).parent.mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
        pathlib.Path(j.output_path).write_bytes(b"PNG")  # type: ignore[attr-defined]
        return True

    with patch("wenqiao.cli.OpenAIFigureRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.generate.side_effect = fake_generate
        instance.async_generate = AsyncMock(side_effect=fake_generate)

        result = CliRunner().invoke(
            main,
            [
                "convert", str(src),
                "--generate-figures",
                "--api-key", "sk-test",
                "--base-url", "http://localhost",
                "--concurrency", "2",
                "-o", str(tmp_path / "out.tex"),
            ],
        )

    assert result.exit_code == 0


def test_convert_concurrency_option_exists() -> None:
    """convert --help shows --concurrency option (--concurrency 选项存在)."""
    result = CliRunner().invoke(main, ["convert", "--help"])
    assert "--concurrency" in result.output
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/test_generate_cmd.py::test_convert_concurrency_option_exists -v
```
Expected: FAIL — `--concurrency` not in help output.

**Step 3: Update convert_cmd in cli.py**

Add `--concurrency` option to `convert_cmd` (after the `--force-regenerate` option block, before the function definition):

```python
@click.option(
    "--concurrency",
    "concurrency",
    default=4,
    show_default=True,
    help="Max concurrent figure generations (最大并发图片生成数)",
)
```

Add `concurrency: int` to the `convert_cmd` function signature.

Replace the figure generation block (currently around lines 248-265):

```python
    # Optional AI figure generation (可选 AI 图片生成)
    if generate_figures:
        from wenqiao.genfig import collect_jobs, run_generate_figures_async
        from wenqiao.genfig_openai import OpenAIFigureRunner

        base_dir = Path(filename).parent if filename != "<stdin>" else Path.cwd()
        runner = OpenAIFigureRunner(config=figures_config)

        try:
            jobs = collect_jobs(doc, base_dir=base_dir, force=True)
            success, fail = asyncio.run(
                run_generate_figures_async(
                    jobs,
                    runner,
                    concurrency=concurrency,
                    force=force_regenerate,
                    writeback=False,  # convert does not write back to source (convert 不写回)
                    echo=lambda msg: click.echo(msg, err=True),
                )
            )
        except (ImportError, OSError) as e:
            click.echo(f"[generate-figures] Runner failed: {e}", err=True)
            raise SystemExit(1)
        if fail > 0:
            click.echo(
                f"[generate-figures] {fail} figure(s) failed to generate.",
                err=True,
            )
```

Also add `import asyncio` at the top of `cli.py` (if not already present).

**Step 4: Run all tests**

```bash
uv run pytest tests/ -v --tb=short
```
Expected: All pass including previous tests.

**Step 5: Commit**

```bash
git add src/wenqiao/cli.py tests/test_generate_cmd.py
git commit -m "feat: update convert --generate-figures to use async runner, add --concurrency"
```

---

### Task 6: Final check

**Step 1: Full test suite**

```bash
make check
```
Expected: lint + typecheck + tests all pass.

**Step 2: Smoke test CLI help**

```bash
uv run wenqiao generate --help
uv run wenqiao convert --help | grep concurrency
```
Expected: Both show expected options.

**Step 3: Commit (if any fixups needed)**

```bash
git add -p
git commit -m "fix: address lint/typecheck issues in generate command"
```
