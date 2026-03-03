"""端到端集成测试：md-mid source → LaTeX / Markdown output
(End-to-end integration tests for LaTeX and Markdown pipelines)
"""

from pathlib import Path

from md_mid.comment import process_comments
from md_mid.latex import LaTeXRenderer
from md_mid.markdown import MarkdownRenderer
from md_mid.parser import parse

FIXTURES = Path(__file__).parent / "fixtures"


def convert(text: str, mode: str = "full") -> str:
    doc = parse(text)
    east = process_comments(doc, "test.md")
    return LaTeXRenderer(mode=mode).render(east)


class TestHeadingParagraph:
    def test_section_with_label(self):
        text = (FIXTURES / "heading_para.mid.md").read_text()
        result = convert(text)
        assert "\\section{Introduction}" in result
        assert "\\label{sec:intro}" in result
        assert "\\subsection{Background}" in result

    def test_inline_formatting(self):
        text = (FIXTURES / "heading_para.mid.md").read_text()
        result = convert(text)
        assert "\\textbf{bold}" in result
        assert "\\textit{italic}" in result

    def test_math(self):
        text = (FIXTURES / "heading_para.mid.md").read_text()
        result = convert(text)
        assert "$x^2$" in result
        # 有 label 的公式块应使用 equation 环境
        assert "\\begin{equation}" in result
        assert "\\label{eq:einstein}" in result


class TestMath:
    def test_inline_math(self):
        text = (FIXTURES / "math.mid.md").read_text()
        result = convert(text)
        assert "$a + b = c$" in result

    def test_block_math_no_label(self):
        text = (FIXTURES / "math.mid.md").read_text()
        result = convert(text)
        assert "\\[" in result
        assert "\\sum" in result

    def test_block_math_with_label(self):
        text = (FIXTURES / "math.mid.md").read_text()
        result = convert(text)
        assert "\\label{eq:integral}" in result


class TestRawAndEnvironment:
    def test_raw_passthrough(self):
        text = "<!-- begin: raw -->\n\\DeclareMathOperator{\\argmin}{argmin}\n<!-- end: raw -->\n"
        result = convert(text)
        assert "\\DeclareMathOperator{\\argmin}{argmin}" in result

    def test_environment(self):
        text = "<!-- begin: theorem -->\nAll primes > 2 are odd.\n<!-- end: theorem -->\n"
        result = convert(text)
        assert "\\begin{theorem}" in result
        assert "\\end{theorem}" in result


class TestFullExample:
    """对照 PRD 13.2 验证完整输出。"""

    def test_preamble(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\documentclass[12pt,a4paper]{article}" in result
        assert "\\usepackage{amsmath}" in result
        assert "\\usepackage{algorithm2e}" in result
        assert "\\bibliographystyle{IEEEtran}" in result
        assert "\\title{" in result

    def test_abstract(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\begin{abstract}" in result
        assert "FPGA" in result

    def test_sections_and_labels(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\section{绪论}" in result
        assert "\\label{sec:intro}" in result
        assert "\\subsection{相关工作}" in result
        assert "\\label{sec:related}" in result

    def test_citations(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\cite{wang2024}" in result
        assert "\\cite{fischler1981}" in result
        assert "\\cite{aiger2008}" in result

    def test_cross_refs(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\ref{fig:pipeline}" in result
        assert "\\ref{tab:results}" in result
        assert "\\ref{eq:transform}" in result
        assert "\\ref{sec:related}" in result

    def test_figure(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\begin{figure}" in result
        assert "\\includegraphics" in result
        assert "figures/pipeline.png" in result
        assert "\\caption{点云配准方法分类与本文方法定位}" in result

    def test_table(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\begin{table}" in result
        assert "\\begin{tabular}" in result
        assert "RANSAC" in result

    def test_equation_with_label(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\begin{equation}" in result
        assert "\\label{eq:transform}" in result

    def test_enumerate(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\begin{enumerate}" in result
        assert "\\item" in result

    def test_bibliography(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="full")
        assert "\\bibliography{refs}" in result

    def test_body_mode(self):
        text = (FIXTURES / "full_example.mid.md").read_text()
        result = convert(text, mode="body")
        assert "\\documentclass" not in result
        assert "\\begin{document}" not in result
        assert "\\section{绪论}" in result
        assert "\\cite{wang2024}" in result


# ── Markdown E2E Tests (Markdown 端到端测试) ──────────────────────


def _convert_markdown(text: str, **kwargs: object) -> str:
    """Helper: parse → comment-process → render as Markdown.

    辅助函数：解析 → 处理注释 → 渲染为 Markdown。
    """
    doc = parse(text)
    east = process_comments(doc, "test.md")
    return MarkdownRenderer(**kwargs).render(east)


def test_markdown_e2e_full_example(tmp_path: Path) -> None:
    """Full example Markdown conversion E2E test.

    全示例 Markdown 转换端到端测试。
    """
    from click.testing import CliRunner

    from md_mid.cli import main

    src = FIXTURES / "full_example.mid.md"
    out = tmp_path / "full.rendered.md"
    result = CliRunner().invoke(main, [str(src), "-t", "markdown", "-o", str(out)])
    assert result.exit_code == 0, result.output
    content = out.read_text()
    # YAML front matter (YAML 前言)
    assert "---" in content
    assert "title:" in content
    # Cross-refs as HTML anchors (交叉引用为 HTML 锚点)
    assert "<a href=" in content
    # Citation footnotes (引用脚注)
    assert "[^" in content
    # Figure blocks (图块)
    assert "<figure" in content
    # Table blocks (表格块)
    assert "<table>" in content
    # Math preserved (数学公式保留)
    assert "$$" in content


def test_markdown_heading_labels_as_anchors(tmp_path: Path) -> None:
    """Heading labels become anchors in Markdown output.

    标题 label 转为锚点。
    """
    from click.testing import CliRunner

    from md_mid.cli import main

    src = tmp_path / "test.mid.md"
    src.write_text("# Introduction\n<!-- label: sec:intro -->\n\nSome text.\n")
    out = tmp_path / "out.rendered.md"
    CliRunner().invoke(main, [str(src), "-t", "markdown", "-o", str(out)])
    content = out.read_text()
    assert "{#sec:intro}" in content or 'id="sec:intro"' in content


def test_markdown_e2e_citations_and_footnotes() -> None:
    """Citations are rendered as footnote references with definitions at end.

    引用渲染为脚注引用，定义在末尾。
    """
    text = "[Wang et al.](cite:wang2024) studied point clouds.\n"
    content = _convert_markdown(text)
    # Body contains footnote reference (正文包含脚注引用)
    assert "Wang et al.[^wang2024]" in content
    # Footnote definition at end (脚注定义在末尾)
    assert "[^wang2024]:" in content


def test_markdown_e2e_cross_ref() -> None:
    """Cross-references become HTML anchor links.

    交叉引用变为 HTML 锚点链接。
    """
    text = "See [Figure 1](ref:fig:a) for details.\n"
    content = _convert_markdown(text)
    assert '<a href="#fig:a">Figure 1</a>' in content


def test_markdown_e2e_figure_rendering() -> None:
    """Figure with caption and label renders as HTML figure block.

    带标题和标签的图渲染为 HTML figure 块。
    """
    text = (
        "![Pipeline](figures/pipeline.png)\n"
        "<!-- caption: System Pipeline -->\n"
        "<!-- label: fig:pipeline -->\n"
    )
    content = _convert_markdown(text)
    assert '<figure id="fig:pipeline">' in content
    assert "System Pipeline" in content
    assert "图 1" in content


def test_markdown_e2e_table_rendering() -> None:
    """Table with caption renders as HTML table block.

    带标题的表格渲染为 HTML table 块。
    """
    text = (
        "| A | B |\n|---|---|\n| 1 | 2 |\n<!-- caption: My Table -->\n<!-- label: tab:mytable -->\n"
    )
    content = _convert_markdown(text)
    assert '<figure id="tab:mytable">' in content
    assert "<table>" in content
    assert "表 1" in content


def test_markdown_e2e_front_matter() -> None:
    """Document metadata renders as YAML front matter.

    文档元数据渲染为 YAML 前言。
    """
    text = "<!-- title: My Paper -->\n<!-- author: Alice -->\n\n# Introduction\n\nHello.\n"
    content = _convert_markdown(text)
    assert "---" in content
    assert "title: My Paper" in content
    assert "author: Alice" in content
    # Front matter before body (前言在正文之前)
    fm_pos = content.find("title: My Paper")
    body_pos = content.find("Hello.")
    assert fm_pos < body_pos
