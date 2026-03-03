"""Unified configuration for md-mid.

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
from typing import cast

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

        Unknown keys are ignored (未知键被忽略).

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
