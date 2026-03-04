"""Public Python API for md-mid.

提供程序化调用 md-mid 转换管线的公共接口。

Exposes convert(), validate_text(), format_text(), and parse_document()
for programmatic use from Python code (build systems, Jupyter, web services).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from md_mid.config import MdMidConfig
from md_mid.diagnostic import DiagCollector, Diagnostic
from md_mid.nodes import Document
from md_mid.pipeline import (
    build_config,
    create_renderer,
    inject_metadata,
    parse_and_process,
    resolve_bib,
)
from md_mid.validate import collect_east_info, validate_bib, validate_crossrefs, validate_images

# -- Result / Error types (结果/错误类型) ------------------------------------


@dataclass(frozen=True)
class ConvertResult:
    """Conversion result (转换结果).

    Attributes:
        text: Rendered output string (渲染输出字符串)
        diagnostics: List of diagnostic messages (诊断信息列表)
        config: Resolved configuration used (解析后的配置)
        document: EAST document tree for further inspection (EAST 文档树)
        timings: Pipeline phase timings (管线阶段计时)
    """

    text: str
    diagnostics: list[Diagnostic]
    config: MdMidConfig
    document: Document
    timings: dict[str, float] = field(default_factory=dict)  # Phase timings (阶段计时)


class ConversionError(Exception):
    """Raised on strict-mode errors or invalid config (严格模式错误或无效配置时抛出).

    Attributes:
        diagnostics: Attached diagnostic list (附属诊断列表)
    """

    def __init__(self, message: str, diagnostics: list[Diagnostic]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


# -- Internal helpers (内部辅助函数) -----------------------------------------


def _read_source(source: str | Path) -> tuple[str, str]:
    """Read source text and derive filename (读取源文本并推导文件名).

    Args:
        source: Markdown text or file path (Markdown 文本或文件路径)

    Returns:
        Tuple of (text, filename) (文本与文件名的元组)
    """
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8"), str(source)
    return source, "<string>"


# -- Public API (公共 API) ---------------------------------------------------


def convert(
    source: str | Path,
    *,
    target: str | None = None,
    mode: str | None = None,
    locale: str | None = None,
    config: MdMidConfig | dict[str, object] | None = None,
    template: Path | None = None,
    bib: Path | str | dict[str, str] | None = None,
    strict: bool = False,
) -> ConvertResult:
    """Convert academic Markdown to LaTeX, Markdown, or HTML.

    将学术 Markdown 转换为 LaTeX、Markdown 或 HTML。

    Args:
        source: Markdown text or file path (Markdown 文本或文件路径)
        target: Output format — "latex" / "markdown" / "html" (输出格式)
        mode: Output mode — "full" / "body" / "fragment" (输出模式)
        locale: Label language — "zh" / "en" (标签语言)
        config: Pre-built config or overrides dict (预构建配置或覆盖字典)
        template: Template YAML file path (模板 YAML 文件路径)
        bib: .bib file path / raw text / pre-parsed dict (参考文献来源)
        strict: Raise ConversionError on diagnostic errors (有诊断错误时抛出异常)

    Returns:
        ConvertResult with rendered text and metadata (包含渲染文本和元数据的结果)

    Raises:
        ConversionError: If strict=True and diagnostics contain errors (严格模式下有错误时)
        ValueError: If target is not supported (目标格式不支持时)
    """
    # Validate explicit target early (提前校验显式目标格式)
    if target is not None and target not in ("latex", "markdown", "html"):
        raise ValueError(
            f"Unsupported target: {target!r}, must be 'latex', 'markdown', or 'html'"
            f" (不支持的目标格式: {target!r})"
        )

    text, filename = _read_source(source)
    diag = DiagCollector(filename)

    # Parse and process comment directives (解析并处理注释指令)
    east = parse_and_process(text, filename, diag)

    # Resolve configuration (解析配置)
    # Build CLI-style override dict: config dict first, then explicit kwargs on top
    # (构建覆盖字典：先合并配置字典，再用显式参数覆盖)
    cli_dict: dict[str, object] = {}
    if isinstance(config, dict):
        cli_dict.update(config)
    # Explicit kwargs take precedence over config dict (显式参数优先于配置字典)
    if mode is not None:
        cli_dict["mode"] = mode
    if locale is not None:
        cli_dict["locale"] = locale
    if target is not None:
        cli_dict["target"] = target

    cfg = build_config(
        east.metadata,
        cli_overrides=cli_dict if cli_dict else None,
        template_path=template,
        pre_built=config if isinstance(config, MdMidConfig) else None,
    )

    # Use resolved target from config — dict/MdMidConfig may override the default
    # (使用配置中解析后的目标格式 — 字典/MdMidConfig 可能覆盖默认值)
    effective_target = cfg.target

    # Validate resolved target (校验解析后的目标格式)
    if effective_target not in ("latex", "markdown", "html"):
        raise ValueError(
            f"Unsupported target: {effective_target!r}, must be 'latex', 'markdown', or 'html'"
            f" (不支持的目标格式: {effective_target!r})"
        )

    # Resolve bibliography (解析参考文献)
    bib_entries = resolve_bib(bib)

    # Strict-mode check before rendering (渲染前的严格模式检查)
    if strict and diag.has_errors:
        raise ConversionError(
            "Conversion aborted: diagnostic errors found (转换中止：发现诊断错误)",
            diagnostics=list(diag.diagnostics),
        )

    # Inject metadata and render (注入元数据并渲染)
    inject_metadata(east, cfg, effective_target)
    renderer = create_renderer(effective_target, cfg, bib_entries, diag)
    with diag.phase("render"):
        rendered: str = renderer.render(east)

    # Post-render strict check (渲染后的严格模式检查)
    if strict and diag.has_errors:
        raise ConversionError(
            "Conversion completed with errors (转换完成但存在错误)",
            diagnostics=list(diag.diagnostics),
        )

    return ConvertResult(
        text=rendered,
        diagnostics=list(diag.diagnostics),
        config=cfg,
        document=east,
        timings=dict(diag.timings),
    )


def validate_text(
    source: str | Path,
    *,
    bib: Path | str | dict[str, str] | None = None,
    strict: bool = False,
) -> list[Diagnostic]:
    """Validate an academic Markdown document.

    验证学术 Markdown 文档。

    Runs EAST walker + validators to check citations, cross-references, etc.
    (运行 EAST 遍历器和验证器检查引用、交叉引用等。)

    Args:
        source: Markdown text or file path (Markdown 文本或文件路径)
        bib: .bib file path / raw text / pre-parsed dict (参考文献来源)
        strict: Raise ConversionError on errors (有错误时抛出异常)

    Returns:
        List of diagnostic messages (诊断信息列表)

    Raises:
        ConversionError: If strict=True and diagnostics contain errors (严格模式下有错误时)
    """
    text, filename = _read_source(source)
    diag = DiagCollector(filename)

    # Parse and process (解析并处理)
    east = parse_and_process(text, filename, diag)

    # Collect EAST info (收集 EAST 信息)
    info = collect_east_info(east)

    # Resolve bib and validate (解析参考文献并验证)
    bib_entries = resolve_bib(bib)
    if bib_entries or info.cite_keys:
        validate_bib(info, bib_entries, diag)
    validate_crossrefs(info, diag)

    # Validate images when source is a file path (文件路径时验证图片)
    if isinstance(source, Path):
        validate_images(info, source.parent, diag)

    if strict and diag.has_errors:
        raise ConversionError(
            "Validation failed (验证失败)",
            diagnostics=list(diag.diagnostics),
        )

    return list(diag.diagnostics)


def format_text(source: str | Path) -> str:
    """Format academic Markdown via round-trip normalisation.

    通过往返规范化格式化学术 Markdown。

    Parse → process_comments → MarkdownRenderer(mode="full").render().

    Args:
        source: Markdown text or file path (Markdown 文本或文件路径)

    Returns:
        Formatted Markdown text (格式化后的 Markdown 文本)
    """
    from md_mid.markdown import MarkdownRenderer

    text, filename = _read_source(source)
    diag = DiagCollector(filename)

    east = parse_and_process(text, filename, diag)
    renderer = MarkdownRenderer(mode="full", diag=diag)
    return renderer.render(east)


def parse_document(source: str | Path) -> Document:
    """Parse academic Markdown into an EAST Document tree.

    将学术 Markdown 解析为 EAST 文档树。

    Low-level: parse() → process_comments(). Returns EAST Document
    for custom processing.
    (低级 API：解析并处理注释，返回 EAST 文档供自定义处理。)

    Args:
        source: Markdown text or file path (Markdown 文本或文件路径)

    Returns:
        EAST Document node (EAST 文档节点)
    """
    text, filename = _read_source(source)
    diag = DiagCollector(filename)
    return parse_and_process(text, filename, diag)
