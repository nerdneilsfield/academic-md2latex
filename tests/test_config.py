from pathlib import Path

import pytest

from wenqiao.config import WenqiaoConfig, load_config_file, load_template, resolve_config


def test_config_defaults() -> None:
    """Default config values match PRD §10.2 (默认配置值)."""
    cfg = WenqiaoConfig()
    assert cfg.target == "latex"
    assert cfg.mode == "full"
    assert cfg.documentclass == "article"
    assert cfg.classoptions == ["12pt", "a4paper"]
    assert "amsmath" in cfg.packages
    assert cfg.bibstyle == "plain"
    assert cfg.code_style == "lstlisting"
    assert cfg.thematic_break == "newpage"
    assert cfg.ref_tilde is True
    assert cfg.heading_id_style == "attr"
    assert cfg.locale == "zh"
    assert cfg.bibliography_mode == "auto"


def test_config_from_dict() -> None:
    """Build config from dict with kebab-to-snake normalization (从字典构建配置)."""
    d = {"mode": "fragment", "code-style": "minted", "ref-tilde": False}
    cfg = WenqiaoConfig.from_dict(d)
    assert cfg.mode == "fragment"
    assert cfg.code_style == "minted"
    assert cfg.ref_tilde is False


def test_config_from_dict_ignores_unknown() -> None:
    """Unknown keys are ignored (未知键被忽略)."""
    d = {"mode": "body", "unknown-key": "value"}
    cfg = WenqiaoConfig.from_dict(d)
    assert cfg.mode == "body"


def test_resolve_config_priority_chain() -> None:
    """Config priority chain: CLI > doc > config > template > defaults (优先级链)."""
    cfg = resolve_config(
        cli_overrides={"mode": "body"},
        east_meta={"documentclass": "report"},
        config_dict={"code-style": "minted"},
        template_dict={"bibstyle": "IEEEtran"},
    )
    assert cfg.mode == "body"  # from CLI (来自 CLI)
    assert cfg.documentclass == "report"  # from doc directives (来自文档指令)
    assert cfg.code_style == "minted"  # from config file (来自配置文件)
    assert cfg.bibstyle == "IEEEtran"  # from template (来自模板)
    assert cfg.target == "latex"  # from defaults (来自默认值)


def test_resolve_config_higher_priority_wins() -> None:
    """Higher priority overrides lower (高优先级覆盖低优先级)."""
    cfg = resolve_config(
        cli_overrides={"mode": "fragment"},
        east_meta={"mode": "body"},
    )
    assert cfg.mode == "fragment"  # CLI wins over doc directive (CLI 胜过文档指令)


def test_resolve_config_explicit_default_preserved() -> None:
    """Explicitly set default value wins over lower-priority non-default (显式默认值保留)."""
    # CLI explicitly sets mode="full" (which is also the default value)
    # Template sets mode="body" (a non-default value at lower priority)
    # CLI must win even though its value equals the default
    cfg = resolve_config(
        cli_overrides={"mode": "full"},
        template_dict={"mode": "body"},
    )
    assert cfg.mode == "full"  # CLI wins, even though "full" is default value


def test_resolve_config_empty_calls() -> None:
    """resolve_config with no args returns defaults (无参数返回默认值)."""
    cfg = resolve_config()
    assert cfg.mode == "full"
    assert cfg.locale == "zh"


def test_resolve_config_mutable_defaults_not_shared() -> None:
    """Mutable defaults are not shared across calls (可变默认值不跨调用共享)."""
    cfg1 = resolve_config()
    cfg2 = resolve_config()
    cfg1.classoptions.append("draft")
    assert "draft" not in cfg2.classoptions


def test_config_from_dict_list_value_is_copied() -> None:
    """from_dict shallow-copies list values to prevent aliasing (from_dict 浅拷贝列表防别名)."""
    source = ["11pt", "a4paper"]
    cfg = WenqiaoConfig.from_dict({"classoptions": source})
    source.append("draft")
    assert "draft" not in cfg.classoptions


def test_load_config_file(tmp_path: Path) -> None:
    """Load external config file (加载外部配置文件)."""
    cfg_file = tmp_path / "wenqiao.yaml"
    cfg_file.write_text(
        "latex:\n"
        "  mode: body\n"
        "  code-style: minted\n"
        "  bibstyle: IEEEtran\n"
        "markdown:\n"
        "  locale: en\n"
    )
    d = load_config_file(cfg_file)
    assert d["mode"] == "body"
    assert d["code-style"] == "minted"
    assert d["bibstyle"] == "IEEEtran"
    assert d["locale"] == "en"


def test_load_config_file_not_found() -> None:
    """Missing config file returns empty dict (不存在的配置文件返回空字典)."""
    d = load_config_file(Path("/nonexistent/wenqiao.yaml"))
    assert d == {}


def test_load_config_file_flat_keys(tmp_path: Path) -> None:
    """Flat key config (扁平键配置)."""
    cfg_file = tmp_path / "wenqiao.yaml"
    cfg_file.write_text("default-target: markdown\n")
    d = load_config_file(cfg_file)
    assert d["target"] == "markdown"


def test_load_config_file_invalid_yaml(tmp_path: Path) -> None:
    """Invalid YAML returns empty dict with no crash (无效 YAML 不崩溃)."""
    cfg_file = tmp_path / "wenqiao.yaml"
    cfg_file.write_text(": invalid: yaml: {{{\n")
    d = load_config_file(cfg_file)
    assert d == {}


def test_load_template(tmp_path: Path) -> None:
    """Load LaTeX template (加载 LaTeX 模板)."""
    tpl = tmp_path / "ieee.yaml"
    tpl.write_text(
        "documentclass: IEEEtran\n"
        "classoptions: [conference]\n"
        "packages:\n"
        "  - amsmath\n"
        "  - graphicx\n"
        "  - cite\n"
        "bibstyle: IEEEtran\n"
        "extra-preamble: override\n"
    )
    d = load_template(tpl)
    assert d["documentclass"] == "IEEEtran"
    assert d["classoptions"] == ["conference"]
    assert "cite" in d["packages"]
    assert d["bibstyle"] == "IEEEtran"
    assert d.get("preamble") == "override"
    assert "extra-preamble" not in d


def test_load_template_not_found() -> None:
    """Missing template returns empty dict (不存在的模板返回空字典)."""
    d = load_template(Path("/nonexistent/template.yaml"))
    assert d == {}


def test_load_template_invalid_yaml(tmp_path: Path) -> None:
    """Invalid YAML in template returns empty dict (模板中无效 YAML 不崩溃)."""
    tpl = tmp_path / "bad.yaml"
    # Use a flow mapping that is never closed — ruamel.yaml raises ParserError
    # (使用未闭合的流式映射使解析器抛出 ParserError)
    tpl.write_text("{unclosed\n")
    d = load_template(tpl)
    assert d == {}


def test_load_template_extra_preamble_mapped(tmp_path: Path) -> None:
    """extra-preamble key is mapped to preamble (extra-preamble 映射为 preamble)."""
    tpl = tmp_path / "t.yaml"
    tpl.write_text("extra-preamble: '\\newcommand{\\x}{1}'\n")
    d = load_template(tpl)
    assert "preamble" in d
    assert "extra-preamble" not in d


# ── P1-2: Config type validation ─────────────────────────────────────────────


def test_load_template_missing_file() -> None:
    """Missing template returns empty dict (不存在的模板返回空字典)."""
    from wenqiao.diagnostic import DiagCollector

    diag = DiagCollector("<test>")
    d = load_template(Path("/nonexistent/template.yaml"), diag=diag)
    assert d == {}


def test_load_template_invalid_yaml_warns(tmp_path: Path) -> None:
    """Invalid YAML template produces diag warning (无效 YAML 模板产生诊断警告)."""
    from wenqiao.diagnostic import DiagCollector, DiagLevel

    tpl = tmp_path / "bad.yaml"
    tpl.write_text("{unclosed\n")
    diag = DiagCollector("<test>")
    d = load_template(tpl, diag=diag)
    assert d == {}
    warns = [d for d in diag.diagnostics if d.level == DiagLevel.WARNING]
    assert any("template" in d.message.lower() for d in warns)


def test_from_dict_unknown_key_info() -> None:
    """Unknown keys produce info diagnostic (未知键产生 info 诊断)."""
    from wenqiao.diagnostic import DiagCollector, DiagLevel

    diag = DiagCollector("<test>")
    cfg = WenqiaoConfig.from_dict({"mode": "body", "unknown-key": "value"}, diag=diag)
    assert cfg.mode == "body"
    assert any(d.level == DiagLevel.INFO and "unknown-key" in d.message for d in diag.diagnostics)


def test_config_type_error_classoptions_int() -> None:
    """classoptions as int raises TypeError (classoptions 为 int 时抛出 TypeError)."""
    with pytest.raises(TypeError, match="classoptions"):
        WenqiaoConfig.from_dict({"classoptions": 12})


def test_config_type_error_packages_str() -> None:
    """packages as str raises TypeError (packages 为 str 时抛出 TypeError)."""
    with pytest.raises(TypeError, match="packages"):
        WenqiaoConfig.from_dict({"packages": "numpy"})


def test_config_type_error_classoptions_int_element() -> None:
    """classoptions with int element raises TypeError (classoptions 含 int 元素时抛出 TypeError)."""
    with pytest.raises(TypeError, match=r"classoptions\[0\]"):
        WenqiaoConfig.from_dict({"classoptions": [12]})


# --- Preset tests (预设测试) ---


class TestPresets:
    """Tests for built-in presets (内置预设测试)."""

    def test_zh_preset_sets_ctexart(self) -> None:
        """zh preset should set documentclass to ctexart (zh 预设应设置 documentclass)."""
        cfg = resolve_config(preset_name="zh")
        assert cfg.documentclass == "ctexart"
        assert cfg.locale == "zh"
        assert "hyperref" in cfg.packages

    def test_en_preset_sets_locale_en(self) -> None:
        """en preset locale should be en (en 预设的 locale 应为 en)."""
        cfg = resolve_config(preset_name="en")
        assert cfg.locale == "en"
        assert cfg.documentclass == "article"

    def test_directive_overrides_preset(self) -> None:
        """Document directive overrides preset (文档指令应覆盖预设)."""
        cfg = resolve_config(
            preset_name="zh",
            east_meta={"documentclass": "report"},
        )
        assert cfg.documentclass == "report"
        assert cfg.locale == "zh"  # not overridden, preset value preserved (未覆盖，保留预设值)

    def test_template_overrides_preset(self) -> None:
        """Template overrides preset (模板应覆盖预设)."""
        cfg = resolve_config(
            preset_name="zh",
            template_dict={"locale": "en"},
        )
        assert cfg.locale == "en"  # template wins over preset (模板优先于预设)

    def test_unknown_preset_raises(self) -> None:
        """Unknown preset name should raise ValueError (未知预设应抛出 ValueError)."""
        with pytest.raises(ValueError, match="unknown preset"):
            resolve_config(preset_name="nonexistent")

    def test_none_preset_is_noop(self) -> None:
        """No preset (None) should behave like current defaults (None 预设不影响默认行为)."""
        cfg_no_preset = resolve_config()
        cfg_none = resolve_config(preset_name=None)
        assert cfg_no_preset.documentclass == cfg_none.documentclass
        assert cfg_no_preset.locale == cfg_none.locale
