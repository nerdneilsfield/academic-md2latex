from md_mid.parser import parse
from md_mid.comment import process_comments
from md_mid.nodes import (
    Document, Heading, Paragraph, Figure, Environment, RawBlock, Image,
)


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
    text = '<!-- begin: raw -->\n\\newcommand{\\myop}{\\operatorname}\n<!-- end: raw -->\n'
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
    text = "<!-- begin: algorithm -->\nStep 1\n"
    doc = parse(text)
    from md_mid.diagnostic import DiagCollector
    dc = DiagCollector("test.md")
    east = process_comments(doc, "test.md", diag=dc)
    assert dc.has_errors
