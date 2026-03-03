"""Unified configuration for md-mid.

统一配置对象，实现 PRD §10.1 优先级链：
CLI args > document directives > external config > template > defaults.

Architecture: dict-based layered merge. Each config source produces a plain dict
with only the keys it explicitly sets. Layers merge via dict.update().
(架构：基于字典的分层合并。每个配置源仅产出显式设置的键值对。)
"""

from __future__ import annotations

import logging
from dataclasses import (
    dataclass,
    field,
    fields,
)
from pathlib import Path
from typing import cast

from ruamel.yaml import YAML

# Module-level YAML parser and logger (模块级 YAML 解析器与日志)
_yaml = YAML(typ="safe")
_log = logging.getLogger(__name__)

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
    "strict": False,
    "verbose": False,
}


@dataclass
class MdMidConfig:
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
    code_style: str = "lstlisting"       # lstlisting | minted
    thematic_break: str = "newpage"      # newpage | hrule | ignore
    ref_tilde: bool = True

    # Document metadata populated by directives (文档元信息，由指令填充)
    title: str = ""
    author: str = ""
    date: str = ""
    abstract: str = ""
    preamble: str = ""

    # Markdown options (Markdown 选项)
    heading_id_style: str = "attr"       # attr | html
    locale: str = "zh"                   # zh | en

    # Runtime flags (运行时标志，非序列化)
    strict: bool = False
    verbose: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> MdMidConfig:
        """Build config from dict with kebab/snake key normalization (从字典构建配置).

        Values of list or dict type are shallow-copied to prevent aliasing
        (list 和 dict 值浅拷贝以防止别名问题).

        Note:
            No type coercion is performed. Callers are responsible for ensuring
            value types match the declared field types (调用方需确保值类型与字段类型匹配).

        Args:
            data: Dictionary with kebab-case or snake_case keys (键可为 kebab 或 snake)

        Returns:
            MdMidConfig with matched fields set, defaults for missing (匹配字段已设置)
        """
        valid_fields = {f.name for f in fields(cls)}
        kwargs: dict[str, object] = {}
        for key, value in data.items():
            norm = key.replace("-", "_")
            if norm in valid_fields:
                # Shallow-copy mutable containers to prevent aliasing (浅拷贝可变容器防止别名)
                if isinstance(value, list):
                    value = list(value)
                elif isinstance(value, dict):
                    value = dict(value)
                kwargs[norm] = value
        return cls(**kwargs)  # type: ignore[arg-type]


def _normalize_keys(data: dict[str, object]) -> dict[str, object]:
    """Normalize kebab-case keys to snake_case (将 kebab-case 键归一化为 snake_case)."""
    return {k.replace("-", "_"): v for k, v in data.items()}


def resolve_config(
    cli_overrides: dict[str, object] | None = None,
    east_meta: dict[str, object] | None = None,
    config_dict: dict[str, object] | None = None,
    template_dict: dict[str, object] | None = None,
) -> MdMidConfig:
    """Resolve final config by merging dict layers in priority order (按优先级合并配置).

    Priority (high -> low): CLI > document directives > config file > template > defaults.
    Each layer is a plain dict with only the keys it explicitly sets.
    dict.update() naturally preserves lower-priority values for absent keys.

    Args:
        cli_overrides: CLI arg overrides, only non-None values (CLI 覆盖，仅非 None 值)
        east_meta: Document directive metadata (文档指令元数据)
        config_dict: Flattened config file dict (配置文件扁平字典)
        template_dict: Template file dict (模板文件字典)

    Returns:
        Fully resolved MdMidConfig (完全解析的配置)
    """
    # Start with defaults (从默认值开始)
    merged: dict[str, object] = _DEFAULTS.copy()
    # Deep-copy mutable defaults to avoid shared state (深拷贝可变默认值)
    merged["classoptions"] = list(cast(list[str], _DEFAULTS["classoptions"]))
    merged["packages"] = list(cast(list[str], _DEFAULTS["packages"]))
    merged["package_options"] = dict(cast(dict[str, str], _DEFAULTS["package_options"]))

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

    return MdMidConfig.from_dict(merged)


def load_config_file(path: Path) -> dict[str, object]:
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

    Returns:
        Flat dict with only explicitly-set keys (仅含显式设置键的扁平字典)
    """
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            data = _yaml.load(f)
    except Exception:
        _log.warning("Failed to parse config file: %s", path)
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

    return flat
