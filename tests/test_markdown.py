from md_mid.markdown import MarkdownRenderer
from md_mid.nodes import (
    Blockquote,
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    Emphasis,
    Figure,
    HardBreak,
    Heading,
    Image,
    List,
    ListItem,
    MathBlock,
    MathInline,
    Node,
    Paragraph,
    RawBlock,
    SoftBreak,
    Strong,
    Table,
    Text,
    ThematicBreak,
)


def render(node, **kwargs):
    return MarkdownRenderer(**kwargs).render(node)


def doc(*children):
    return Document(children=list(children))


class TestInline:
    def test_text(self):
        assert render(doc(Paragraph(children=[Text(content="hello")]))) == "hello\n\n"

    def test_strong(self):
        p = Paragraph(children=[Strong(children=[Text(content="bold")])])
        assert "**bold**" in render(doc(p))

    def test_emphasis(self):
        p = Paragraph(children=[Emphasis(children=[Text(content="italic")])])
        assert "*italic*" in render(doc(p))

    def test_code_inline(self):
        p = Paragraph(children=[CodeInline(content="x = 1")])
        assert "`x = 1`" in render(doc(p))

    def test_math_inline(self):
        p = Paragraph(children=[MathInline(content=r"E=mc^2")])
        assert "$E=mc^2$" in render(doc(p))

    def test_softbreak(self):
        p = Paragraph(children=[Text(content="a"), SoftBreak(), Text(content="b")])
        result = render(doc(p))
        assert "a\nb" in result

    def test_hardbreak(self):
        p = Paragraph(children=[Text(content="a"), HardBreak(), Text(content="b")])
        result = render(doc(p))
        assert "a  \nb" in result


class TestBlock:
    def test_heading_level1(self):
        h = Heading(level=1, children=[Text(content="Title")])
        assert "# Title" in render(doc(h))

    def test_heading_level2(self):
        h = Heading(level=2, children=[Text(content="Sec")])
        assert "## Sec" in render(doc(h))

    def test_paragraph(self):
        p = Paragraph(children=[Text(content="Hello.")])
        result = render(doc(p))
        assert "Hello." in result
        assert result.endswith("\n\n") or result.endswith("\n")

    def test_code_block(self):
        c = CodeBlock(content="x = 1", language="python")
        result = render(doc(c))
        assert "```python" in result
        assert "x = 1" in result
        assert "```" in result

    def test_math_block(self):
        m = MathBlock(content=r"x^2 + y^2 = z^2")
        result = render(doc(m))
        assert "$$" in result
        assert r"x^2 + y^2 = z^2" in result

    def test_unordered_list(self):
        lst = List(
            ordered=False,
            children=[
                ListItem(children=[Paragraph(children=[Text(content="a")])]),
                ListItem(children=[Paragraph(children=[Text(content="b")])]),
            ],
        )
        result = render(doc(lst))
        assert "- a" in result
        assert "- b" in result

    def test_ordered_list(self):
        lst = List(
            ordered=True,
            children=[
                ListItem(children=[Paragraph(children=[Text(content="x")])]),
            ],
        )
        result = render(doc(lst))
        assert "1. x" in result

    def test_blockquote(self):
        bq = Blockquote(children=[Paragraph(children=[Text(content="quote")])])
        result = render(doc(bq))
        assert "> quote" in result

    def test_thematic_break(self):
        result = render(doc(ThematicBreak()))
        assert "---" in result


# ── Task 2: CrossRef + Heading Labels (交叉引用和标题标签) ────────


class TestCrossRef:
    """Cross-reference rendering tests (交叉引用渲染测试)."""

    def test_cross_ref_html_anchor(self) -> None:
        """CrossRef renders as HTML anchor link (交叉引用渲染为 HTML 锚点链接)."""
        r = CrossRef(label="fig:result", display_text="图1")
        p = Paragraph(children=[r])
        result = render(doc(p))
        assert '<a href="#fig:result">图1</a>' in result

    def test_cross_ref_in_sentence(self) -> None:
        """CrossRef inline with text (交叉引用在句子中)."""
        p = Paragraph(children=[
            Text(content="如"),
            CrossRef(label="fig:a", display_text="图1"),
            Text(content="所示"),
        ])
        result = render(doc(p))
        assert '如<a href="#fig:a">图1</a>所示' in result


class TestHeadingLabel:
    """Heading label/anchor rendering tests (标题标签渲染测试)."""

    def test_heading_with_label_attr_style(self) -> None:
        """Heading label uses attr style by default (默认使用 attr 风格)."""
        h = Heading(level=2, children=[Text(content="方法")])
        h.metadata["label"] = "sec:method"
        result = render(doc(h))
        assert "## 方法 {#sec:method}" in result

    def test_heading_with_label_html_style(self) -> None:
        """Heading label uses HTML style when configured (配置为 HTML 风格)."""
        h = Heading(level=2, children=[Text(content="方法")])
        h.metadata["label"] = "sec:method"
        result = render(doc(h), heading_id_style="html")
        assert '<h2 id="sec:method">方法</h2>' in result

    def test_heading_without_label(self) -> None:
        """Heading without label has no anchor markup (无标签标题无锚点)."""
        h = Heading(level=1, children=[Text(content="Title")])
        result = render(doc(h))
        assert "# Title" in result
        assert "{#" not in result
        assert "<h1" not in result

    def test_math_block_with_label_gets_anchor(self) -> None:
        """MathBlock with label gets an anchor element (带标签的公式块有锚点)."""
        m = MathBlock(content=r"E=mc^2")
        m.metadata["label"] = "eq:einstein"
        result = render(doc(m))
        assert '<a id="eq:einstein"></a>' in result
        assert "$$" in result


# ── Task 3: Citation (引用) ──────────────────────────────────────


class TestCitation:
    """Citation and footnote rendering tests (引用和脚注渲染测试)."""

    def test_single_cite_with_display(self) -> None:
        """Single cite key with display text (单引用键带显示文本)."""
        c = Citation(keys=["wang2024"], display_text="Wang et al.")
        p = Paragraph(children=[c])
        result = render(doc(p))
        assert "Wang et al.[^wang2024]" in result

    def test_single_cite_empty_display(self) -> None:
        """Single cite key with empty display text (单引用键无显示文本)."""
        c = Citation(keys=["wang2024"], display_text="")
        p = Paragraph(children=[c])
        result = render(doc(p))
        assert "[^wang2024]" in result

    def test_multiple_keys(self) -> None:
        """Multiple cite keys joined together (多引用键合并)."""
        c = Citation(keys=["a", "b", "c"], display_text="1-3")
        p = Paragraph(children=[c])
        result = render(doc(p))
        assert "1-3[^a][^b][^c]" in result

    def test_footnote_definitions_appear_at_end(self) -> None:
        """Footnote definitions appear after body (脚注定义出现在正文之后)."""
        c = Citation(keys=["wang2024"], display_text="Wang")
        p = Paragraph(children=[c])
        result = render(doc(p))
        body_pos = result.find("Wang[^wang2024]")
        def_pos = result.find("[^wang2024]:", body_pos)
        assert def_pos > body_pos

    def test_footnote_definition_content_key_only(self) -> None:
        """Footnote definition defaults to key as content (脚注定义默认为键名)."""
        c = Citation(keys=["li2023"], display_text="Li")
        p = Paragraph(children=[c])
        result = render(doc(p))
        assert "[^li2023]: li2023" in result

    def test_footnote_definition_from_bib(self) -> None:
        """Footnote definition uses bib entry when available (有 bib 时使用条目内容)."""
        c = Citation(keys=["wang2024"], display_text="Wang")
        p = Paragraph(children=[c])
        bib = {"wang2024": "Wang et al. Point Cloud Registration. CVPR, 2024."}
        result = render(doc(p), bib=bib)
        assert "[^wang2024]: Wang et al. Point Cloud Registration. CVPR, 2024." in result

    def test_cite_keys_ordered_in_footnotes(self) -> None:
        """Footnote definitions follow citation order (脚注定义按引用顺序)."""
        p = Paragraph(children=[
            Citation(keys=["a"], display_text="A"),
            Text(content=" and "),
            Citation(keys=["b"], display_text="B"),
        ])
        result = render(doc(p))
        pos_a = result.find("[^a]: a")
        pos_b = result.find("[^b]: b")
        assert pos_a < pos_b


# ── Task 4: Figure (图) ─────────────────────────────────────────


class TestFigure:
    """Figure rendering tests (图渲染测试)."""

    def test_figure_node_renders_html_block(self) -> None:
        """Figure node renders as HTML figure block (Figure 节点渲染为 HTML 块)."""
        f = Figure(src="fig.png", alt="alt text")
        f.metadata["caption"] = "My Fig"
        f.metadata["label"] = "fig:a"
        result = render(doc(f))
        assert '<figure id="fig:a">' in result
        assert '<img src="fig.png" alt="alt text"' in result
        assert "<figcaption><strong>图 1</strong>: My Fig</figcaption>" in result
        assert "</figure>" in result

    def test_image_in_paragraph_promoted_to_figure(self) -> None:
        """Image with caption in Paragraph promoted to figure (段落中有标题的图片提升为 figure)."""
        img = Image(src="img.png", alt="photo")
        img.metadata["caption"] = "Photo"
        img.metadata["label"] = "fig:photo"
        p = Paragraph(children=[img])
        result = render(doc(p))
        assert '<figure id="fig:photo">' in result
        assert "Photo" in result

    def test_plain_image_not_promoted(self) -> None:
        """Plain image without caption stays as markdown (无标题的普通图片保持 markdown 格式)."""
        img = Image(src="img.png", alt="plain")
        p = Paragraph(children=[img])
        result = render(doc(p))
        assert "![plain](img.png)" in result
        assert "<figure" not in result

    def test_figure_auto_numbering(self) -> None:
        """Figures are auto-numbered sequentially (图自动编号)."""
        f1 = Figure(src="a.png", alt="")
        f1.metadata["caption"] = "First"
        f1.metadata["label"] = "fig:first"
        f2 = Figure(src="b.png", alt="")
        f2.metadata["caption"] = "Second"
        f2.metadata["label"] = "fig:second"
        result = render(doc(f1, f2))
        pos1 = result.find("图 1")
        pos2 = result.find("图 2")
        assert pos1 < pos2

    def test_figure_without_label_no_id(self) -> None:
        """Figure without label has no id attribute (无标签的图没有 id 属性)."""
        f = Figure(src="a.png", alt="")
        f.metadata["caption"] = "No label"
        result = render(doc(f))
        assert "id=" not in result
        assert "<figure>" in result

    def test_figure_with_ai_info(self) -> None:
        """Figure with AI metadata renders details block (带 AI 元数据的图渲染折叠块)."""
        f = Figure(src="ai.png", alt="AI fig")
        f.metadata["caption"] = "AI Generated"
        f.metadata["label"] = "fig:ai"
        f.metadata["ai"] = {
            "model": "dall-e-3",
            "prompt": "Academic diagram",
            "negative_prompt": "photorealistic",
        }
        result = render(doc(f))
        assert "<details>" in result
        assert "AI Generation Info" in result
        assert "dall-e-3" in result


# ── Task 5: Table (表) ──────────────────────────────────────────


class TestTable:
    """Table rendering tests (表格渲染测试)."""

    def test_basic_table(self) -> None:
        """Basic table renders as HTML table (基本表格渲染为 HTML 表格)."""
        t = Table(
            headers=["Method", "RMSE"],
            alignments=["left", "left"],
            rows=[["RANSAC", "2.3"], ["Ours", "1.9"]],
        )
        t.metadata["caption"] = "Results"
        t.metadata["label"] = "tab:results"
        result = render(doc(t))
        assert '<figure id="tab:results">' in result
        assert "<table>" in result
        assert "<th>Method</th>" in result
        assert "<td>RANSAC</td>" in result
        assert "<figcaption><strong>表 1</strong>: Results</figcaption>" in result

    def test_table_auto_numbering(self) -> None:
        """Tables are auto-numbered sequentially (表自动编号)."""
        t1 = Table(headers=["A"], alignments=["left"], rows=[["1"]])
        t1.metadata["caption"] = "First"
        t1.metadata["label"] = "tab:first"
        t2 = Table(headers=["B"], alignments=["left"], rows=[["2"]])
        t2.metadata["caption"] = "Second"
        t2.metadata["label"] = "tab:second"
        result = render(doc(t1, t2))
        assert "表 1" in result
        assert "表 2" in result

    def test_table_and_figure_numbered_separately(self) -> None:
        """Tables and figures have separate counters (表和图分开编号)."""
        f = Figure(src="a.png", alt="")
        f.metadata["caption"] = "A figure"
        t = Table(headers=["X"], alignments=["left"], rows=[["y"]])
        t.metadata["caption"] = "A table"
        result = render(doc(f, t))
        assert "图 1" in result
        assert "表 1" in result


# ── Task 6: RawBlock + FrontMatter (原始块和前言) ────────────────


class TestRawBlock:
    """Raw LaTeX block rendering tests (原始 LaTeX 块渲染测试)."""

    def test_raw_block_renders_details(self) -> None:
        """RawBlock renders as details/summary fold (原始块渲染为折叠块)."""
        rb = RawBlock(content=r"\newcommand{\myop}{\operatorname}")
        result = render(doc(rb))
        assert "<details>" in result
        assert "Raw LaTeX" in result
        assert "```latex" in result
        assert r"\newcommand{\myop}{\operatorname}" in result
        assert "</details>" in result

    def test_raw_block_content_preserved(self) -> None:
        """RawBlock preserves multiline content verbatim (原始块保留多行内容)."""
        content = r"\begin{algorithm}" + "\nStep 1\n" + r"\end{algorithm}"
        rb = RawBlock(content=content)
        result = render(doc(rb))
        assert content in result


class TestFrontMatter:
    """YAML front matter rendering tests (YAML 前言渲染测试)."""

    def test_front_matter_with_title_author(self) -> None:
        """Front matter includes title and author (前言包含标题和作者)."""
        d = doc()
        d.metadata["title"] = "My Paper"
        d.metadata["author"] = "Alice"
        result = render(d)
        assert "---" in result
        assert "title: My Paper" in result
        assert "author: Alice" in result

    def test_front_matter_appears_first(self) -> None:
        """Front matter appears before body content (前言出现在正文之前)."""
        d = Document(children=[Paragraph(children=[Text(content="Body.")])])
        d.metadata["title"] = "Title"
        result = render(d)
        fm_pos = result.find("title: Title")
        body_pos = result.find("Body.")
        assert fm_pos < body_pos

    def test_no_front_matter_when_no_metadata(self) -> None:
        """No front matter when no metadata present (无元数据时无前言)."""
        d = Document(children=[Paragraph(children=[Text(content="Body.")])])
        result = render(d)
        assert "---" not in result

    def test_multiline_abstract_block_scalar(self) -> None:
        """多行摘要使用块标量 (Multi-line abstract uses YAML block scalar)."""
        d = doc()
        d.metadata["abstract"] = "Line 1\nLine 2"
        result = render(d)
        assert "abstract: |" in result
        assert "  Line 1" in result

    def test_multiline_front_matter_valid_yaml(self) -> None:
        """多行前言可解析为合法 YAML (Multi-line FM parseable as valid YAML)."""
        from ruamel.yaml import YAML
        d = doc()
        d.metadata["title"] = "Paper"
        d.metadata["abstract"] = "L1\nL2"
        result = render(d)
        yaml_str = result.split("---")[1]
        parsed = YAML(typ="safe").load(yaml_str)
        assert parsed["title"] == "Paper"
        assert "L1" in parsed["abstract"]

    def test_single_line_not_affected(self) -> None:
        """单行值不受影响 (Single-line values unchanged)."""
        d = doc()
        d.metadata["title"] = "Simple"
        result = render(d)
        assert "title: Simple" in result
        assert "abstract: |" not in result


# ── Task 2 (H3): HTML Escaping (HTML 转义) ───────────────────────


class TestHtmlEscaping:
    """HTML escaping tests (HTML 转义测试)."""

    def test_table_cell_ampersand_escaped(self) -> None:
        """表格 & 被转义 (Table cell & is escaped)."""
        t = Table(headers=["H"], alignments=["left"], rows=[["x & y"]])
        t.metadata["caption"] = "T"
        result = render(doc(t))
        assert "x &amp; y" in result

    def test_figure_alt_quotes_escaped(self) -> None:
        """图片 alt 引号被转义 (Image alt quotes escaped in attribute)."""
        f = Figure(src="t.png", alt='alt "q"')
        f.metadata["caption"] = "C"
        result = render(doc(f))
        assert 'alt="alt &quot;q&quot;"' in result

    def test_figure_caption_html_escaped(self) -> None:
        """图标题 HTML 被转义 (Figure caption HTML tags escaped)."""
        f = Figure(src="a.png", alt="x")
        f.metadata["caption"] = "<script>alert(1)</script>"
        result = render(doc(f))
        assert "&lt;script&gt;" in result

    def test_cross_ref_display_text_escaped(self) -> None:
        """交叉引用文本被转义 (CrossRef display text HTML escaped)."""
        r = CrossRef(label="fig:a", display_text="A & B")
        result = render(doc(Paragraph(children=[r])))
        assert "A &amp; B" in result


# ── Task 4 (M3): Unhandled node warning includes position (未处理节点警告含位置) ─


class TestUnhandledNodeWarning:
    """Unhandled node type warning position tests (未处理节点警告位置测试)."""

    def test_unhandled_node_warning_has_position(self) -> None:
        """未处理节点警告含位置 (Unhandled node warning includes position)."""
        from md_mid.diagnostic import DiagCollector

        class FakeNode(Node):
            @property
            def type(self) -> str:
                return "fake_type"

        dc = DiagCollector("test")
        n = FakeNode(position={"start": {"line": 42, "column": 5}})
        d = Document(children=[n])
        MarkdownRenderer(diag=dc).render(d)
        assert len(dc.warnings) == 1
        assert dc.warnings[0].position is not None
        assert dc.warnings[0].position.line == 42
