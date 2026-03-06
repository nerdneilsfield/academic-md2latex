"""Unified configuration for wenqiao (文桥).

统一配置对象，实现 PRD §10.1 优先级链：
CLI args > document directives > external config > template > defaults.

Architecture: dict-based layered merge. Each config source produces a plain dict
with only the keys it explicitly sets. Layers merge via dict.update().
(架构：基于字典的分层合并。每个配置源仅产出显式设置的键值对。)
"""

from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
    fields,
)
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from wenqiao.diagnostic import DiagCollector

# Module-level YAML parser (模块级 YAML 解析器)
_yaml = YAML(typ="safe")

# Type constraints for fields that renderers cast (渲染器依赖的字段类型约束)
_LIST_FIELDS = {"classoptions", "packages"}
_DICT_FIELDS = {"package_options"}

# Default config values matching PRD §10.2 (PRD §10.2 默认值)
_DEFAULTS: dict[str, object] = {
    "target": "latex",
    "mode": "full",
    "documentclass": "article",
    "classoptions": ["12pt", "a4paper"],
    "packages": ["amsmath", "graphicx"],
    "package_options": {},
    "bibliography": "",
    "bibstyle": "plain",
    "bibliography_mode": "auto",
    "code_style": "lstlisting",
    "thematic_break": "newpage",
    "ref_tilde": True,
    "title": "",
    "author": "",
    "date": "",
    "abstract": "",
    "preamble": "",
    "heading_id_style": "attr",
    "locale": "zh",
    "html_image_max_width": "92%",
    "strict": False,
    "verbose": False,
}


# Comprehensive package list shared by all presets (所有预设共享的完整宏包列表)
# Covers: math, symbols, graphics, hyperlinks, colors, code blocks,
# theorems, algorithms, and nice tables — the full wenqiao feature set.
# (涵盖：数学、符号、图形、超链接、颜色、代码块、定理、算法、美化表格)
_PRESET_PACKAGES = [
    "amsmath",       # math environments (数学环境)
    "amssymb",       # math symbols ∀ ∃ etc. (数学符号)
    "graphicx",      # images (图片)
    "xcolor",        # colors — must load before hyperref (颜色支持，须在 hyperref 之前加载)
    "listings",      # code blocks / lstlisting (代码块)
    "amsthm",        # theorem / lemma / proof environments (定理/引理/证明)
    "algorithm2e",   # algorithm environments (算法环境)
    "booktabs",      # professional table rules \toprule etc. (专业表格线)
    "hyperref",      # cross-references and hyperlinks — load last (交叉引用与超链接，最后加载)
]

# Built-in presets (内置预设字典)
_PRESETS: dict[str, dict[str, object]] = {
    "zh": {
        "documentclass": "ctexart",
        "classoptions": ["12pt", "a4paper"],
        "packages": list(_PRESET_PACKAGES),
        "locale": "zh",
        "preamble": "% Compiled with XeLaTeX recommended (建议使用 XeLaTeX 编译)\n",
    },
    "en": {
        "documentclass": "article",
        "classoptions": ["12pt", "a4paper"],
        "packages": list(_PRESET_PACKAGES),
        "locale": "en",
    },
}


@dataclass
class WenqiaoConfig:
    """Central configuration object (中央配置对象).

    Attributes follow PRD §10.2 naming (snake_case internally, kebab-case externally).
    This is the **resolved** config — all layers already merged.
    """

    # Output options (输出选项)
    target: str = "latex"
    mode: str = "full"

    # LaTeX options (LaTeX 选项)
    documentclass: str = "article"
    classoptions: list[str] = field(default_factory=lambda: ["12pt", "a4paper"])
    packages: list[str] = field(default_factory=lambda: ["amsmath", "graphicx"])
    package_options: dict[str, str] = field(default_factory=dict)
    bibliography: str = ""
    bibstyle: str = "plain"
    bibliography_mode: str = "auto"
    code_style: str = "lstlisting"  # lstlisting | minted
    thematic_break: str = "newpage"  # newpage | hrule | ignore
    ref_tilde: bool = True

    # Document metadata populated by directives (文档元信息，由指令填充)
    title: str = ""
    author: str = ""
    date: str = ""
    abstract: str = ""
    preamble: str = ""

    # Markdown options (Markdown 选项)
    heading_id_style: str = "attr"  # attr | html
    locale: str = "zh"  # zh | en
    html_image_max_width: str = "92%"  # HTML image max width (HTML 图片最大宽度)

    # Runtime flags (运行时标志，非序列化)
    strict: bool = False
    verbose: bool = False

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
        diag: DiagCollector | None = None,
    ) -> WenqiaoConfig:
        """Build config from dict with kebab/snake key normalization (从字典构建配置).

        Values of list or dict type are shallow-copied to prevent aliasing
        (list 和 dict 值浅拷贝以防止别名问题).

        Note:
            No type coercion is performed. Callers are responsible for ensuring
            value types match the declared field types (调用方需确保值类型与字段类型匹配).

        Args:
            data: Dictionary with kebab-case or snake_case keys (键可为 kebab 或 snake)
            diag: Optional diagnostic collector for unknown key warnings (可选诊断收集器)

        Returns:
            WenqiaoConfig with matched fields set, defaults for missing (匹配字段已设置)
        """
        valid_fields = {f.name for f in fields(cls)}
        kwargs: dict[str, object] = {}
        for key, value in data.items():
            norm = key.replace("-", "_")
            if norm not in valid_fields:
                if diag:
                    diag.info(f"Unknown config key '{key}' ignored (未知配置键 '{key}' 被忽略)")
                continue
            # Shallow-copy mutable containers to prevent aliasing (浅拷贝可变容器防止别名)
            if isinstance(value, list):
                value = list(value)
            elif isinstance(value, dict):
                value = dict(value)
            kwargs[norm] = value
        # Validate types for fields that renderers depend on (校验渲染器依赖的字段类型)
        for key in _LIST_FIELDS:
            if key in kwargs and not isinstance(kwargs[key], list):
                raise TypeError(
                    f"Config '{key}' must be a list, got {type(kwargs[key]).__name__}"
                    f" (配置 '{key}' 必须为列表)"
                )
        for key in _DICT_FIELDS:
            if key in kwargs and not isinstance(kwargs[key], dict):
                raise TypeError(
                    f"Config '{key}' must be a dict, got {type(kwargs[key]).__name__}"
                    f" (配置 '{key}' 必须为字典)"
                )
        # Validate list element types — renderers assume str elements (校验列表元素类型)
        for key in _LIST_FIELDS:
            val = kwargs.get(key)
            if isinstance(val, list):
                for i, elem in enumerate(val):
                    if not isinstance(elem, str):
                        raise TypeError(
                            f"Config '{key}[{i}]' must be str, got {type(elem).__name__}"
                            f" (配置 '{key}[{i}]' 必须为字符串)"
                        )
        return cls(**kwargs)  # type: ignore[arg-type]


def _normalize_keys(data: dict[str, object]) -> dict[str, object]:
    """Normalize kebab-case keys to snake_case (将 kebab-case 键归一化为 snake_case)."""
    return {k.replace("-", "_"): v for k, v in data.items()}


def resolve_config(
    cli_overrides: dict[str, object] | None = None,
    east_meta: dict[str, object] | None = None,
    config_dict: dict[str, object] | None = None,
    template_dict: dict[str, object] | None = None,
    preset_name: str | None = None,
) -> WenqiaoConfig:
    """Resolve final config by merging dict layers in priority order (按优先级合并配置).

    Priority (high -> low): CLI > document directives > config file > template > preset > defaults.
    Each layer is a plain dict with only the keys it explicitly sets.
    dict.update() naturally preserves lower-priority values for absent keys.

    Args:
        cli_overrides: CLI arg overrides, only non-None values (CLI 覆盖，仅非 None 值)
        east_meta: Document directive metadata (文档指令元数据)
        config_dict: Flattened config file dict (配置文件扁平字典)
        template_dict: Template file dict (模板文件字典)
        preset_name: Optional built-in preset name, e.g. "zh" or "en" (可选内置预设名)

    Returns:
        Fully resolved WenqiaoConfig (完全解析的配置)

    Raises:
        ValueError: If preset_name is not None and not in _PRESETS (预设名无效时抛出)
    """
    # Start with defaults (从默认值开始)
    merged: dict[str, object] = _DEFAULTS.copy()
    # Deep-copy mutable defaults to avoid shared state (深拷贝可变默认值)
    merged["classoptions"] = list(cast(list[str], _DEFAULTS["classoptions"]))
    merged["packages"] = list(cast(list[str], _DEFAULTS["packages"]))
    merged["package_options"] = dict(cast(dict[str, str], _DEFAULTS["package_options"]))

    # Layer preset — sits above defaults, below template (层: 预设，高于默认值，低于模板)
    if preset_name is not None:
        if preset_name not in _PRESETS:
            raise ValueError(
                f"unknown preset {preset_name!r}; available: {list(_PRESETS)}"
                f" (未知预设 {preset_name!r}；可用预设: {list(_PRESETS)})"
            )
        merged.update(_PRESETS[preset_name])
        # Deep-copy list values to prevent aliasing (深拷贝列表防止别名)
        for key in _LIST_FIELDS:
            if key in merged and isinstance(merged[key], list):
                merged[key] = list(cast(list[object], merged[key]))

    # Layer template (层: 模板)
    if template_dict:
        merged.update(_normalize_keys(template_dict))

    # Layer config file (层: 配置文件)
    if config_dict:
        merged.update(_normalize_keys(config_dict))

    # Layer document directives (层: 文档指令)
    if east_meta:
        merged.update(_normalize_keys(east_meta))

    # Layer CLI overrides — highest priority (层: CLI 参数，最高优先级)
    if cli_overrides:
        merged.update(_normalize_keys(cli_overrides))

    return WenqiaoConfig.from_dict(merged)


def load_template(
    path: Path,
    diag: DiagCollector | None = None,
) -> dict[str, object]:
    """Load LaTeX template from YAML file, return dict (从 YAML 文件加载 LaTeX 模板).

    Template keys are a subset of config (PRD §10.3):
    documentclass, classoptions, packages, package-options, extra-preamble, bibstyle.

    The key 'extra-preamble' is mapped to 'preamble' for WenqiaoConfig compatibility.
    (extra-preamble 映射为 preamble 以兼容 WenqiaoConfig。)

    Returns an empty dict if file does not exist or YAML parse fails.
    (文件不存在或 YAML 解析失败时返回空字典。)

    Args:
        path: Path to template file (模板文件路径)
        diag: Optional diagnostic collector (可选诊断收集器)

    Returns:
        Dict with only explicitly-set template keys (仅含显式设置键的字典)
    """
    if not path.exists():
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = _yaml.load(f)
    except (OSError, UnicodeDecodeError) as exc:
        msg = f"Cannot read template file: {path} ({exc})"
        if diag:
            diag.warning(msg)
        return {}
    except Exception as exc:
        msg = f"Failed to parse template YAML: {path} ({type(exc).__name__}: {exc})"
        if diag:
            diag.warning(msg)
        return {}

    if not isinstance(data, dict):
        return {}

    # Map template-specific keys to config keys (映射模板键到配置键)
    result = dict(data)
    if "extra-preamble" in result:
        result["preamble"] = result.pop("extra-preamble")

    return result


def load_config_file(
    path: Path,
    diag: DiagCollector | None = None,
) -> dict[str, object]:
    """Load config from YAML file, return flat dict (从 YAML 文件加载配置，返回扁平字典).

    Supports the nested structure from PRD §10.2:
    ```yaml
    default-target: latex
    latex:
      mode: full
      code-style: lstlisting
    markdown:
      locale: zh
    ```

    Nested sections ('latex', 'markdown') are flattened into a single dict.
    The special top-level key 'default-target' maps to 'target'.

    Note: When 'latex' and 'markdown' sections share a key name, later section wins.
    This is unlikely in practice since latex/markdown options are disjoint by design.
    (注意：latex 和 markdown 段的同名键后者覆盖前者，实际不太可能因为选项不重叠。)

    Returns an empty dict if:
    - File does not exist (文件不存在)
    - YAML parse fails (YAML 解析失败)
    - YAML root is not a dict (根节点非字典)

    Args:
        path: Path to config file (配置文件路径)
        diag: Optional diagnostic collector (可选诊断收集器)

    Returns:
        Flat dict with only explicitly-set keys (仅含显式设置键的扁平字典)
    """
    if not path.exists():
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = _yaml.load(f)
    except (OSError, UnicodeDecodeError) as exc:
        msg = f"Cannot read config file: {path} ({exc})"
        if diag:
            diag.warning(msg)
        return {}
    except Exception as exc:
        msg = f"Failed to parse config YAML: {path} ({type(exc).__name__}: {exc})"
        if diag:
            diag.warning(msg)
        return {}

    if not isinstance(data, dict):
        return {}

    # Flatten nested sections into single dict (展平嵌套段为单层字典)
    flat: dict[str, object] = {}

    for key, val in data.items():
        if key == "default-target":
            # Special top-level key (特殊顶层键映射)
            flat["target"] = val
        elif isinstance(val, dict):
            # Nested section like "latex:" or "markdown:" (嵌套段)
            for sub_key, sub_val in val.items():
                flat[sub_key] = sub_val
        else:
            flat[key] = val

    # Map extra-preamble → preamble for consistency with template loader
    # (将 extra-preamble 映射为 preamble，与模板加载器保持一致)
    if "extra-preamble" in flat:
        flat["preamble"] = flat.pop("extra-preamble")

    return flat
