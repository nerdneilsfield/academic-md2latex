"""Public Python API for md-mid.

提供程序化调用 md-mid 转换管线的公共接口。

Exposes convert(), validate_text(), format_text(), and parse_document()
for programmatic use from Python code (build systems, Jupyter, web services).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from md_mid.bibtex import parse_bib
from md_mid.comment import process_comments
from md_mid.config import MdMidConfig, load_template, resolve_config
from md_mid.diagnostic import DiagCollector, Diagnostic  # noqa: F401 (re-exported)
from md_mid.nodes import Document
from md_mid.parser import parse
from md_mid.validate import collect_east_info, validate_bib, validate_crossrefs

# -- Result / Error types (结果/错误类型) ------------------------------------


@dataclass(frozen=True)
class ConvertResult:
    """Conversion result (转换结果).

    Attributes:
        text: Rendered output string (渲染输出字符串)
        diagnostics: List of diagnostic messages (诊断信息列表)
        config: Resolved configuration used (解析后的配置)
        document: EAST document tree for further inspection (EAST 文档树)
    """

    text: str
    diagnostics: list[Diagnostic]
    config: MdMidConfig
    document: Document


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


def _resolve_bib(
    bib: Path | str | dict[str, str] | None,
) -> dict[str, str]:
    """Normalise bib input to parsed dict (将 bib 输入归一化为解析后的字典).

    Args:
        bib: .bib file path / raw text / pre-parsed dict / None
             (.bib 文件路径 / 原始文本 / 预解析字典 / None)

    Returns:
        Parsed bibliography dict (解析后的参考文献字典)
    """
    if bib is None:
        return {}
    if isinstance(bib, dict):
        return bib
    if isinstance(bib, Path):
        return parse_bib(bib.read_text(encoding="utf-8"))
    # str — treat as raw .bib text (字符串视为原始 .bib 文本)
    return parse_bib(bib)


def _render(
    east: Document,
    cfg: MdMidConfig,
    target: str,
    bib: dict[str, str],
    diag: DiagCollector,
) -> str:
    """Dispatch to the correct renderer (分派到正确的渲染器).

    Args:
        east: EAST document tree (EAST 文档树)
        cfg: Resolved configuration (解析后的配置)
        target: Output format (输出格式)
        bib: Parsed bibliography (解析后的参考文献)
        diag: Diagnostic collector (诊断收集器)

    Returns:
        Rendered text (渲染后的文本)

    Raises:
        ValueError: If target is not supported (目标格式不受支持时)
    """
    if target == "latex":
        from md_mid.latex import LaTeXRenderer

        # Inject config metadata into EAST for renderer (注入配置元数据供渲染器使用)
        east.metadata.update(
            {
                "documentclass": cfg.documentclass,
                "classoptions": cfg.classoptions,
                "packages": cfg.packages,
                "package_options": cfg.package_options,
                "bibliography": cfg.bibliography,
                "bibstyle": cfg.bibstyle,
                "preamble": cfg.preamble,
                "bibliography_mode": cfg.bibliography_mode,
                "title": cfg.title,
                "author": cfg.author,
                "date": cfg.date,
                "abstract": cfg.abstract,
            }
        )
        renderer = LaTeXRenderer(
            mode=cfg.mode,
            ref_tilde=cfg.ref_tilde,
            code_style=cfg.code_style,
            thematic_break=cfg.thematic_break,
            locale=cfg.locale,
            diag=diag,
        )
        return renderer.render(east)

    if target == "markdown":
        from md_mid.markdown import MarkdownRenderer

        renderer_md = MarkdownRenderer(
            bib=bib,
            heading_id_style=cfg.heading_id_style,
            locale=cfg.locale,
            mode=cfg.mode,
            diag=diag,
        )
        return renderer_md.render(east)

    if target == "html":
        from md_mid.html import HTMLRenderer

        # Inject document metadata for HTML renderer (注入文档元数据供 HTML 渲染器使用)
        east.metadata.update(
            {
                "title": cfg.title,
                "author": cfg.author,
                "date": cfg.date,
                "abstract": cfg.abstract,
            }
        )
        renderer_html = HTMLRenderer(
            mode=cfg.mode,
            bib=bib,
            locale=cfg.locale,
            diag=diag,
        )
        return renderer_html.render(east)

    raise ValueError(
        f"Unsupported target: {target!r}, must be 'latex', 'markdown', or 'html'"
        f" (不支持的目标格式: {target!r})"
    )


# -- Public API (公共 API) ---------------------------------------------------


def convert(
    source: str | Path,
    *,
    target: str = "latex",
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
    # Validate target early (提前校验目标格式)
    if target not in ("latex", "markdown", "html"):
        raise ValueError(
            f"Unsupported target: {target!r}, must be 'latex', 'markdown', or 'html'"
            f" (不支持的目标格式: {target!r})"
        )

    text, filename = _read_source(source)
    diag = DiagCollector(filename)

    # Parse and process comment directives (解析并处理注释指令)
    doc = parse(text, diag=diag)
    east = process_comments(doc, filename, diag=diag)

    # Resolve configuration (解析配置)
    if isinstance(config, MdMidConfig):
        cfg = config
    else:
        # Build CLI-style override dict from kwargs (从参数构建覆盖字典)
        cli_dict: dict[str, object] = {}
        if mode is not None:
            cli_dict["mode"] = mode
        if locale is not None:
            cli_dict["locale"] = locale
        if target != "latex":
            cli_dict["target"] = target

        # If config is a dict, merge it into cli_dict (字典配置合并到覆盖字典)
        if isinstance(config, dict):
            cli_dict.update(config)

        tpl_dict = load_template(template) if template else None

        cfg = resolve_config(
            cli_overrides=cli_dict if cli_dict else None,
            east_meta=east.metadata,
            template_dict=tpl_dict,
        )

    # Resolve bibliography (解析参考文献)
    bib_entries = _resolve_bib(bib)

    # Strict-mode check before rendering (渲染前的严格模式检查)
    if strict and diag.has_errors:
        raise ConversionError(
            "Conversion aborted: diagnostic errors found (转换中止：发现诊断错误)",
            diagnostics=list(diag.diagnostics),
        )

    # Render (渲染)
    rendered = _render(east, cfg, target, bib_entries, diag)

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
    doc = parse(text, diag=diag)
    east = process_comments(doc, filename, diag=diag)

    # Collect EAST info (收集 EAST 信息)
    info = collect_east_info(east)

    # Resolve bib and validate (解析参考文献并验证)
    bib_entries = _resolve_bib(bib)
    if bib_entries or info.cite_keys:
        validate_bib(info, bib_entries, diag)
    validate_crossrefs(info, diag)

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

    doc = parse(text, diag=diag)
    east = process_comments(doc, filename, diag=diag)
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

    doc = parse(text, diag=diag)
    return process_comments(doc, filename, diag=diag)
