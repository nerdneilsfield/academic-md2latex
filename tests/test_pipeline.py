"""Tests for pipeline module (管线模块测试).

Tests parse_and_process, build_config, inject_metadata, create_renderer, resolve_bib.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from md_mid.config import MdMidConfig
from md_mid.diagnostic import DiagCollector
from md_mid.nodes import Document
from md_mid.pipeline import (
    build_config,
    create_renderer,
    inject_metadata,
    parse_and_process,
    resolve_bib,
)

# -- parse_and_process tests (parse_and_process 测试) --------------------------


def test_parse_and_process_returns_document() -> None:
    """parse_and_process returns a Document with timing data (返回含计时数据的 Document)."""
    diag = DiagCollector("<test>")
    doc = parse_and_process("# Hello\n\nWorld.\n", "<test>", diag)
    assert isinstance(doc, Document)
    assert len(doc.children) > 0
    assert "parse" in diag.timings
    assert "process_comments" in diag.timings


def test_parse_and_process_with_directives() -> None:
    """Directives are processed into metadata (指令被处理到元数据中)."""
    md = "<!-- title: My Title -->\n\n# Hello\n"
    diag = DiagCollector("<test>")
    doc = parse_and_process(md, "<test>", diag)
    assert doc.metadata.get("title") == "My Title"


# -- build_config tests (build_config 测试) ------------------------------------


def test_build_config_defaults() -> None:
    """build_config with no overrides returns defaults (无覆盖返回默认配置)."""
    cfg = build_config({})
    assert isinstance(cfg, MdMidConfig)
    assert cfg.mode == "full"
    assert cfg.target == "latex"


def test_build_config_pre_built() -> None:
    """pre_built short-circuits config resolution (pre_built 直接返回)."""
    pre = MdMidConfig(mode="body")
    cfg = build_config({}, pre_built=pre)
    assert cfg is pre


def test_build_config_cli_overrides() -> None:
    """CLI overrides win over east_meta (CLI 覆盖优先于 east_meta)."""
    cfg = build_config(
        {"mode": "body"},
        cli_overrides={"mode": "fragment"},
    )
    assert cfg.mode == "fragment"


def test_build_config_template_path(tmp_path: Path) -> None:
    """Template file is loaded and applied (模板文件被加载和应用)."""
    tpl = tmp_path / "test.yaml"
    tpl.write_text("documentclass: report\n", encoding="utf-8")
    cfg = build_config({}, template_path=tpl)
    assert cfg.documentclass == "report"


# -- inject_metadata tests (inject_metadata 测试) ------------------------------


def test_inject_metadata_latex() -> None:
    """LaTeX target injects 12 metadata keys (LaTeX 目标注入 12 个元数据键)."""
    doc = Document()
    cfg = MdMidConfig(title="Test", documentclass="report")
    inject_metadata(doc, cfg, "latex")
    assert doc.metadata["title"] == "Test"
    assert doc.metadata["documentclass"] == "report"
    assert "bibliography_mode" in doc.metadata


def test_inject_metadata_html() -> None:
    """HTML target injects 4 metadata keys (HTML 目标注入 4 个元数据键)."""
    doc = Document()
    cfg = MdMidConfig(title="Test", author="A")
    inject_metadata(doc, cfg, "html")
    assert doc.metadata["title"] == "Test"
    assert doc.metadata["author"] == "A"
    assert "documentclass" not in doc.metadata


def test_inject_metadata_markdown_noop() -> None:
    """Markdown target injects nothing (Markdown 目标不注入任何内容)."""
    doc = Document()
    cfg = MdMidConfig(title="Test")
    inject_metadata(doc, cfg, "markdown")
    assert "title" not in doc.metadata


# -- create_renderer tests (create_renderer 测试) ------------------------------


def test_create_renderer_latex() -> None:
    """create_renderer returns LaTeXRenderer for 'latex' (返回 LaTeX 渲染器)."""
    from md_mid.latex import LaTeXRenderer

    cfg = MdMidConfig()
    diag = DiagCollector("<test>")
    r = create_renderer("latex", cfg, {}, diag)
    assert isinstance(r, LaTeXRenderer)


def test_create_renderer_markdown() -> None:
    """create_renderer returns MarkdownRenderer for 'markdown' (返回 Markdown 渲染器)."""
    from md_mid.markdown import MarkdownRenderer

    cfg = MdMidConfig()
    diag = DiagCollector("<test>")
    r = create_renderer("markdown", cfg, {}, diag)
    assert isinstance(r, MarkdownRenderer)


def test_create_renderer_html() -> None:
    """create_renderer returns HTMLRenderer for 'html' (返回 HTML 渲染器)."""
    from md_mid.html import HTMLRenderer

    cfg = MdMidConfig()
    diag = DiagCollector("<test>")
    r = create_renderer("html", cfg, {}, diag)
    assert isinstance(r, HTMLRenderer)


def test_create_renderer_invalid() -> None:
    """create_renderer raises ValueError for unknown target (未知目标抛出 ValueError)."""
    cfg = MdMidConfig()
    diag = DiagCollector("<test>")
    with pytest.raises(ValueError, match="Unsupported target"):
        create_renderer("pdf", cfg, {}, diag)


# -- resolve_bib tests (resolve_bib 测试) --------------------------------------


def test_resolve_bib_none() -> None:
    """None returns empty dict (None 返回空字典)."""
    assert resolve_bib(None) == {}


def test_resolve_bib_dict_passthrough() -> None:
    """Dict input is returned as-is (字典输入直接返回)."""
    d = {"key": "val"}
    assert resolve_bib(d) is d


def test_resolve_bib_path(tmp_path: Path) -> None:
    """Path input is read and parsed (路径输入被读取并解析)."""
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text(
        "@article{wang2024,\n  author={Wang},\n  title={T},\n  year={2024}\n}\n",
        encoding="utf-8",
    )
    result = resolve_bib(bib_file)
    assert "wang2024" in result


def test_resolve_bib_string() -> None:
    """String input is parsed as raw .bib text (字符串输入作为原始 .bib 文本解析)."""
    bib_text = "@article{smith2024,\n  author={Smith},\n  title={S},\n  year={2024}\n}\n"
    result = resolve_bib(bib_text)
    assert "smith2024" in result
