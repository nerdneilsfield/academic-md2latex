"""Shared pipeline orchestration for all entry points.

共享管线编排，供所有入口点 (cli/api/format_cmd/validate) 使用。
Eliminates ~250 lines of duplicated parse→process→config→render logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from md_mid.bibtex import parse_bib
from md_mid.comment import process_comments
from md_mid.config import (
    MdMidConfig,
    load_config_file,
    load_template,
    resolve_config,
)
from md_mid.diagnostic import DiagCollector
from md_mid.nodes import Document
from md_mid.parser import parse


class Renderer(Protocol):
    """Protocol for all renderers — LaTeX, Markdown, HTML (渲染器协议)."""

    def render(self, node: Document) -> str: ...


def parse_and_process(
    text: str,
    filename: str,
    diag: DiagCollector,
) -> Document:
    """Parse Markdown and process comment directives (解析 Markdown 并处理注释指令).

    Wraps parse() + process_comments() with phase timing.
    (封装 parse() + process_comments() 并添加阶段计时。)

    Args:
        text: Markdown source text (Markdown 源文本)
        filename: Source filename for diagnostics (用于诊断的源文件名)
        diag: Diagnostic collector (诊断收集器)

    Returns:
        Processed EAST Document (处理后的 EAST 文档)
    """
    with diag.phase("parse"):
        doc = parse(text, diag=diag)
    with diag.phase("process_comments"):
        return process_comments(doc, filename, diag=diag)


def build_config(
    east_meta: dict[str, object],
    *,
    cli_overrides: dict[str, object] | None = None,
    config_path: Path | None = None,
    template_path: Path | None = None,
    pre_built: MdMidConfig | None = None,
    diag: DiagCollector | None = None,
) -> MdMidConfig:
    """Unified config resolution (统一配置解析).

    Handles the full priority chain: CLI > doc > config file > template > defaults.
    If pre_built is provided, returns it directly (short-circuit).
    (如果提供了 pre_built，直接返回。)

    Args:
        east_meta: Document directive metadata (文档指令元数据)
        cli_overrides: CLI arg overrides (CLI 参数覆盖)
        config_path: External config file path (外部配置文件路径)
        template_path: Template YAML file path (模板 YAML 文件路径)
        pre_built: Pre-built MdMidConfig to use directly (直接使用的预构建配置)
        diag: Diagnostic collector for config warnings (配置警告的诊断收集器)

    Returns:
        Fully resolved MdMidConfig (完全解析的配置)
    """
    if pre_built is not None:
        return pre_built

    tpl_dict = load_template(template_path, diag=diag) if template_path else None
    cfg_dict = load_config_file(config_path, diag=diag) if config_path else None

    return resolve_config(
        cli_overrides=cli_overrides if cli_overrides else None,
        east_meta=east_meta,
        config_dict=cfg_dict,
        template_dict=tpl_dict,
    )


def inject_metadata(
    east: Document,
    cfg: MdMidConfig,
    target: str,
) -> None:
    """Inject config metadata into EAST for renderer use (注入配置元数据供渲染器使用).

    LaTeX needs 12 keys; HTML needs 4 keys; Markdown needs nothing.
    (LaTeX 需要 12 个键；HTML 需要 4 个键；Markdown 无需注入。)

    Args:
        east: EAST document tree (EAST 文档树)
        cfg: Resolved configuration (解析后的配置)
        target: Output format — latex / markdown / html (输出格式)
    """
    if target == "latex":
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
    elif target == "html":
        east.metadata.update(
            {
                "title": cfg.title,
                "author": cfg.author,
                "date": cfg.date,
                "abstract": cfg.abstract,
            }
        )


def create_renderer(
    target: str,
    cfg: MdMidConfig,
    bib: dict[str, str],
    diag: DiagCollector,
) -> Renderer:
    """Dispatch and construct the correct renderer (分派并构造正确的渲染器).

    Args:
        target: Output format — latex / markdown / html (输出格式)
        cfg: Resolved configuration (解析后的配置)
        bib: Parsed bibliography entries (解析后的参考文献)
        diag: Diagnostic collector (诊断收集器)

    Returns:
        Renderer instance satisfying Renderer protocol (满足 Renderer 协议的渲染器实例)

    Raises:
        ValueError: If target is not supported (目标格式不受支持时)
    """
    if target == "latex":
        from md_mid.latex import LaTeXRenderer

        return LaTeXRenderer(
            mode=cfg.mode,
            ref_tilde=cfg.ref_tilde,
            code_style=cfg.code_style,
            thematic_break=cfg.thematic_break,
            locale=cfg.locale,
            diag=diag,
        )

    if target == "markdown":
        from md_mid.markdown import MarkdownRenderer

        return MarkdownRenderer(
            bib=bib,
            heading_id_style=cfg.heading_id_style,
            locale=cfg.locale,
            mode=cfg.mode,
            diag=diag,
        )

    if target == "html":
        from md_mid.html import HTMLRenderer

        return HTMLRenderer(
            mode=cfg.mode,
            bib=bib,
            locale=cfg.locale,
            diag=diag,
        )

    raise ValueError(
        f"Unsupported target: {target!r}, must be 'latex', 'markdown', or 'html'"
        f" (不支持的目标格式: {target!r})"
    )


def resolve_bib(bib: Path | str | dict[str, str] | None) -> dict[str, str]:
    """Normalize bib input to parsed dict (将 bib 输入归一化为解析后的字典).

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
