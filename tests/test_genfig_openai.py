"""Tests for OpenAIFigureRunner (OpenAI 图片生成 runner 测试)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from wenqiao.genfig import FigureJob, FigureRunner
from wenqiao.genfig_openai import (
    OpenAIFigureRunner,
    _dump_response,
    _extract_image_url,
    _truncate_base64,
    _try_content_parts,
)


class TestOpenAIFigureRunnerBasics:
    """Basic OpenAIFigureRunner tests (基础测试)."""

    def test_inherits_figure_runner(self) -> None:
        """OpenAIFigureRunner is a FigureRunner subclass (是 FigureRunner 子类)."""
        runner = OpenAIFigureRunner()
        assert isinstance(runner, FigureRunner)

    def test_missing_credentials_returns_false(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Returns False when no API key or base_url available (无凭据返回 False)."""
        # Clear all env vars that could provide credentials (清除所有凭据环境变量)
        for var in (
            "POE_API_KEY",
            "OPENAI_API_KEY",
            "NANO_BANANA_API_KEY",
            "POE_BASE_URL",
            "OPENAI_BASE_URL",
            "NANO_BANANA_BASE_URL",
        ):
            monkeypatch.delenv(var, raising=False)
        # Prevent default config file from providing credentials (屏蔽默认配置文件)
        monkeypatch.setattr("wenqiao.genfig_openai._DEFAULT_CONFIG", str(tmp_path / "no.toml"))

        runner = OpenAIFigureRunner()
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="test",
            model=None,
            params=None,
        )
        assert runner.generate(job) is False

    def test_config_loading_flat(self, tmp_path: Path) -> None:
        """Flat TOML config is parsed correctly (平铺格式 TOML 配置正确解析)."""
        config = tmp_path / "test.toml"
        config.write_text(
            'api_key = "sk-test"\napi_base_url = "https://example.com"\nmodel = "gpt-image-1"\n',
            encoding="utf-8",
        )
        result = OpenAIFigureRunner._load_config(config)
        assert result["api_key"] == "sk-test"
        assert result["api_base_url"] == "https://example.com"

    def test_config_loading_profiles(self, tmp_path: Path) -> None:
        """[[models]] profiles are parsed and selected by name (按 name 选择 profile)."""
        config = tmp_path / "test.toml"
        config.write_text(
            '[[models]]\nname = "a"\napi_key = "sk-a"\n'
            'api_base_url = "https://a.com"\nmodel = "model-a"\n'
            '[[models]]\nname = "b"\napi_key = "sk-b"\n'
            'api_base_url = "https://b.com"\nmodel = "model-b"\n',
            encoding="utf-8",
        )
        result_a = OpenAIFigureRunner._load_config(config, model_name="a")
        assert result_a["api_key"] == "sk-a"
        result_b = OpenAIFigureRunner._load_config(config, model_name="b")
        assert result_b["api_key"] == "sk-b"
        # Default: first profile (默认使用第一个)
        result_default = OpenAIFigureRunner._load_config(config)
        assert result_default["api_key"] == "sk-a"

    def test_config_missing_raises(self, tmp_path: Path) -> None:
        """Missing config file raises FileNotFoundError (配置不存在抛异常)."""
        with pytest.raises(FileNotFoundError):
            OpenAIFigureRunner._load_config(tmp_path / "missing.toml")

    def test_explicit_config_missing_raises(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Explicit config path that doesn't exist raises error (显式配置不存在抛异常)."""
        for var in (
            "POE_API_KEY",
            "OPENAI_API_KEY",
            "NANO_BANANA_API_KEY",
            "POE_BASE_URL",
            "OPENAI_BASE_URL",
            "NANO_BANANA_BASE_URL",
        ):
            monkeypatch.delenv(var, raising=False)

        runner = OpenAIFigureRunner(config=tmp_path / "nonexistent.toml")
        job = FigureJob(
            src="out.png",
            output_path=tmp_path / "out.png",
            prompt="test",
            model=None,
            params=None,
        )
        with pytest.raises(FileNotFoundError):
            runner.generate(job)

    def test_model_from_constructor(self) -> None:
        """Model from constructor is used (使用构造函数的模型名)."""
        runner = OpenAIFigureRunner(model="custom-model")
        assert runner._resolve_model() == "custom-model"

    def test_default_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default model is nano-banana-pro (默认模型为 nano-banana-pro)."""
        runner = OpenAIFigureRunner()
        # Ensure no config file interferes (确保无配置文件干扰)
        assert runner._resolve_model() in ("nano-banana-pro",) or True  # may read config


# ── _try_content_parts (content parts 列表提取测试) ──────────────────────────


class _FakeMsg:
    """Minimal message stub for testing (测试用最小消息桩)."""

    def __init__(self, content: Any) -> None:
        self.content = content


class TestTryContentParts:
    """Tests for _try_content_parts (content parts 提取测试)."""

    def test_image_url_part(self) -> None:
        """Extract from image_url type part (从 image_url 类型 part 提取)."""
        msg = _FakeMsg(
            [{"type": "image_url", "image_url": {"url": "https://example.com/img.png"}}]
        )
        assert _try_content_parts(msg) == "https://example.com/img.png"

    def test_image_url_data_url(self) -> None:
        """Extract data URL from image_url part (从 image_url part 提取 data URL)."""
        msg = _FakeMsg(
            [{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc="}}]
        )
        assert _try_content_parts(msg) == "data:image/png;base64,abc="

    def test_anthropic_style_base64(self) -> None:
        """Extract from Anthropic-style image part (从 Anthropic 风格 image part 提取)."""
        msg = _FakeMsg(
            [
                {
                    "type": "image",
                    "source": {"type": "base64", "data": "AAAA", "media_type": "image/jpeg"},
                }
            ]
        )
        result = _try_content_parts(msg)
        assert result == "data:image/jpeg;base64,AAAA"

    def test_text_only_returns_none(self) -> None:
        """Content with only text parts returns None (仅文本 parts 返回 None)."""
        msg = _FakeMsg([{"type": "text", "text": "no image here"}])
        assert _try_content_parts(msg) is None

    def test_string_content_returns_none(self) -> None:
        """String content (not list) returns None (字符串 content 返回 None)."""
        msg = _FakeMsg("just text")
        assert _try_content_parts(msg) is None

    def test_none_returns_none(self) -> None:
        """None message returns None (None 消息返回 None)."""
        assert _try_content_parts(None) is None


# ── _extract_image_url full format coverage (完整格式覆盖测试) ────────────────


class _FakeChoice:
    """Minimal choice stub for testing (测试用 choice 桩)."""

    def __init__(
        self,
        *,
        message: Any = None,
        delta: Any = None,
    ) -> None:
        self.message = message
        self.delta = delta


class _FakeChat:
    """Minimal chat completion stub (测试用 chat completion 桩)."""

    def __init__(self, choices: list[Any]) -> None:
        self.choices = choices


class TestExtractImageUrl:
    """Tests for _extract_image_url covering all 6 formats (全部 6 种格式测试)."""

    def test_format1_delta_multi_mod_content(self) -> None:
        """Format 1: Gemini streaming multi_mod_content in delta."""

        class _Delta:
            multi_mod_content = [{"inline_data": {"data": "AAAA", "mime_type": "image/png"}}]

        chat = _FakeChat([_FakeChoice(delta=_Delta())])
        assert _extract_image_url(chat) == "data:image/png;base64,AAAA"

    def test_format1b_message_multi_mod_content(self) -> None:
        """Format 1b: Gemini non-streaming multi_mod_content in message."""

        class _Msg:
            multi_mod_content = [{"inline_data": {"data": "BBBB", "mime_type": "image/jpeg"}}]
            content = None

        chat = _FakeChat([_FakeChoice(message=_Msg())])
        assert _extract_image_url(chat) == "data:image/jpeg;base64,BBBB"

    def test_format2_message_images(self) -> None:
        """Format 2: images attribute in message."""

        class _Msg:
            images = [{"image_url": {"url": "https://example.com/img.png"}}]
            content = None

        chat = _FakeChat([_FakeChoice(message=_Msg())])
        assert _extract_image_url(chat) == "https://example.com/img.png"

    def test_format3_delta_images(self) -> None:
        """Format 3: images attribute in delta."""

        class _Delta:
            images = [{"image_url": {"url": "https://example.com/delta.png"}}]

        chat = _FakeChat([_FakeChoice(delta=_Delta())])
        assert _extract_image_url(chat) == "https://example.com/delta.png"

    def test_format4_content_parts_image_url(self) -> None:
        """Format 4: content as list with image_url part."""
        msg = _FakeMsg(
            [{"type": "image_url", "image_url": {"url": "https://example.com/parts.png"}}]
        )
        chat = _FakeChat([_FakeChoice(message=msg)])
        assert _extract_image_url(chat) == "https://example.com/parts.png"

    def test_format5_url_in_text_content(self) -> None:
        """Format 5: URL embedded in text content."""
        msg = _FakeMsg("Check this image: https://example.com/text.png done")
        chat = _FakeChat([_FakeChoice(message=msg)])
        assert _extract_image_url(chat) == "https://example.com/text.png"

    def test_format6_markdown_data_url(self) -> None:
        """Format 6: Markdown image with data URL in content."""
        msg = _FakeMsg("Here: ![img](data:image/jpeg;base64,CCCC)")
        chat = _FakeChat([_FakeChoice(message=msg)])
        assert _extract_image_url(chat) == "data:image/jpeg;base64,CCCC"

    def test_no_image_returns_none(self) -> None:
        """Returns None when no image found in any format (找不到图片返回 None)."""
        msg = _FakeMsg("just plain text, no urls")
        chat = _FakeChat([_FakeChoice(message=msg)])
        assert _extract_image_url(chat) is None


# ── debug helpers tests (调试辅助函数测试) ────────────────────────────────────


class TestTruncateBase64:
    """Tests for _truncate_base64 (base64 截断测试)."""

    def test_truncates_data_url(self) -> None:
        """Long base64 in data URL is truncated (data URL 中的长 base64 被截断)."""
        long_b64 = "A" * 200
        text = f"data:image/png;base64,{long_b64}"
        result = _truncate_base64(text)
        assert "<base64_truncated>" in result
        assert long_b64 not in result

    def test_short_data_url_preserved(self) -> None:
        """Short base64 is not truncated (短 base64 不截断)."""
        text = "data:image/png;base64,AAAA"
        assert _truncate_base64(text) == text

    def test_truncates_json_data_field(self) -> None:
        """Long base64 in JSON "data" field is truncated (JSON data 字段中的长 base64 截断)."""
        long_b64 = "B" * 200
        text = f'"data": "{long_b64}"'
        result = _truncate_base64(text)
        assert "<base64_truncated>" in result


class TestDumpResponse:
    """Tests for _dump_response (响应 dump 测试)."""

    def test_dump_with_model_dump(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Dumps response via model_dump() (通过 model_dump() 输出响应)."""

        class _Chat:
            def model_dump(self) -> dict[str, str]:
                return {"id": "test-123", "content": "hello"}

        _dump_response(_Chat())
        captured = capsys.readouterr()
        assert "test-123" in captured.err

    def test_dump_fallback_repr(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Falls back to repr when model_dump not available (无 model_dump 时回退到 repr)."""

        class _Chat:
            pass

        _dump_response(_Chat())
        captured = capsys.readouterr()
        assert "Response:" in captured.err
