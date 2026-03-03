from pathlib import Path

from md_mid.comment import process_comments
from md_mid.diagnostic import DiagCollector
from md_mid.nodes import (
    Environment,
    Heading,
    Image,
    Paragraph,
    RawBlock,
    Strong,
)
from md_mid.parser import parse


def test_document_level_directives():
    doc = parse("<!-- title: My Paper -->\n<!-- packages: [amsmath] -->\n\n# Intro\n")
    east = process_comments(doc, "test.md")
    assert east.metadata.get("title") == "My Paper"
    assert east.metadata.get("packages") == ["amsmath"]


def test_label_attaches_to_heading():
    doc = parse("# Introduction\n<!-- label: sec:intro -->\n")
    east = process_comments(doc, "test.md")
    h = east.children[0]
    assert isinstance(h, Heading)
    assert h.metadata.get("label") == "sec:intro"


def test_caption_label_attach_to_image():
    text = "![fig](a.png)\n<!-- caption: My Fig -->\n<!-- label: fig:a -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    # Image 应被提升为 Figure（或 Image 节点获得 metadata）
    fig = east.children[0]
    # 穿透 paragraph → image
    if isinstance(fig, Paragraph) and len(fig.children) == 1:
        fig = fig.children[0]
    assert fig.metadata.get("caption") == "My Fig"
    assert fig.metadata.get("label") == "fig:a"


def test_begin_end_creates_environment():
    text = "<!-- begin: algorithm -->\nStep 1\n<!-- end: algorithm -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    envs = [c for c in east.children if isinstance(c, Environment)]
    assert len(envs) == 1
    assert envs[0].name == "algorithm"


def test_begin_end_raw_creates_raw_block():
    text = "<!-- begin: raw -->\n\\newcommand{\\myop}{\\operatorname}\n<!-- end: raw -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    raws = [c for c in east.children if isinstance(c, RawBlock)]
    assert len(raws) == 1
    assert "\\newcommand" in raws[0].content


def test_document_directive_after_content_ignored():
    text = "# Intro\n<!-- title: Late Title -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    # title 不应被收集（已进入正文）
    assert "title" not in east.metadata


def test_unmatched_begin_raises():
    """未匹配的 begin 指令触发错误（Unmatched begin directive triggers error）."""
    text = "<!-- begin: algorithm -->\nStep 1\n"
    doc = parse(text)
    dc = DiagCollector("test.md")
    process_comments(doc, "test.md", diag=dc)
    assert dc.has_errors


# ── Task 1: Stack-based begin/end matching ────────────────────────────────────


def test_nested_same_name_environments() -> None:
    """同名嵌套环境正确配对（Same-name nested environments correctly matched）."""
    text = (
        "<!-- begin: figure -->\n"
        "Outer\n"
        "<!-- begin: figure -->\n"
        "Inner\n"
        "<!-- end: figure -->\n"
        "<!-- end: figure -->\n"
    )
    doc = parse(text)
    east = process_comments(doc, "test.md")
    # 应该有 1 个顶层 figure 环境（Should have 1 top-level figure environment）
    envs = [c for c in east.children if isinstance(c, Environment)]
    assert len(envs) == 1
    outer = envs[0]
    assert outer.name == "figure"
    # 内部包含 1 个嵌套 figure（Inner should contain 1 nested figure）
    inner_envs = [c for c in outer.children if isinstance(c, Environment)]
    assert len(inner_envs) == 1
    assert inner_envs[0].name == "figure"


# ── Task 2: Environment-level directive attachment ────────────────────────────


def test_env_level_options_attached_to_environment() -> None:
    """环境级 options 指令附着到 Environment.metadata（Env-level options attached to env）."""
    text = (
        "<!-- begin: lstlisting -->\n"
        "<!-- options: language=Python -->\n"
        "print('hello')\n"
        "<!-- end: lstlisting -->\n"
    )
    doc = parse(text)
    east = process_comments(doc, "test.md")
    envs = [c for c in east.children if isinstance(c, Environment)]
    assert len(envs) == 1
    env = envs[0]
    assert env.metadata.get("options") == "language=Python"


def test_env_level_label_attached_to_environment() -> None:
    """环境级 label 指令附着到 Environment.metadata（Env-level label attached to env）."""
    text = (
        "<!-- begin: algorithm -->\n"
        "<!-- label: alg:sort -->\n"
        "Sort step\n"
        "<!-- end: algorithm -->\n"
    )
    doc = parse(text)
    east = process_comments(doc, "test.md")
    envs = [c for c in east.children if isinstance(c, Environment)]
    assert len(envs) == 1
    assert envs[0].metadata.get("label") == "alg:sort"


# ── Task 3: Diagnostic system ─────────────────────────────────────────────────


def test_orphan_end_directive_triggers_error() -> None:
    """孤立的 end 指令触发错误（Orphan end directive triggers error）."""
    text = "Some text\n<!-- end: figure -->\n"
    doc = parse(text)
    dc = DiagCollector("test.md")
    process_comments(doc, "test.md", diag=dc)
    assert dc.has_errors
    assert any("Orphan" in d.message for d in dc.errors)


def test_duplicate_document_directive_triggers_warning() -> None:
    """重复文档指令触发 warning（Duplicate doc directive triggers warning）."""
    text = "<!-- title: First -->\n<!-- title: Second -->\n\n# Body\n"
    doc = parse(text)
    dc = DiagCollector("test.md")
    east = process_comments(doc, "test.md", diag=dc)
    # 第一个 title 应被收集，第二个触发 warning（First title collected, second warns）
    assert east.metadata.get("title") == "First"
    assert any("Duplicate" in d.message for d in dc.warnings)


def test_post_content_document_directive_triggers_warning() -> None:
    """正文中的文档级指令触发 warning（Doc directive after content triggers warning）."""
    text = "# Intro\n<!-- title: Late -->\n"
    doc = parse(text)
    dc = DiagCollector("test.md")
    east = process_comments(doc, "test.md", diag=dc)
    assert "title" not in east.metadata
    assert any("after content" in d.message for d in dc.warnings)


def test_unknown_directive_key_triggers_info() -> None:
    """未知指令键触发 info 诊断（Unknown directive key triggers info diagnostic）."""
    text = "# Heading\n<!-- foobar: something -->\n"
    doc = parse(text)
    dc = DiagCollector("test.md")
    process_comments(doc, "test.md", diag=dc)
    assert any("Unknown directive" in d.message for d in dc.diagnostics)


# ── Task 5: Narrow paragraph penetration ─────────────────────────────────────


def test_non_image_single_child_paragraph_not_penetrated() -> None:
    """单子节点段落（非 Image）不穿透（Non-Image single-child para not penetrated）."""
    # Bold text inside paragraph should NOT be penetrated for directive attachment
    text = "**bold text**\n<!-- label: my-label -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    # The label should attach to the paragraph, NOT to the Strong node inside
    para = east.children[0]
    assert isinstance(para, Paragraph)
    assert para.metadata.get("label") == "my-label"
    # The Strong inside should NOT have the label
    if para.children:
        strong = para.children[0]
        if isinstance(strong, Strong):
            assert "label" not in strong.metadata


def test_image_in_paragraph_is_penetrated() -> None:
    """段落中的 Image 节点被穿透（Image inside paragraph is penetrated）."""
    text = "![alt](img.png)\n<!-- caption: My Fig -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    para = east.children[0]
    if isinstance(para, Paragraph) and len(para.children) == 1:
        img = para.children[0]
        assert isinstance(img, Image)
        assert img.metadata.get("caption") == "My Fig"


# ── Fix D: Misplaced directive removed from AST ────────────────────────────────


def test_misplaced_directive_removed_from_ast() -> None:
    """Fix D: 正文中错位的指令节点被从 AST 中删除 (Misplaced directive node removed from AST)."""
    # A paragraph followed by a misplaced document-level directive (段落后跟错位的文档指令)
    text = "Some content.\n\n<!-- title: Late -->\n"
    raw = parse(text)
    node_count_before = len(raw.children)
    dc = DiagCollector("test.md")
    east = process_comments(raw, "test.md", diag=dc)
    # The directive warning should fire (指令警告应触发)
    assert any("after content" in d.message for d in dc.warnings)
    # The misplaced node must be removed — AST shrinks by at least 1 (AST 节点数减少至少 1)
    assert len(east.children) < node_count_before


# ── Task 7: include-tex directive ─────────────────────────────────────────────


def test_include_tex_creates_raw_block(tmp_path: Path) -> None:
    """include-tex creates RawBlock from file (include-tex 创建 RawBlock)."""
    tex_file = tmp_path / "frag.tex"
    tex_file.write_text("\\begin{equation}\nx^2\n\\end{equation}\n")
    src_file = tmp_path / "t.mid.md"
    md_text = "# Intro\n\n<!-- include-tex: frag.tex -->\n\nMore text.\n"
    doc = parse(md_text)
    east = process_comments(doc, str(src_file), diag=DiagCollector(str(src_file)))
    raws = [c for c in east.children if isinstance(c, RawBlock)]
    assert len(raws) == 1
    assert "\\begin{equation}" in raws[0].content


def test_include_tex_relative_path(tmp_path: Path) -> None:
    """include-tex resolves relative path (include-tex 相对路径解析)."""
    sub = tmp_path / "tables"
    sub.mkdir()
    tex = sub / "complex.tex"
    tex.write_text("\\begin{tabular}{ll}\nA & B\n\\end{tabular}\n")
    src = tmp_path / "paper.mid.md"
    md = "# Tables\n\n<!-- include-tex: tables/complex.tex -->\n"
    doc = parse(md)
    east = process_comments(doc, str(src), diag=DiagCollector(str(src)))
    raws = [c for c in east.children if isinstance(c, RawBlock)]
    assert len(raws) == 1
    assert "tabular" in raws[0].content


def test_include_tex_file_not_found(tmp_path: Path) -> None:
    """Missing include file triggers error (文件不存在触发错误)."""
    src = tmp_path / "t.mid.md"
    md = "# Intro\n\n<!-- include-tex: nonexistent.tex -->\n"
    doc = parse(md)
    dc = DiagCollector(str(src))
    process_comments(doc, str(src), diag=dc)
    assert dc.has_errors
    assert any("not found" in d.message.lower() for d in dc.errors)


def test_include_tex_path_traversal_rejected(tmp_path: Path) -> None:
    """Path traversal in include-tex is rejected (路径遍历被拒绝)."""
    # Create a file outside source dir (在源目录外创建文件)
    outer = tmp_path / "outer"
    outer.mkdir()
    secret = outer / "secret.tex"
    secret.write_text("SECRET CONTENT")
    # Source file is in a subdirectory (源文件在子目录中)
    inner = tmp_path / "inner"
    inner.mkdir()
    src = inner / "paper.mid.md"
    md = "<!-- include-tex: ../outer/secret.tex -->\n"
    doc = parse(md)
    dc = DiagCollector(str(src))
    process_comments(doc, str(src), diag=dc)
    assert dc.has_errors
    assert any(
        "traversal" in d.message.lower() or "outside" in d.message.lower()
        for d in dc.errors
    )


def test_include_tex_preserves_content_verbatim(tmp_path: Path) -> None:
    """include-tex preserves content verbatim, no strip (内容原样保留)."""
    tex = tmp_path / "frag.tex"
    # Leading/trailing whitespace matters in TeX (TeX 中前后空白有意义)
    tex.write_text("\n  \\command\n\n")
    src = tmp_path / "t.mid.md"
    doc = parse("<!-- include-tex: frag.tex -->\n")
    east = process_comments(doc, str(src), diag=DiagCollector(str(src)))
    raws = [c for c in east.children if isinstance(c, RawBlock)]
    assert len(raws) == 1
    assert raws[0].content == "\n  \\command\n\n"


def test_include_tex_directory_path(tmp_path: Path) -> None:
    """include-tex 指向目录时报错而不崩溃.

    include-tex on directory path reports error, no crash.
    """
    (tmp_path / "subdir").mkdir()
    text = "<!-- include-tex: subdir -->\n"
    raw = parse(text)
    dc = DiagCollector(str(tmp_path / "t.mid.md"))
    # Must not raise; must produce a diag error (不抛异常，报告 diag 错误)
    process_comments(raw, str(tmp_path / "t.mid.md"), diag=dc)
    assert any("include-tex" in d.message for d in dc.errors)


def test_include_tex_non_utf8_file(tmp_path: Path) -> None:
    """include-tex 指向非 UTF-8 文件时报错而不崩溃.

    include-tex on binary file reports error, no crash.
    """
    binary = tmp_path / "bad.tex"
    binary.write_bytes(b"\xff\xfe\x00bad")
    text = "<!-- include-tex: bad.tex -->\n"
    raw = parse(text)
    dc = DiagCollector(str(tmp_path / "t.mid.md"))
    process_comments(raw, str(tmp_path / "t.mid.md"), diag=dc)
    assert any("include-tex" in d.message for d in dc.errors)
