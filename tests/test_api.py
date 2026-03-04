"""Tests for the public Python API (公共 Python API 测试).

Covers convert(), validate_text(), format_text(), and parse_document().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wenqiao import (
    ConversionError,
    ConvertResult,
    Document,
    WenqiaoConfig,
    convert,
    format_text,
    parse_document,
    validate_text,
)
from wenqiao.diagnostic import DiagLevel

# -- Fixtures (测试固件) -----------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"
MINIMAL_MD = FIXTURES / "minimal.mid.md"

SIMPLE_MD = "# Hello\n\nWorld.\n"


# -- convert() tests (convert 函数测试) --------------------------------------


def test_convert_string_to_latex() -> None:
    """Convert a simple string to LaTeX (简单字符串转 LaTeX)."""
    result = convert(SIMPLE_MD)
    assert isinstance(result, ConvertResult)
    assert "\\section{Hello}" in result.text or "Hello" in result.text
    assert "World" in result.text


def test_convert_file_path() -> None:
    """Convert from a file Path (从文件路径转换)."""
    result = convert(MINIMAL_MD)
    assert isinstance(result, ConvertResult)
    assert "Hello World" in result.text
    assert len(result.text) > 0


def test_convert_to_markdown() -> None:
    """Convert to Markdown target (转换为 Markdown 格式)."""
    result = convert(SIMPLE_MD, target="markdown")
    assert "Hello" in result.text
    assert "World" in result.text


def test_convert_to_html() -> None:
    """Convert to HTML target (转换为 HTML 格式)."""
    result = convert(SIMPLE_MD, target="html")
    assert "Hello" in result.text
    assert "World" in result.text


def test_convert_with_mode() -> None:
    """Convert with mode=body omits preamble (body 模式省略前导码)."""
    result_full = convert(SIMPLE_MD, target="latex", mode="full")
    result_body = convert(SIMPLE_MD, target="latex", mode="body")
    # full mode contains documentclass, body mode does not (full 模式含 documentclass)
    assert "\\documentclass" in result_full.text
    assert "\\documentclass" not in result_body.text


def test_convert_with_locale() -> None:
    """Convert with locale parameter (使用 locale 参数转换)."""
    result = convert(SIMPLE_MD, target="latex", locale="en")
    assert isinstance(result.config, WenqiaoConfig)
    # Config should reflect locale=en (配置应反映 locale=en)
    assert result.config.locale == "en"


def test_convert_with_config_dict() -> None:
    """Convert with dict overrides (使用字典覆盖转换)."""
    result = convert(SIMPLE_MD, config={"mode": "body", "locale": "en"})
    assert "\\documentclass" not in result.text


def test_convert_with_config_object() -> None:
    """Convert with WenqiaoConfig directly (直接使用 WenqiaoConfig 转换)."""
    cfg = WenqiaoConfig(mode="body", locale="en")
    result = convert(SIMPLE_MD, config=cfg)
    assert result.config is cfg
    assert "\\documentclass" not in result.text


def test_convert_with_template(tmp_path: Path) -> None:
    """Convert with template YAML (使用模板 YAML 转换)."""
    tpl = tmp_path / "test.yaml"
    tpl.write_text("documentclass: report\n", encoding="utf-8")
    result = convert(SIMPLE_MD, template=tpl)
    assert "report" in result.text


def test_convert_with_bib_path(tmp_path: Path) -> None:
    """Convert with bib file path for markdown target (Markdown 目标使用 bib 文件路径)."""
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text(
        "@article{wang2024,\n  author={Wang, X},\n  title={Test},\n  year={2024}\n}\n",
        encoding="utf-8",
    )
    md = "See [Wang](cite:wang2024).\n"
    result = convert(md, target="markdown", bib=bib_file)
    assert "Wang" in result.text


def test_convert_with_bib_string() -> None:
    """Convert with raw .bib text content (使用原始 .bib 文本内容转换)."""
    bib_text = "@article{wang2024,\n  author={Wang, X},\n  title={Test},\n  year={2024}\n}\n"
    md = "See [Wang](cite:wang2024).\n"
    result = convert(md, target="markdown", bib=bib_text)
    assert "Wang" in result.text


def test_convert_with_bib_dict() -> None:
    """Convert with pre-parsed bib dict (使用预解析的 bib 字典转换)."""
    bib_dict = {"wang2024": "Wang. Test. 2024."}
    md = "See [Wang](cite:wang2024).\n"
    result = convert(md, target="markdown", bib=bib_dict)
    assert "Wang" in result.text


def test_convert_strict_raises() -> None:
    """strict=True raises ConversionError on diagnostic errors (严格模式有错误时抛出异常)."""
    # Unmatched begin/end triggers an error diagnostic (不匹配的 begin/end 触发错误诊断)
    md = "<!-- begin: figure -->\nHello\n"
    with pytest.raises(ConversionError) as exc_info:
        convert(md, strict=True)
    assert len(exc_info.value.diagnostics) > 0


def test_convert_result_attributes() -> None:
    """Verify ConvertResult attributes (验证 ConvertResult 属性)."""
    result = convert(SIMPLE_MD)
    assert isinstance(result.text, str)
    assert isinstance(result.diagnostics, list)
    assert isinstance(result.config, WenqiaoConfig)
    assert isinstance(result.document, Document)


def test_convert_invalid_target() -> None:
    """Invalid target raises ValueError (无效目标格式抛出 ValueError)."""
    with pytest.raises(ValueError, match="Unsupported target"):
        convert(SIMPLE_MD, target="pdf")


def test_convert_target_from_config_dict() -> None:
    """Target in config dict overrides the default (配置字典中的 target 覆盖默认值)."""
    result = convert(SIMPLE_MD, config={"target": "html"})
    # Should render HTML, not LaTeX (应渲染 HTML 而非 LaTeX)
    assert "\\documentclass" not in result.text
    assert result.config.target == "html"


def test_convert_target_from_config_object() -> None:
    """Target from WenqiaoConfig object is respected (WenqiaoConfig 对象的 target 被使用)."""
    cfg = WenqiaoConfig(target="markdown", mode="full")
    result = convert(SIMPLE_MD, config=cfg)
    # Should render Markdown, not LaTeX (应渲染 Markdown 而非 LaTeX)
    assert "\\documentclass" not in result.text
    assert result.config.target == "markdown"


def test_convert_explicit_target_beats_config_dict() -> None:
    """Explicit target= beats config dict (显式 target 参数优先于配置字典)."""
    result = convert(SIMPLE_MD, target="html", config={"target": "markdown"})
    # Explicit target="html" wins — config dict "markdown" is overridden
    # (显式 target="html" 优先 — 配置字典的 "markdown" 被覆盖)
    assert result.config.target == "html"


# -- validate_text() tests (validate_text 函数测试) --------------------------


def test_validate_text_clean() -> None:
    """Clean document returns no diagnostics (干净文档无诊断信息)."""
    diags = validate_text(SIMPLE_MD)
    # Simple doc should have no errors (简单文档应无错误)
    errors = [d for d in diags if d.level == DiagLevel.ERROR]
    assert len(errors) == 0


def test_validate_text_missing_cite() -> None:
    """Missing citation key produces a warning (缺失引用键产生警告)."""
    md = "See [ref](cite:nonexistent_key).\n"
    # Provide empty bib to trigger missing-key warning (提供空 bib 触发缺失键警告)
    diags = validate_text(md, bib={})
    warnings = [d for d in diags if d.level == DiagLevel.WARNING]
    assert any("nonexistent_key" in d.message for d in warnings)


def test_validate_text_strict_raises() -> None:
    """strict=True raises on unmatched begin (严格模式对不匹配 begin 抛出异常)."""
    md = "<!-- begin: figure -->\nHello\n"
    with pytest.raises(ConversionError):
        validate_text(md, strict=True)


def test_validate_text_missing_image(tmp_path: Path) -> None:
    """Path source with missing local image produces diagnostic (路径源缺失本地图片产生诊断)."""
    md_file = tmp_path / "doc.mid.md"
    md_file.write_text("![Alt](missing.png)\n", encoding="utf-8")
    diags = validate_text(md_file)
    # Should report missing image file (应报告缺失的图片文件)
    assert any("missing" in d.message.lower() for d in diags)


def test_validate_text_url_image_no_warning(tmp_path: Path) -> None:
    """URL images are not flagged as missing (URL 图片不被标记为缺失)."""
    md_file = tmp_path / "doc.mid.md"
    md_file.write_text("![Alt](https://example.com/img.png)\n", encoding="utf-8")
    diags = validate_text(md_file)
    # URL images should not produce missing-file warnings (URL 图片不应产生文件缺失警告)
    image_diags = [d for d in diags if "img.png" in d.message]
    assert len(image_diags) == 0


# -- format_text() tests (format_text 函数测试) ------------------------------


def test_format_text_roundtrip() -> None:
    """Formatting is idempotent on already-formatted text (对已格式化文本幂等)."""
    formatted = format_text(SIMPLE_MD)
    assert isinstance(formatted, str)
    # Re-formatting should produce the same result (再次格式化应产生相同结果)
    reformatted = format_text(formatted)
    assert formatted == reformatted


def test_format_text_normalises() -> None:
    """format_text produces normalized output (格式化产生规范化输出)."""
    result = format_text(SIMPLE_MD)
    assert "Hello" in result
    assert len(result) > 0


# -- parse_document() tests (parse_document 函数测试) ------------------------


def test_parse_document_returns_document() -> None:
    """parse_document returns a Document instance (返回 Document 实例)."""
    doc = parse_document(SIMPLE_MD)
    assert isinstance(doc, Document)
    assert len(doc.children) > 0


def test_parse_document_from_path() -> None:
    """parse_document accepts a Path input (接受 Path 输入)."""
    doc = parse_document(MINIMAL_MD)
    assert isinstance(doc, Document)
    assert len(doc.children) > 0


# -- Regression: target=None defaults correctly (target=None 默认正确) --------


def test_convert_target_none_defaults_to_latex() -> None:
    """target=None falls through to config default 'latex' (target=None 回退到默认 latex)."""
    result = convert(SIMPLE_MD)
    assert "\\documentclass" in result.text


def test_convert_explicit_target_latex_overrides_config() -> None:
    """Explicit target='latex' overrides config target (显式 target='latex' 覆盖配置)."""
    result = convert(SIMPLE_MD, target="latex", config={"target": "html"})
    # Explicit arg wins — should produce LaTeX not HTML (显式参数优先)
    assert "\\documentclass" in result.text


# -- Regression: include-tex blocked for string sources (字符串源禁用 include-tex)


def test_include_tex_blocked_for_string_source() -> None:
    """include-tex is silently ignored for non-file sources (非文件源静默忽略 include-tex)."""
    md = "<!-- include-tex: nonexistent.tex -->\n\n# Hello\n"
    # Should NOT produce an error — include-tex is simply skipped (不应报错)
    result = convert(md)
    assert result.text  # Renders normally (正常渲染)


# -- Preset directive integration tests (预设指令集成测试) ----------------------


def test_preset_directive_zh_sets_ctexart() -> None:
    """Document with <!-- preset: zh --> should produce ctexart class (文档预设 zh 生效).

    Integration test: preset directive flows through pipeline to LaTeX output.
    (集成测试：预设指令通过管线流至 LaTeX 输出。)
    """
    from wenqiao.api import convert as api_convert

    result = api_convert("<!-- preset: zh -->\n\n# Hello\n")
    assert "ctexart" in result.text


def test_preset_kwarg_overrides_preset_directive() -> None:
    """preset kwarg should override document directive (preset 参数应覆盖文档指令).

    When the caller passes preset="en" and the document says <!-- preset: zh -->,
    the explicit kwarg wins (CLI > directive priority).
    (显式传参优先于文档指令，实现 CLI > 指令 的优先级。)
    """
    from wenqiao.api import convert as api_convert

    result = api_convert("<!-- preset: zh -->\n\n# Hello\n", preset="en")
    assert "article" in result.text
    assert "ctexart" not in result.text


def test_preset_unknown_raises_early() -> None:
    """convert() with unknown preset should raise ValueError before parsing (未知预设提前报错).

    Validates that the error is raised with a clear message listing valid presets.
    (验证错误提前抛出，消息中列出合法预设名。)
    """
    import pytest

    from wenqiao.api import convert as api_convert

    with pytest.raises(ValueError, match="unknown preset"):
        api_convert("# Hello\n", preset="nonexistent")


def test_preset_ignored_when_prebuilt_config() -> None:
    """Unknown preset is silently ignored when config is a pre-built WenqiaoConfig.

    The docstring contract: "Ignored when config is a pre-built WenqiaoConfig."
    Must NOT raise even if preset is unknown.
    (当 config 为预构建配置时，preset 参数应被忽略，即使预设名无效也不应报错。)
    """
    from wenqiao.api import convert as api_convert
    from wenqiao.config import WenqiaoConfig

    cfg = WenqiaoConfig()
    # Should not raise — preset is irrelevant when a pre-built config is provided
    # (不应抛出异常，预构建配置下 preset 无意义)
    result = api_convert("# Hello\n", config=cfg, preset="nonexistent-preset")
    assert result is not None
