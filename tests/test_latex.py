from md_mid.latex import LaTeXRenderer
from md_mid.nodes import (
    Blockquote,
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    Emphasis,
    Environment,
    Figure,
    FootnoteDef,
    FootnoteRef,
    HardBreak,
    Heading,
    Link,
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


# 测试辅助函数 (Test helpers for Table cell construction)
def _cells(*texts: str) -> list[list[Node]]:
    """Wrap strings as Text node cells (字符串包装为 Text 节点单元格)."""
    return [[Text(content=t)] for t in texts]


def _rows(*row_texts: list[str]) -> list[list[list[Node]]]:
    """Wrap string rows as Text node rows (字符串行包装为 Text 节点行)."""
    return [[[Text(content=t)] for t in row] for row in row_texts]


def render(node, **kwargs):
    return LaTeXRenderer(**kwargs).render(node)


class TestInline:
    def test_text(self):
        assert render(Text(content="hello")) == "hello"

    def test_text_escapes_special(self):
        assert render(Text(content="a & b")) == r"a \& b"

    def test_strong(self):
        result = render(Strong(children=[Text(content="bold")]))
        assert result == r"\textbf{bold}"

    def test_emphasis(self):
        result = render(Emphasis(children=[Text(content="italic")]))
        assert result == r"\textit{italic}"

    def test_code_inline(self):
        result = render(CodeInline(content="x = 1"))
        assert result == r"\texttt{x = 1}"

    def test_math_inline(self):
        result = render(MathInline(content="E=mc^2"))
        assert result == "$E=mc^2$"

    def test_link(self):
        result = render(Link(url="http://x.com", children=[Text(content="click")]))
        assert result == r"\href{http://x.com}{click}"

    def test_softbreak(self):
        assert render(SoftBreak()) == "\n"

    def test_hardbreak(self):
        assert render(HardBreak()) == r"\\" + "\n"


class TestBlock:
    def test_heading_section(self):
        h = Heading(level=1, children=[Text(content="Intro")])
        assert render(h) == "\\section{Intro}\n"

    def test_heading_with_label(self):
        h = Heading(level=1, children=[Text(content="Intro")])
        h.metadata["label"] = "sec:intro"
        result = render(h)
        assert "\\section{Intro}" in result
        assert "\\label{sec:intro}" in result

    def test_heading_levels(self):
        assert "\\subsection{" in render(Heading(level=2, children=[Text(content="x")]))
        assert "\\subsubsection{" in render(Heading(level=3, children=[Text(content="x")]))
        assert "\\paragraph{" in render(Heading(level=4, children=[Text(content="x")]))

    def test_paragraph(self):
        p = Paragraph(children=[Text(content="Hello world.")])
        assert render(p).strip() == "Hello world."

    def test_math_block_no_label(self):
        m = MathBlock(content="x^2 + y^2 = z^2")
        result = render(m)
        assert "\\[" in result and "\\]" in result
        assert "x^2 + y^2 = z^2" in result

    def test_math_block_with_label(self):
        m = MathBlock(content="E=mc^2")
        m.metadata["label"] = "eq:einstein"
        result = render(m)
        assert "\\begin{equation}" in result
        assert "\\label{eq:einstein}" in result

    def test_code_block(self):
        c = CodeBlock(content="x = 1\ny = 2", language="python")
        result = render(c)
        assert "\\begin{lstlisting}" in result
        assert "x = 1" in result

    def test_unordered_list(self):
        lst = List(
            ordered=False,
            children=[
                ListItem(children=[Paragraph(children=[Text(content="a")])]),
                ListItem(children=[Paragraph(children=[Text(content="b")])]),
            ],
        )
        result = render(lst)
        assert "\\begin{itemize}" in result
        assert "\\item" in result

    def test_ordered_list(self):
        lst = List(
            ordered=True,
            children=[
                ListItem(children=[Paragraph(children=[Text(content="a")])]),
            ],
        )
        assert "\\begin{enumerate}" in result if (result := render(lst)) else False

    def test_blockquote(self):
        bq = Blockquote(children=[Paragraph(children=[Text(content="quote")])])
        result = render(bq)
        assert "\\begin{quotation}" in result

    def test_raw_block(self):
        rb = RawBlock(content=r"\newcommand{\myop}{\operatorname}")
        result = render(rb)
        assert result.strip() == r"\newcommand{\myop}{\operatorname}"

    def test_environment(self):
        env = Environment(
            name="theorem", children=[Paragraph(children=[Text(content="proof here")])]
        )
        result = render(env)
        assert "\\begin{theorem}" in result
        assert "\\end{theorem}" in result

    def test_thematic_break_default_newpage(self):
        """Default thematic break renders as newpage (默认分隔线渲染为 newpage)."""
        result = render(ThematicBreak())
        assert "\\newpage" in result

    def test_thematic_break_hrule(self):
        """hrule thematic break (hrule 分隔线)."""
        result = render(ThematicBreak(), thematic_break="hrule")
        assert "\\hrule" in result
        assert "\\newpage" not in result

    def test_thematic_break_ignore(self):
        """ignore thematic break produces empty (ignore 分隔线为空)."""
        result = render(ThematicBreak(), thematic_break="ignore")
        assert result.strip() == ""

    def test_code_block_minted(self):
        """minted code block rendering (minted 代码块渲染)."""
        c = CodeBlock(content="x = 1", language="python")
        result = render(c, code_style="minted")
        assert "\\begin{minted}{python}" in result
        assert "x = 1" in result
        assert "\\end{minted}" in result

    def test_code_block_minted_no_lang(self):
        """minted code block without language falls back to verbatim (minted 无语言回退)."""
        c = CodeBlock(content="hello", language="")
        result = render(c, code_style="minted")
        assert "\\begin{verbatim}" in result
        assert "\\end{verbatim}" in result

    def test_code_block_lstlisting_default(self):
        """Default lstlisting code block unchanged (默认 lstlisting 不变)."""
        c = CodeBlock(content="x = 1", language="python")
        result = render(c)
        assert "\\begin{lstlisting}" in result


# ── Citation / CrossRef (Task 11) ─────────────────────────────


class TestCiteRef:
    def test_cite_single(self):
        c = Citation(keys=["wang2024"], display_text="Wang et al.")
        assert render(c) == r"\cite{wang2024}"

    def test_cite_multiple(self):
        c = Citation(keys=["wang2024", "li2023"], display_text="1-2")
        assert render(c) == r"\cite{wang2024,li2023}"

    def test_cite_citeauthor(self):
        c = Citation(keys=["wang2024"], display_text="Wang", cmd="citeauthor")
        assert render(c) == r"\citeauthor{wang2024}"

    def test_ref_with_tilde(self):
        r = CrossRef(label="fig:result", display_text="图1")
        result = render(r)
        assert result == r"图1~\ref{fig:result}"

    def test_ref_no_tilde(self):
        r = CrossRef(label="fig:result", display_text="图1")
        result = render(r, ref_tilde=False)
        assert result == r"图1\ref{fig:result}"


# ── Full Document Mode (Task 12) ──────────────────────────────


class TestFullDocument:
    def _make_doc(self):
        doc = Document(
            children=[
                Heading(level=1, children=[Text(content="Intro")]),
                Paragraph(children=[Text(content="Content.")]),
            ]
        )
        doc.metadata.update(
            {
                "documentclass": "article",
                "classoptions": ["12pt", "a4paper"],
                "packages": ["amsmath", "graphicx"],
                "title": "My Paper",
                "author": "Author",
                "date": "2026",
                "abstract": "This is abstract.",
                "bibliography": "refs.bib",
                "bibstyle": "IEEEtran",
            }
        )
        return doc

    def test_full_mode_has_preamble(self):
        doc = self._make_doc()
        result = render(doc, mode="full")
        assert "\\documentclass[12pt,a4paper]{article}" in result
        assert "\\usepackage{amsmath}" in result
        assert "\\usepackage{graphicx}" in result

    def test_full_mode_has_title(self):
        result = render(self._make_doc(), mode="full")
        assert "\\title{My Paper}" in result
        assert "\\author{Author}" in result
        assert "\\date{2026}" in result

    def test_full_mode_has_document_env(self):
        result = render(self._make_doc(), mode="full")
        assert "\\begin{document}" in result
        assert "\\maketitle" in result
        assert "\\end{document}" in result

    def test_full_mode_has_abstract(self):
        result = render(self._make_doc(), mode="full")
        assert "\\begin{abstract}" in result
        assert "This is abstract." in result
        assert "\\end{abstract}" in result

    def test_full_mode_has_bibliography(self):
        result = render(self._make_doc(), mode="full")
        assert "\\bibliographystyle{IEEEtran}" in result
        assert "\\bibliography{refs}" in result  # 去掉 .bib 后缀

    def test_package_options(self):
        doc = self._make_doc()
        doc.metadata["package_options"] = {"geometry": "margin=1in"}
        result = render(doc, mode="full")
        assert "\\usepackage[margin=1in]{geometry}" in result


# ── Body / Fragment Mode (Task 13) ────────────────────────────


class TestBodyMode:
    def test_body_no_preamble(self):
        doc = Document(
            children=[
                Heading(level=1, children=[Text(content="Intro")]),
                Paragraph(children=[Text(content="Content.")]),
            ]
        )
        doc.metadata["title"] = "Should not appear"
        result = render(doc, mode="body")
        assert "\\documentclass" not in result
        assert "\\begin{document}" not in result
        assert "\\end{document}" not in result
        assert "\\section{Intro}" in result
        assert "Content." in result

    def test_body_no_bibliography(self):
        doc = Document(children=[])
        doc.metadata["bibliography"] = "refs.bib"
        result = render(doc, mode="body")
        assert "\\bibliography" not in result


class TestFragmentMode:
    def test_fragment_no_structure(self):
        doc = Document(
            children=[
                Heading(level=1, children=[Text(content="Title")]),
                Paragraph(children=[Text(content="Content.")]),
            ]
        )
        result = render(doc, mode="fragment")
        assert "\\section" not in result
        assert "Content." in result

    def test_fragment_preserves_inline(self):
        doc = Document(
            children=[
                Paragraph(
                    children=[
                        Text(content="This is "),
                        Strong(children=[Text(content="bold")]),
                    ]
                ),
            ]
        )
        result = render(doc, mode="fragment")
        assert "\\textbf{bold}" in result


# ── Figure / Table (Task 14) ──────────────────────────────────


class TestFigure:
    def test_basic_figure(self):
        f = Figure(src="figs/a.png", alt="图A")
        f.metadata["caption"] = "示意图"
        f.metadata["label"] = "fig:a"
        result = render(f)
        assert "\\begin{figure}[htbp]" in result
        assert "\\centering" in result
        assert "\\includegraphics" in result
        assert "figs/a.png" in result
        assert "\\caption{示意图}" in result
        assert "\\label{fig:a}" in result
        assert "\\end{figure}" in result

    def test_figure_with_width(self):
        f = Figure(src="figs/a.png", alt="")
        f.metadata["width"] = r"0.8\textwidth"
        result = render(f)
        assert r"width=0.8\textwidth" in result

    def test_figure_custom_placement(self):
        f = Figure(src="figs/a.png", alt="")
        f.metadata["placement"] = "t"
        result = render(f)
        assert "\\begin{figure}[t]" in result


class TestTable:
    def test_basic_table(self):
        t = Table(
            headers=_cells("Method", "RMSE"),
            alignments=["left", "left"],
            rows=_rows(["RANSAC", "2.3"], ["Ours", "1.9"]),
        )
        t.metadata["caption"] = "Results"
        t.metadata["label"] = "tab:results"
        result = render(t)
        assert "\\begin{table}[htbp]" in result
        assert "\\centering" in result
        assert "\\begin{tabular}" in result
        assert "\\caption{Results}" in result
        assert "\\label{tab:results}" in result
        assert "Method" in result
        assert "RANSAC" in result
        assert "\\hline" in result
        assert "\\end{tabular}" in result
        assert "\\end{table}" in result

    def test_table_cell_bold_latex(self) -> None:
        """表格粗体 LaTeX 渲染 (Bold in table cell renders as \\textbf)."""
        t = Table(
            headers=[[Strong(children=[Text(content="Method")])]],
            alignments=["left"],
            rows=[[[Text(content="RANSAC")]]],
        )
        t.metadata["caption"] = "T"
        result = render(t)
        assert "\\textbf{Method}" in result

    def test_table_cell_code_latex(self) -> None:
        """表格代码 LaTeX 渲染 (Code in table cell renders as \\texttt)."""
        t = Table(
            headers=_cells("H"),
            alignments=["left"],
            rows=[[[CodeInline(content="x=1")]]],
        )
        t.metadata["caption"] = "T"
        result = render(t)
        assert "\\texttt{x=1}" in result


# ── Task 3: Diagnostic warnings in renderer ───────────────────────────────────


class TestDiagnostics:
    def test_unhandled_node_type_triggers_warning(self) -> None:
        """未处理节点类型触发 warning（Unhandled node type triggers warning）."""
        from md_mid.diagnostic import DiagCollector
        from md_mid.nodes import Node

        # 创建一个无法识别的节点类型（Create a node with unrecognized type）
        class UnknownNode(Node):
            @property
            def type(self) -> str:
                return "unknown_custom_type"

        dc = DiagCollector("test")
        renderer = LaTeXRenderer(diag=dc)
        renderer.render(UnknownNode())
        assert any("Unhandled node type" in d.message for d in dc.warnings)

    def test_known_node_type_no_warning(self) -> None:
        """已知节点类型不触发 warning（Known node type does not trigger warning）."""
        from md_mid.diagnostic import DiagCollector

        dc = DiagCollector("test")
        renderer = LaTeXRenderer(diag=dc)
        renderer.render(Paragraph(children=[Text(content="hello")]))
        assert not any("Unhandled" in d.message for d in dc.warnings)


# ── Fix C: HTML-kind RawBlock skipped in LaTeX renderer ───────────────────────


class TestHtmlRawBlockSkipped:
    """HTML-kind RawBlock produces no LaTeX output (HTML 块无 LaTeX 输出测试)."""

    def test_html_raw_block_skipped_in_latex(self) -> None:
        """Fix C: HTML-kind RawBlock 在 LaTeX 渲染器中被跳过 (HTML block skipped in LaTeX)."""
        rb = RawBlock(content="<div>hello</div>", kind="html")
        result = LaTeXRenderer().render(rb)
        assert result == ""

    def test_latex_raw_block_still_emitted(self) -> None:
        """Fix C: LaTeX-kind RawBlock 仍正常输出 (LaTeX block still emits content)."""
        rb = RawBlock(content="\\newcommand{\\myvec}{\\mathbf}", kind="latex")
        result = LaTeXRenderer().render(rb)
        assert "\\newcommand" in result


# ── Task 8: Environment args as YAML sequence ─────────────────────────────────


class TestEnvironmentArgs:
    """Environment args as YAML list tests (环境参数列表测试)."""

    def test_environment_args_list(self) -> None:
        """Environment args as list renders {arg1} (环境列表参数渲染).

        Tests that a single-element list arg produces one brace group.
        (测试单元素列表参数生成一个花括号组。)
        """
        env = Environment(
            name="subfigure",
            children=[Paragraph(children=[Text(content="content")])],
        )
        env.metadata["args"] = [r"0.45\textwidth"]
        result = render(env)
        assert r"\begin{subfigure}{0.45\textwidth}" in result

    def test_environment_args_multiple(self) -> None:
        """Multiple args render as consecutive braces (多参数渲染为连续花括号).

        Tests that a two-element list produces two consecutive brace groups.
        (测试两元素列表生成两个连续花括号组。)
        """
        env = Environment(
            name="myenv",
            children=[Paragraph(children=[Text(content="text")])],
        )
        env.metadata["args"] = ["arg1", "arg2"]
        result = render(env)
        assert r"\begin{myenv}{arg1}{arg2}" in result

    def test_environment_args_string_unchanged(self) -> None:
        """String args still works as before (字符串参数不变).

        Tests that a plain string arg is still wrapped in one brace group.
        (测试普通字符串参数仍被包裹在一个花括号组中。)
        """
        env = Environment(
            name="test",
            children=[Paragraph(children=[Text(content="body")])],
        )
        env.metadata["args"] = "single"
        result = render(env)
        assert r"\begin{test}{single}" in result

    def test_environment_options_and_args_combined(self) -> None:
        """Options and args render together: [opt]{arg} (选项和参数组合渲染).

        Tests that options come before list args in the header.
        (测试选项在列表参数之前出现在头部。)
        """
        env = Environment(
            name="minipage",
            children=[Paragraph(children=[Text(content="text")])],
        )
        env.metadata["options"] = "c"
        env.metadata["args"] = [r"0.5\textwidth"]
        result = render(env)
        assert r"\begin{minipage}[c]{0.5\textwidth}" in result


# ── Task 9: LaTeX Two-Pass Footnote Rendering ─────────────────────────────────


class TestLatexFootnotes:
    """LaTeX two-pass footnote rendering tests (LaTeX 两遍脚注渲染测试)."""

    def test_footnote_inline_expansion(self) -> None:
        """Footnote expands at reference site (脚注在引用处展开).

        FootnoteRef is replaced by \\footnote{content} from the matching FootnoteDef.
        (FootnoteRef 被匹配的 FootnoteDef 内容替换为 \\footnote{content}。)
        """
        fn_def = FootnoteDef(
            def_id="0",
            children=[Paragraph(children=[Text(content="My note")])],
        )
        p = Paragraph(children=[
            Text(content="See this"),
            FootnoteRef(ref_id="0"),
            Text(content=" and more."),
        ])
        doc = Document(children=[p, fn_def])
        result = render(doc)
        assert "\\footnote{My note}" in result
        # FootnoteDef itself should not appear in output (脚注定义不出现在输出中)
        assert "\\footnotetext" not in result

    def test_footnote_fallback_no_def(self) -> None:
        """Unknown footnote ref falls back gracefully (未知脚注引用回退).

        When a FootnoteRef has no matching def, produces \\footnote{[ref_id]}.
        (当 FootnoteRef 没有匹配定义时，产出 \\footnote{[ref_id]}。)
        """
        p = Paragraph(children=[
            Text(content="See this"),
            FootnoteRef(ref_id="999"),
        ])
        doc = Document(children=[p])
        result = render(doc)
        # No crash, produces the [ref_id] fallback marker (不崩溃，产出 [ref_id] 回退标记)
        assert "\\footnote{[999]}" in result

    def test_footnote_multiple_refs(self) -> None:
        """Multiple footnotes each expand correctly (多个脚注各自正确展开).

        Two FootnoteDefs and two FootnoteRefs each expand to the correct content.
        (两个脚注定义和引用各自展开为正确内容。)
        """
        fn1 = FootnoteDef(def_id="0", children=[Paragraph(children=[Text(content="Note A")])])
        fn2 = FootnoteDef(def_id="1", children=[Paragraph(children=[Text(content="Note B")])])
        p = Paragraph(children=[
            Text(content="First"),
            FootnoteRef(ref_id="0"),
            Text(content=" second"),
            FootnoteRef(ref_id="1"),
        ])
        doc = Document(children=[p, fn1, fn2])
        result = render(doc)
        assert "\\footnote{Note A}" in result
        assert "\\footnote{Note B}" in result

    def test_footnote_def_produces_no_output(self) -> None:
        """FootnoteDef node alone produces no LaTeX output (FootnoteDef 节点独立渲染为空字符串).

        Content is already expanded inline at the FootnoteRef site; the def itself
        must not emit any LaTeX. (内容已在引用处展开，定义节点本身不输出任何内容。)
        """
        fn_def = FootnoteDef(
            def_id="0",
            children=[Paragraph(children=[Text(content="Unused")])],
        )
        result = LaTeXRenderer().render(fn_def)
        assert result == ""


# ── Task 10: LaTeX Locale Overrides ───────────────────────────────────────────


class TestLatexLocale:
    """LaTeX locale override tests (LaTeX 本地化覆盖测试)."""

    def test_latex_locale_english_figurename(self) -> None:
        """English locale injects figurename and tablename overrides (英文本地化注入图表名覆盖).

        With locale='en', render_document() must emit \\renewcommand for both
        \\figurename and \\tablename. (locale='en' 时，两个 renewcommand 必须出现。)
        """
        doc = Document(children=[], metadata={})
        result = LaTeXRenderer(locale="en").render(doc)
        assert "\\renewcommand{\\figurename}{Figure}" in result
        assert "\\renewcommand{\\tablename}{Table}" in result

    def test_latex_locale_zh_no_override(self) -> None:
        """Default (zh) locale does not inject renewcommand overrides (默认中文本地化不注入覆盖).

        With locale='zh' (default), no \\renewcommand lines should appear for
        figurename or tablename. (默认中文时不应出现 renewcommand 覆盖。)
        """
        doc = Document(children=[], metadata={})
        result = LaTeXRenderer(locale="zh").render(doc)
        assert "\\renewcommand{\\figurename}" not in result
        assert "\\renewcommand{\\tablename}" not in result
