"""EAST 验证模块：检查引用、交叉引用和图片完整性。

Validation module: check citations, cross-references, and image integrity
against the EAST tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import click

from md_mid.diagnostic import DiagCollector
from md_mid.nodes import (
    Citation,
    CrossRef,
    Figure,
    Image,
    Node,
    Table,
)
from md_mid.pipeline import build_config, parse_and_process, resolve_bib


@dataclass
class ValidationInfo:
    """Collected references from an EAST tree (从 EAST 树收集的引用信息).

    Attributes:
        cite_keys: Citation keys found in Citation nodes (引用键)
        labels: Labels from node metadata (节点标签)
        crossref_labels: Labels from CrossRef nodes (交叉引用标签)
        image_srcs: Image source paths from Figure/Image nodes (图片路径)
    """

    cite_keys: set[str] = field(default_factory=set)
    labels: set[str] = field(default_factory=set)
    crossref_labels: set[str] = field(default_factory=set)
    image_srcs: list[str] = field(default_factory=list)


def collect_east_info(node: Node) -> ValidationInfo:
    """Single-pass recursive walker to collect validation info (单遍递归收集验证信息).

    Handles Table.headers (list[list[Node]]) and Table.rows (list[list[list[Node]]])
    since citations/refs can appear inside table cells.
    (处理表格单元格中的引用/交叉引用)

    Args:
        node: Root EAST node to walk (待遍历的 EAST 根节点)

    Returns:
        Collected validation info (收集到的验证信息)
    """
    info = ValidationInfo()
    _walk(node, info)
    return info


def _walk(node: Node, info: ValidationInfo) -> None:
    """Recursively walk an EAST node tree (递归遍历 EAST 节点树)."""
    # Collect from current node (从当前节点收集)
    if isinstance(node, Citation):
        info.cite_keys.update(node.keys)
    elif isinstance(node, CrossRef):
        if node.label:
            info.crossref_labels.add(node.label)
    elif isinstance(node, Figure):
        if node.src:
            info.image_srcs.append(node.src)
    elif isinstance(node, Image):
        if node.src:
            info.image_srcs.append(node.src)

    # Collect labels from metadata (从元数据收集标签)
    label = node.metadata.get("label")
    if isinstance(label, str) and label:
        info.labels.add(label)

    # Walk table cells — headers and rows contain nested node lists
    # (遍历表格单元格 — headers 和 rows 包含嵌套节点列表)
    if isinstance(node, Table):
        for cell in node.headers:
            for cell_node in cell:
                _walk(cell_node, info)
        for row in node.rows:
            for cell in row:
                for cell_node in cell:
                    _walk(cell_node, info)

    # Walk children (遍历子节点)
    for child in node.children:
        _walk(child, info)


def validate_bib(
    info: ValidationInfo,
    bib_entries: dict[str, str],
    diag: DiagCollector,
) -> None:
    """Check that all citation keys exist in .bib entries (检查引用键是否存在于 .bib 条目中).

    Args:
        info: Collected EAST info (EAST 收集信息)
        bib_entries: Parsed bib entries keyed by cite key (解析后的 bib 条目)
        diag: Diagnostic collector (诊断收集器)
    """
    for key in sorted(info.cite_keys):
        if key not in bib_entries:
            diag.warning(
                f"Citation key '{key}' not found in bibliography (引用键未在参考文献中找到)"
            )


def validate_crossrefs(info: ValidationInfo, diag: DiagCollector) -> None:
    """Check that all cross-ref labels have matching definitions (检查交叉引用标签是否有定义).

    Args:
        info: Collected EAST info (EAST 收集信息)
        diag: Diagnostic collector (诊断收集器)
    """
    for label in sorted(info.crossref_labels):
        if label not in info.labels:
            diag.warning(f"Cross-reference '{label}' has no matching label (交叉引用无对应标签)")


def validate_images(
    info: ValidationInfo,
    base_dir: Path,
    diag: DiagCollector,
) -> None:
    """Check that image source files exist on disk (检查图片源文件是否存在).

    Skips URLs (http/https) and AI-generated placeholders.
    (跳过 URL 和 AI 生成的占位符)

    Args:
        info: Collected EAST info (EAST 收集信息)
        base_dir: Base directory for resolving relative paths (相对路径解析基目录)
        diag: Diagnostic collector (诊断收集器)
    """
    for src in info.image_srcs:
        # Skip URLs (跳过 URL)
        if src.startswith(("http://", "https://", "data:")):
            continue
        resolved = base_dir / src
        if not resolved.exists():
            diag.warning(f"Image file not found: {src} (图片文件未找到)")


@click.command("validate")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--bib",
    "bib_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="BibTeX file for citation validation (用于验证引用的 BibTeX 文件)",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="External config file (外部配置文件, md-mid.yaml)",
)
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="LaTeX template file (LaTeX 模板文件, .yaml)",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit 1 on any diagnostic errors (有诊断错误时以退出码 1 退出)",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show all diagnostics including info (显示全部诊断信息)",
)
def validate_cmd(
    input: Path,
    bib_path: Path | None,
    config_path: Path | None,
    template_path: Path | None,
    strict: bool,
    verbose: bool,
) -> None:
    """Validate an academic Markdown file (验证学术 Markdown 文件).

    Checks citations against .bib, cross-references, and image file existence.
    (检查引用、交叉引用和图片文件是否完整。)
    """
    text = input.read_text(encoding="utf-8")
    filename = str(input)
    diag = DiagCollector(filename)

    # Parse and process comment directives (解析并处理注释指令)
    east = parse_and_process(text, filename, diag)

    # Optionally resolve config for metadata (可选：解析配置获取元数据)
    if config_path or template_path:
        try:
            build_config(
                east.metadata,
                config_path=config_path,
                template_path=template_path,
                diag=diag,
            )
        except TypeError as e:
            click.echo(f"Configuration error: {e}", err=True)
            raise SystemExit(1)

    # Collect info from EAST (从 EAST 收集信息)
    info = collect_east_info(east)

    # Resolve bib source: --bib flag > east.metadata["bibliography"]
    # (解析 bib 来源：--bib 标志 > east.metadata 中的 bibliography)
    bib_entries: dict[str, str] = {}
    effective_bib_path = bib_path
    if effective_bib_path is None:
        bib_meta = east.metadata.get("bibliography")
        if isinstance(bib_meta, str) and bib_meta:
            candidate = input.parent / bib_meta
            if candidate.exists():
                effective_bib_path = candidate

    if effective_bib_path is not None:
        try:
            bib_entries = resolve_bib(effective_bib_path)
        except Exception as exc:
            click.echo(f"[WARNING] Failed to parse {effective_bib_path}: {exc}", err=True)

    # Run validators (运行验证器)
    if bib_entries or info.cite_keys:
        validate_bib(info, bib_entries, diag)
    validate_crossrefs(info, diag)
    validate_images(info, input.parent, diag)

    # Output diagnostics (输出诊断信息)
    has_warnings = bool(diag.warnings)
    if verbose:
        for d in diag.diagnostics:
            click.echo(str(d), err=True)
    elif has_warnings or diag.has_errors:
        for d in diag.warnings + diag.errors:
            click.echo(str(d), err=True)

    # Exit code (退出码)
    if diag.has_errors:
        raise SystemExit(1)
    if strict and has_warnings:
        raise SystemExit(1)
