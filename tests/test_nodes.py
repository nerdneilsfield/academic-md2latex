from md_mid.nodes import (
    Citation,
    CrossRef,
    Document,
    Environment,
    Figure,
    Heading,
    MathBlock,
    Strong,
    Table,
    Text,
)


def test_text_node():
    t = Text(content="hello")
    assert t.type == "text"
    assert t.content == "hello"
    assert t.children == []
    assert t.metadata == {}


def test_heading_with_metadata():
    h = Heading(level=2, children=[Text(content="Related Work")])
    h.metadata["label"] = "sec:related"
    assert h.type == "heading"
    assert h.level == 2
    assert len(h.children) == 1
    assert h.metadata["label"] == "sec:related"


def test_document_metadata():
    doc = Document(children=[])
    doc.metadata["title"] = "My Paper"
    doc.metadata["documentclass"] = "article"
    assert doc.type == "document"


def test_math_block():
    m = MathBlock(content="E = mc^2")
    assert m.type == "math_block"
    assert m.content == "E = mc^2"


def test_environment():
    env = Environment(
        name="algorithm",
        children=[Text(content="step 1")],
    )
    env.metadata["label"] = "alg:main"
    assert env.type == "environment"
    assert env.name == "algorithm"


def test_citation():
    c = Citation(keys=["wang2024", "li2023"], display_text="Wang et al.", cmd="cite")
    assert c.type == "citation"
    assert c.keys == ["wang2024", "li2023"]


def test_cross_ref():
    r = CrossRef(label="fig:result", display_text="图1")
    assert r.type == "cross_ref"
    assert r.label == "fig:result"


def test_figure():
    f = Figure(src="figs/a.png", alt="图A")
    f.metadata["caption"] = "示意图"
    f.metadata["label"] = "fig:a"
    assert f.type == "figure"
    assert f.src == "figs/a.png"


def test_table_node_with_inline_nodes() -> None:
    """表格节点含行内节点 (Table node with inline nodes in cells)."""
    t = Table(
        headers=[[Text(content="A")], [Strong(children=[Text(content="B")])]],
        alignments=["left", "left"],
        rows=[[[Text(content="1")], [Text(content="2")]]],
    )
    assert t.type == "table"
    assert len(t.headers) == 2
    assert len(t.rows) == 1


def test_table_to_dict_serializes_cell_nodes() -> None:
    """表格 to_dict 序列化单元格节点 (Table to_dict serializes cell nodes)."""
    t = Table(
        headers=[[Text(content="H")]],
        alignments=["left"],
        rows=[[[Text(content="V")]]],
    )
    d = t.to_dict()
    assert d["headers"][0][0]["type"] == "text"
    assert d["headers"][0][0]["content"] == "H"
    assert d["rows"][0][0][0]["type"] == "text"
