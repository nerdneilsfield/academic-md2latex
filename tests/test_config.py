from md_mid.config import MdMidConfig, resolve_config


def test_config_defaults() -> None:
    """Default config values match PRD §10.2 (默认配置值)."""
    cfg = MdMidConfig()
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
    cfg = MdMidConfig.from_dict(d)
    assert cfg.mode == "fragment"
    assert cfg.code_style == "minted"
    assert cfg.ref_tilde is False


def test_config_from_dict_ignores_unknown() -> None:
    """Unknown keys are ignored (未知键被忽略)."""
    d = {"mode": "body", "unknown-key": "value"}
    cfg = MdMidConfig.from_dict(d)
    assert cfg.mode == "body"


def test_resolve_config_priority_chain() -> None:
    """Config priority chain: CLI > doc > config > template > defaults (优先级链)."""
    cfg = resolve_config(
        cli_overrides={"mode": "body"},
        east_meta={"documentclass": "report"},
        config_dict={"code-style": "minted"},
        template_dict={"bibstyle": "IEEEtran"},
    )
    assert cfg.mode == "body"              # from CLI (来自 CLI)
    assert cfg.documentclass == "report"  # from doc directives (来自文档指令)
    assert cfg.code_style == "minted"     # from config file (来自配置文件)
    assert cfg.bibstyle == "IEEEtran"     # from template (来自模板)
    assert cfg.target == "latex"          # from defaults (来自默认值)


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
