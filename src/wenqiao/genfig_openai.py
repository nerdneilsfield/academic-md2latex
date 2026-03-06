"""OpenAI-compatible figure generation runner.

OpenAI 兼容图片生成 runner。
Wraps OpenAI/Poe/Gemini-compatible APIs for image generation via chat completions.
"""

from __future__ import annotations

import base64
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

from wenqiao.genfig import FigureJob, FigureRunner

# Default TOML config path (默认配置路径)
_DEFAULT_CONFIG = "~/.config/skiils.toml"
# Default model name (默认模型名)
_DEFAULT_MODEL = "nano-banana-pro"

# Parameters that belong to the Images API — embed into prompt instead of passing to chat.completions
# (图片 API 专属参数 — 嵌入 prompt，不传给 chat.completions)
_IMAGES_API_ONLY_PARAMS: frozenset[str] = frozenset({"size", "quality", "style", "n"})


class OpenAIFigureRunner(FigureRunner):
    """OpenAI-compatible figure runner (OpenAI 兼容图片生成 runner).

    Wraps OpenAI/Poe/Gemini-compatible APIs for image generation.
    (封装 OpenAI/Poe/Gemini 兼容 API 进行图片生成。)

    Args:
        api_key: API key (API 密钥, env: OPENAI_API_KEY / POE_API_KEY)
        base_url: API base URL (API 基础 URL, env: OPENAI_BASE_URL / POE_BASE_URL)
        model: Model name, default "nano-banana-pro" (模型名)
        config: TOML config file path for credentials (TOML 配置文件路径)
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        config: Path | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._config_path = config

    # ── public interface (公开接口) ────────────────────────────────────────

    def generate(self, job: FigureJob) -> bool:
        """Generate image via OpenAI-compatible API (通过 API 生成图片).

        Args:
            job: Figure generation job (图片生成作业)

        Returns:
            True if generation succeeded and output file exists (成功返回 True)
        """
        api_key, base_url = self._resolve_auth()
        if not api_key or not base_url:
            sys.stderr.write(
                "Missing API key or base URL. Set env vars, pass api_key/base_url, "
                "or use config with api_key/api_base_url.\n"
            )
            return False

        model = self._resolve_model()

        try:
            import openai
        except ImportError as exc:
            sys.stderr.write(f"Missing dependency: openai ({exc}).\n")
            return False

        # Separate chat-compatible params from Images-API-only ones (分离 chat 参数与图片 API 专属参数)
        extra_params: dict[str, Any] = {}
        prompt_suffix: list[str] = []
        for k, v in (job.params or {}).items():
            if k in _IMAGES_API_ONLY_PARAMS:
                prompt_suffix.append(f"{k}: {v}")  # embed into prompt (嵌入 prompt)
            else:
                extra_params[k] = v
        effective_prompt = job.prompt
        if prompt_suffix:
            effective_prompt = job.prompt + "\n" + ", ".join(prompt_suffix)
        ok = self._call_api_and_save(
            openai,
            api_key,
            base_url,
            model,
            effective_prompt,
            job.output_path,
            extra_params,
        )
        return ok and job.output_path.is_file()

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
            sys.stderr.write(
                "Missing API key or base URL. (缺少 API key 或 base URL)\n"
            )
            return False

        model = self._resolve_model()

        try:
            import openai
        except ImportError as exc:
            sys.stderr.write(f"Missing dependency: openai ({exc}).\n")
            return False

        # Separate chat-compatible params from Images-API-only ones (分离 chat 参数与图片 API 专属参数)
        extra_params: dict[str, Any] = {}
        prompt_suffix: list[str] = []
        for k, v in (job.params or {}).items():
            if k in _IMAGES_API_ONLY_PARAMS:
                prompt_suffix.append(f"{k}: {v}")  # embed into prompt (嵌入 prompt)
            else:
                extra_params[k] = v
        effective_prompt = job.prompt
        if prompt_suffix:
            effective_prompt = job.prompt + "\n" + ", ".join(prompt_suffix)

        try:
            client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            chat = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": effective_prompt}],
                **extra_params,
            )
            image_url = _extract_image_url(chat)
            if not image_url:
                sys.stderr.write("No image URL or data found in model output.\n")
                _dump_response(chat)
                return False
        except Exception as exc:
            sys.stderr.write(f"Async API call failed: {exc}\n")
            return False

        try:
            _save_image(image_url, job.output_path)
        except Exception as exc:
            sys.stderr.write(f"Failed to save image: {exc}\n")
            return False

        return job.output_path.is_file()

    # ── auth resolution (认证解析) ────────────────────────────────────────

    def _resolve_auth(self) -> tuple[str | None, str | None]:
        """Resolve API key and base URL from args / config / env (解析认证信息)."""
        cfg_key: str | None = None
        cfg_base: str | None = None

        # Try TOML config (尝试 TOML 配置)
        config_path = self._config_path or Path(_DEFAULT_CONFIG).expanduser()
        if isinstance(config_path, Path) and config_path.exists():
            cfg = self._load_config(config_path, model_name=self._model)
            cfg_key = cfg.get("api_key")
            cfg_base = cfg.get("api_base_url")
        elif self._config_path is not None and not config_path.exists():
            # Explicit config path that doesn't exist (显式指定的配置不存在)
            raise FileNotFoundError(f"config not found: {config_path}")

        api_key = (
            self._api_key
            or cfg_key
            or os.getenv("POE_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("NANO_BANANA_API_KEY")
        )
        base_url = (
            self._base_url
            or cfg_base
            or os.getenv("POE_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("NANO_BANANA_BASE_URL")
        )
        return api_key, base_url

    def _resolve_model(self) -> str:
        """Resolve actual model name from config profile / default.

        ``self._model`` is treated as a profile selector (name in [[models]]).
        The actual model name for the API comes from the selected profile's
        ``model`` or ``image_model`` field.

        self._model 作为 profile 选择器（[[models]] 中的 name 字段）。
        实际传给 API 的模型名来自所选 profile 的 model / image_model 字段。
        """
        config_path = self._config_path or Path(_DEFAULT_CONFIG).expanduser()
        if isinstance(config_path, Path) and config_path.exists():
            try:
                cfg = self._load_config(config_path, model_name=self._model)
                model = cfg.get("model") or cfg.get("image_model")
                if model:
                    return str(model)
            except Exception:
                pass

        # No config: self._model as direct model name fallback (无配置时直接用作模型名)
        return self._model or _DEFAULT_MODEL

    # ── config loading (配置加载) ──────────────────────────────────────────

    @staticmethod
    def _load_config(path: Path, model_name: str | None = None) -> dict[str, Any]:
        """Load TOML config file, optionally selecting a named model profile.

        加载 TOML 配置文件，可通过 model_name 选择具名模型配置项。

        Supports two layouts (支持两种格式):
          - Flat: top-level ``api_key``, ``api_base_url``, ``model`` keys.
          - Profiles: ``[[models]]`` array, each entry with a ``name`` field.
            If ``model_name`` is given, the matching entry is returned.
            If omitted, the first entry is used.

        Args:
            path: Path to TOML config file (TOML 配置文件路径)
            model_name: Profile name to select from ``[[models]]`` array (模型配置名)

        Returns:
            Config dictionary for the selected profile (选中的配置字典)

        Raises:
            FileNotFoundError: If config file does not exist (配置文件不存在)
            KeyError: If ``model_name`` not found in ``[[models]]`` (找不到指定 profile)
        """
        if not path.exists():
            raise FileNotFoundError(f"config not found: {path}")
        import tomllib

        data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))

        # [[models]] array layout (profiles 格式)
        profiles = data.get("models")
        if isinstance(profiles, list) and profiles:
            if model_name is not None:
                for entry in profiles:
                    if isinstance(entry, dict) and entry.get("name") == model_name:
                        return dict(entry)
                raise KeyError(
                    f"Model profile '{model_name}' not found in {path} "
                    f"(可用 profile: {[e.get('name') for e in profiles if isinstance(e, dict)]})"
                )
            # No name given — use first profile (未指定时用第一个)
            return dict(profiles[0])

        # Flat layout — return top-level keys (平铺格式)
        return dict(data)

    # ── API call and image saving (API 调用与图片保存) ─────────────────────

    @staticmethod
    def _call_api_and_save(
        openai: Any,
        api_key: str,
        base_url: str,
        model: str,
        prompt: str,
        output_path: Path,
        extra_params: dict[str, Any] | None = None,
    ) -> bool:
        """Call OpenAI-compatible API and save generated image (调用 API 并保存图片).

        Args:
            openai: The openai module (openai 模块)
            api_key: API key (API 密钥)
            base_url: API base URL (API 基础 URL)
            model: Model name (模型名)
            prompt: Generation prompt (生成提示词)
            output_path: Path to save image (图片保存路径)
            extra_params: Extra kwargs passed to chat.completions.create (额外参数，透传给 API)

        Returns:
            True on success (成功返回 True)
        """
        try:
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            chat = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **(extra_params or {}),
            )
            image_url = _extract_image_url(chat)
            if not image_url:
                sys.stderr.write("No image URL or data found in model output.\n")
                _dump_response(chat)
                return False
        except Exception as exc:
            sys.stderr.write(f"API call failed: {exc}\n")
            return False

        try:
            _save_image(image_url, output_path)
        except Exception as exc:
            sys.stderr.write(f"Failed to save image: {exc}\n")
            return False

        return True


# ── image extraction helpers (图片提取辅助函数) ──────────────────────────────


def _extract_image_url(chat: Any) -> str | None:
    """Extract image URL or data URL from chat completion response.

    从聊天补全响应中提取图片 URL 或 data URL。

    Supports multiple response formats: Gemini multi_mod_content,
    OpenAI images, URL in content, Markdown data URL.

    Args:
        chat: Chat completion response object (聊天补全响应对象)

    Returns:
        Image URL/data string, or None if not found (图片 URL 或 None)
    """
    choice = chat.choices[0]
    image_url: str | None = None

    # Format 1: multi_mod_content in delta (Gemini streaming)
    image_url = _try_multi_mod_content(getattr(choice, "delta", None))

    # Format 1b: multi_mod_content in message (Gemini non-streaming)
    if not image_url:
        image_url = _try_multi_mod_content(getattr(choice, "message", None))

    # Format 2: images in message (图片在 message 中)
    if not image_url:
        image_url = _try_images_attr(getattr(choice, "message", None))

    # Format 3: images in delta (图片在 delta 中)
    if not image_url:
        image_url = _try_images_attr(getattr(choice, "delta", None))

    # Format 4: content as list of parts with image_url (内容为 parts 列表含 image_url)
    # e.g. GPT-4o / multimodal: [{"type": "image_url", "image_url": {"url": "..."}}]
    if not image_url:
        image_url = _try_content_parts(getattr(choice, "message", None))

    # Format 5: URL in message content text (内容文本中的 URL)
    if not image_url:
        content = _get_text_content(choice)
        if content:
            image_url = _extract_first_url(content)

    # Format 6: Markdown data URL in content (内容中的 Markdown data URL)
    if not image_url:
        content = _get_text_content(choice)
        if content:
            m = re.search(r"!\[.*?\]\((data:image/[^)]+)\)", content)
            if m:
                image_url = m.group(1)

    return image_url


def _get_text_content(choice: Any) -> str:
    """Extract text content from a choice, handling str or list-of-parts.

    从 choice 提取文本内容，处理字符串或 parts 列表两种格式。

    Args:
        choice: Chat completion choice object (聊天补全 choice 对象)

    Returns:
        Text content string, empty if not found (文本内容，找不到返回空字符串)
    """
    raw = getattr(getattr(choice, "message", None), "content", None)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        # Concatenate text parts (拼接文本 parts)
        parts: list[str] = []
        for part in raw:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "\n".join(parts)
    return ""


def _try_content_parts(msg: Any) -> str | None:
    """Try to extract image from content as list of parts (尝试从 content parts 列表提取图片).

    Handles GPT-4o / multimodal responses where content is a list:
    ``[{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]``

    Args:
        msg: Message object with content attribute (含 content 属性的消息对象)

    Returns:
        Image URL/data string, or None (图片 URL 或 None)
    """
    if msg is None:
        return None
    content = getattr(msg, "content", None)
    if not isinstance(content, list):
        return None
    try:
        for part in content:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type", "")
            # {"type": "image_url", "image_url": {"url": "..."}}
            if ptype == "image_url":
                iu = part.get("image_url")
                if isinstance(iu, dict):
                    url = iu.get("url")
                    if isinstance(url, str):
                        return url
            # {"type": "image", "source": {"data": "...", "media_type": "..."}}
            # (Anthropic-style proxy format)
            if ptype == "image":
                src = part.get("source")
                if isinstance(src, dict) and src.get("type") == "base64":
                    b64 = src.get("data")
                    mime = src.get("media_type", "image/png")
                    if isinstance(b64, str):
                        return f"data:{mime};base64,{b64}"
    except (TypeError, KeyError):
        pass
    return None


def _try_multi_mod_content(obj: Any) -> str | None:
    """Try to extract image from multi_mod_content attribute (尝试从 multi_mod_content 提取图片)."""
    if obj is None:
        return None
    mmc = getattr(obj, "multi_mod_content", None)
    if not mmc:
        return None
    try:
        item = mmc[0]
        inline_data = (
            item.get("inline_data")
            if isinstance(item, dict)
            else getattr(item, "inline_data", None)
        )
        if not inline_data:
            return None
        if isinstance(inline_data, dict):
            b64 = inline_data.get("data")
            mime = inline_data.get("mime_type", "image/jpeg")
        else:
            b64 = getattr(inline_data, "data", None)
            mime = getattr(inline_data, "mime_type", "image/jpeg")
        if not b64:
            return None
        return b64 if b64.startswith("data:") else f"data:{mime};base64,{b64}"
    except (IndexError, AttributeError, TypeError):
        return None


def _try_images_attr(obj: Any) -> str | None:
    """Try to extract image URL from images attribute (尝试从 images 属性提取图片 URL)."""
    if obj is None:
        return None
    images = getattr(obj, "images", None)
    if not images:
        return None
    try:
        img = images[0]
        if isinstance(img, dict):
            url: str | None = img.get("image_url", {}).get("url")
            return url
        iu = img.image_url
        if isinstance(iu, dict):
            url_val: str | None = iu.get("url")
            return url_val
        result: str = iu.url
        return result
    except (IndexError, AttributeError, TypeError):
        return None


def _extract_first_url(text: str) -> str | None:
    """Extract first URL from text content (从文本中提取第一个 URL).

    Prefers Markdown reference-style links, falls back to any URL.

    Args:
        text: Text to search (待搜索文本)

    Returns:
        First URL found, or None (第一个 URL 或 None)
    """
    # Prefer Markdown reference-style links: [id]: URL (优先引用式链接)
    ref_links: list[str] = re.findall(r"^\[[^\]]+\]:\s*(\S+)", text, flags=re.M)
    if ref_links:
        return ref_links[0]
    # Fallback: any URL (回退：任意 URL)
    urls: list[str] = re.findall(r"https?://\S+", text)
    return urls[0] if urls else None


# ── debug helpers (调试辅助函数) ──────────────────────────────────────────────


def _truncate_base64(text: str, _max_length: int = 100) -> str:
    """Truncate long base64 strings in text for cleaner logs (截断日志中的长 base64 字符串).

    Args:
        text: Text possibly containing base64 data (可能含 base64 的文本)
        _max_length: Minimum length to trigger truncation (触发截断的最小长度)

    Returns:
        Text with long base64 strings replaced by placeholder (替换后的文本)
    """
    # data URL base64 (data:image/...;base64,XXXXX)
    text = re.sub(
        r"(data:image/[^;]+;base64,)[A-Za-z0-9+/=]{100,}",
        r"\1<base64_truncated>",
        text,
    )
    # 'data': 'XXXXX' (single quotes)
    text = re.sub(
        r"('data':\s*')[A-Za-z0-9+/=]{100,}(')",
        r"\1<base64_truncated>\2",
        text,
    )
    # "data": "XXXXX" (double quotes)
    text = re.sub(
        r'("data":\s*")[A-Za-z0-9+/=]{100,}(")',
        r"\1<base64_truncated>\2",
        text,
    )
    return text


def _dump_response(chat: Any) -> None:
    """Dump API response structure to stderr for debugging (输出 API 响应结构到 stderr 用于调试).

    Args:
        chat: Chat completion response object (聊天补全响应对象)
    """
    import json

    try:
        response_dict = (
            chat.model_dump() if hasattr(chat, "model_dump") else chat.dict()
        )
        response_str = json.dumps(response_dict, indent=2, ensure_ascii=False)
        response_str = _truncate_base64(response_str)
        sys.stderr.write(f"Response structure:\n{response_str}\n")
    except Exception:
        sys.stderr.write(f"Response: {_truncate_base64(repr(chat))}\n")


# ── image saving helpers (图片保存辅助函数) ───────────────────────────────────


def _save_image(url_or_data: str, output: Path) -> None:
    """Save image from URL or base64 data URL (从 URL 或 base64 保存图片).

    Args:
        url_or_data: URL string or data URL (URL 字符串或 data URL)
        output: Output file path (输出路径)

    Raises:
        ValueError: If format is unrecognized (格式无法识别时)
    """
    if url_or_data.startswith("data:"):
        _save_base64_image(url_or_data, output)
    elif url_or_data.startswith(("http://", "https://")):
        _download(url_or_data, output)
    else:
        # Try as raw base64 data (尝试作为原始 base64 数据)
        try:
            image_data = base64.b64decode(url_or_data)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(image_data)
        except Exception as exc:
            raise ValueError(f"Unknown image format: {url_or_data[:50]}... (未知图片格式)") from exc


def _save_base64_image(data_url: str, output: Path) -> None:
    """Save a base64-encoded data URL to file (保存 base64 data URL 到文件).

    Args:
        data_url: Data URL string (data URL 字符串)
        output: Output file path (输出路径)
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    base64_data = data_url.split(",", 1)[1] if "," in data_url else data_url
    output.write_bytes(base64.b64decode(base64_data))


def _download(url: str, output: Path) -> None:
    """Download an image from HTTP/HTTPS URL (从 URL 下载图片).

    Args:
        url: Image URL (图片 URL)
        output: Output file path (输出路径)
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "nanobanana-runner"})
    with urllib.request.urlopen(req) as resp, output.open("wb") as f:  # noqa: S310
        f.write(resp.read())
