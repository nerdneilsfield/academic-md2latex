from pathlib import Path

from md_mid.nodes import (
    Blockquote,
    Citation,
    CodeInline,
    CrossRef,
    Document,
    Heading,
    List,
    ListItem,
    MathBlock,
    MathInline,
    Paragraph,
    RawBlock,
    Strong,
    Table,
    Text,
)
from md_mid.parser import parse

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_returns_document():
    doc = parse("# Hello")
    assert isinstance(doc, Document)


def test_heading():
    doc = parse("# Hello World")
    assert len(doc.children) == 1
    h = doc.children[0]
    assert isinstance(h, Heading)
    assert h.level == 1
    texts = [c for c in h.children if isinstance(c, Text)]
    assert any("Hello World" in t.content for t in texts)


def test_paragraph_with_inline():
    doc = parse("This is **bold** and *italic*.")
    para = doc.children[0]
    assert isinstance(para, Paragraph)
    # 段落应包含 Text, Strong, Text, Emphasis, Text
    types = [type(c).__name__ for c in para.children]
    assert "Strong" in types
    assert "Emphasis" in types


def test_math_inline():
    doc = parse("Hello $E=mc^2$ world")
    para = doc.children[0]
    math_nodes = [c for c in para.children if isinstance(c, MathInline)]
    assert len(math_nodes) == 1
    assert math_nodes[0].content == "E=mc^2"


def test_math_block():
    doc = parse("$$\n\\int_0^\\infty f(x) dx\n$$")
    math_nodes = [c for c in doc.children if isinstance(c, MathBlock)]
    assert len(math_nodes) == 1
    assert "\\int" in math_nodes[0].content


def test_unordered_list():
    doc = parse("- a\n- b\n")
    lst = doc.children[0]
    assert isinstance(lst, List)
    assert lst.ordered is False
    assert len(lst.children) == 2
    assert all(isinstance(c, ListItem) for c in lst.children)


def test_blockquote():
    doc = parse("> hello\n")
    bq = doc.children[0]
    assert isinstance(bq, Blockquote)


def test_code_inline():
    doc = parse("use `printf`")
    para = doc.children[0]
    codes = [c for c in para.children if isinstance(c, CodeInline)]
    assert len(codes) == 1
    assert codes[0].content == "printf"


def test_fixture_minimal(tmp_path):
    text = (FIXTURES / "minimal.mid.md").read_text()
    doc = parse(text)
    assert isinstance(doc, Document)
    # 应至少有: heading, paragraph, math_block, list, blockquote
    types = {type(c).__name__ for c in doc.children}
    assert "Heading" in types
    assert "Paragraph" in types
    assert "MathBlock" in types
    assert "List" in types
    assert "Blockquote" in types


# ── cite/ref tests (Task 10) ──────────────────────────────────


def test_cite_single():
    doc = parse("[Wang et al.](cite:wang2024)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].keys == ["wang2024"]
    assert cites[0].display_text == "Wang et al."


def test_cite_multiple_keys():
    doc = parse("[1-3](cite:wang2024,li2023,zhang2025)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].keys == ["wang2024", "li2023", "zhang2025"]


def test_cite_empty_display():
    doc = parse("[](cite:wang2024)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].display_text == ""


def test_cite_with_cmd():
    doc = parse("[Wang](cite:wang2024?cmd=citeauthor)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].cmd == "citeauthor"


def test_ref():
    doc = parse("[图1](ref:fig:result)")
    para = doc.children[0]
    refs = [c for c in para.children if isinstance(c, CrossRef)]
    assert len(refs) == 1
    assert refs[0].label == "fig:result"
    assert refs[0].display_text == "图1"


def test_regular_link_not_converted():
    doc = parse("[click](http://example.com)")
    para = doc.children[0]
    from md_mid.nodes import Link

    links = [c for c in para.children if isinstance(c, Link)]
    assert len(links) == 1


# ── Task 4: Citation validation ───────────────────────────────────────────────


def test_cite_empty_key_filtered() -> None:
    """空引用键被过滤（Empty citation keys are filtered out）."""
    doc = parse("[](cite:,wang2024,)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    # 空键应被过滤（Empty keys should be filtered）
    assert "" not in cites[0].keys
    assert "wang2024" in cites[0].keys


def test_cite_invalid_cmd_warning() -> None:
    """无效的引用命令触发 warning（Invalid cite cmd triggers warning）."""
    from md_mid.diagnostic import DiagCollector

    dc = DiagCollector("test.md")
    doc = parse("[text](cite:wang2024?cmd=badcmd)", diag=dc)
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    # 节点应仍然创建（Node should still be created for graceful degradation）
    assert cites[0].cmd == "badcmd"
    # 应触发 warning（Should trigger warning）
    assert any("Unknown citation command" in d.message for d in dc.warnings)


def test_cite_valid_cmd_no_warning() -> None:
    """合法的引用命令不触发 warning（Valid cite cmd does not trigger warning）."""
    from md_mid.diagnostic import DiagCollector

    dc = DiagCollector("test.md")
    parse("[text](cite:wang2024?cmd=citet)", diag=dc)
    assert not any("Unknown citation command" in d.message for d in dc.warnings)


# ── Task 1: Rich table cell tests ─────────────────────────────────────────────


def test_table_cell_bold_preserved() -> None:
    """表格粗体保留 (Bold in table cell preserved as Strong node)."""
    doc = parse("| **bold** | plain |\n|---|---|\n| a | b |\n")
    table = [c for c in doc.children if isinstance(c, Table)][0]
    # 第一个表头含 Strong 节点 (First header contains Strong)
    assert any(isinstance(n, Strong) for n in table.headers[0])


def test_table_cell_code_preserved() -> None:
    """表格行内代码保留 (Code in table cell preserved as CodeInline)."""
    doc = parse("| `code` | text |\n|---|---|\n| a | b |\n")
    table = [c for c in doc.children if isinstance(c, Table)][0]
    assert any(isinstance(n, CodeInline) for n in table.headers[0])


def test_table_cell_plain_text_as_text_node() -> None:
    """表格纯文本为 Text 节点 (Plain text cell is Text node)."""
    doc = parse("| hello |\n|---|\n| world |\n")
    table = [c for c in doc.children if isinstance(c, Table)][0]
    assert any(isinstance(n, Text) for n in table.headers[0])
    assert any(isinstance(n, Text) for n in table.rows[0][0])


def test_single_column_table() -> None:
    """单列表格 (Single column table parses correctly)."""
    doc = parse("| H |\n|---|\n| V |\n")
    table = [c for c in doc.children if isinstance(c, Table)][0]
    assert len(table.headers) == 1
    assert len(table.rows) == 1


def test_empty_cell_table() -> None:
    """空单元格表格 (Table with empty cells)."""
    doc = parse("| A | |\n|---|---|\n| | B |\n")
    table = [c for c in doc.children if isinstance(c, Table)][0]
    assert len(table.headers) == 2
    assert len(table.rows[0]) == 2


# ── Fix C: html_block and html_inline produce RawBlock with kind="html" ────────


def test_html_block_creates_rawblock_html_kind() -> None:
    """html_block 生成 kind=html 的 RawBlock (html_block creates RawBlock with kind=html)."""
    doc = parse("<div>hello</div>\n\n")
    raw_blocks = [c for c in doc.children if isinstance(c, RawBlock)]
    assert len(raw_blocks) >= 1
    assert all(rb.kind == "html" for rb in raw_blocks)


def test_html_inline_creates_rawblock_html_kind() -> None:
    """html_inline 生成 kind=html 的 RawBlock (html_inline creates RawBlock with kind=html)."""
    doc = parse("Text with <span>inline</span> html\n")
    # html_inline nodes appear inside paragraph children
    para = doc.children[0]
    raw_blocks = [c for c in para.children if isinstance(c, RawBlock)]
    assert len(raw_blocks) >= 1
    assert all(rb.kind == "html" for rb in raw_blocks)
