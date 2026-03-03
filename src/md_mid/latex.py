"""LaTeX Renderer：EAST → LaTeX 文本。

支持三种输出模式：
- full: 完整 .tex 文档（含 preamble、title、abstract、bibliography）
- body: 仅 \\begin{document}...\\end{document} 内部正文
- fragment: 纯正文片段，heading 降级为纯文本
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from md_mid.diagnostic import DiagCollector
from md_mid.escape import escape_latex_with_protection
from md_mid.nodes import (
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Environment,
    Figure,
    FootnoteDef,
    FootnoteRef,
    Heading,
    Image,
    Link,
    List,
    MathBlock,
    MathInline,
    Node,
    RawBlock,
    Table,
    Text,
)

_HEADING_CMDS = {
    1: "section",
    2: "subsection",
    3: "subsubsection",
    4: "paragraph",
    5: "subparagraph",
    6: "subparagraph",
}


class LaTeXRenderer:
    def __init__(
        self,
        mode: str = "full",
        ref_tilde: bool = True,
        code_style: str = "lstlisting",
        thematic_break: str = "newpage",
        locale: str = "zh",
        diag: DiagCollector | None = None,
    ) -> None:
        """初始化 LaTeX 渲染器（Initialize LaTeX renderer）.

        Args:
            mode: Output mode: full/body/fragment (输出模式)
            ref_tilde: Whether to use tilde before \\ref (是否在 \\ref 前加波浪号)
            code_style: Code block style: lstlisting | minted (代码块样式)
            thematic_break: Thematic break style: newpage | hrule | ignore (分隔线样式)
            locale: Output locale: zh | en (输出语言环境)
            diag: Optional diagnostic collector (可选诊断收集器)
        """
        self.mode = mode
        self.ref_tilde = ref_tilde
        self.code_style = code_style
        self.thematic_break = thematic_break
        self.locale = locale
        self._fn_defs: dict[str, Node] = {}  # footnote defs by id (按 ID 索引的脚注定义)
        self.diag = diag

    def render(self, node: Node) -> str:
        """渲染节点为 LaTeX 字符串（Render node to LaTeX string）."""
        method_name = f"render_{node.type}"
        method: Callable[[Node], str] | None = getattr(self, method_name, None)
        if method is None:
            # 未处理的节点类型（Unhandled node type, rendering children only）
            if self.diag is not None:
                self.diag.warning(
                    f"Unhandled node type '{node.type}', rendering children only",
                )
            return self.render_children(node)
        return method(node)

    def render_children(self, node: Node) -> str:
        return "".join(self.render(child) for child in node.children)

    def _collect_footnote_defs(self, node: Node) -> None:
        """Pre-scan tree to collect FootnoteDef nodes by id (预扫描收集脚注定义).

        Called once from render_document(), not from render().
        (从 render_document() 调用一次，而不是从 render() 调用。)

        Args:
            node: Node to scan recursively (递归扫描的节点)
        """
        if isinstance(node, FootnoteDef):
            self._fn_defs[node.def_id] = node
        for child in node.children:
            self._collect_footnote_defs(child)

    # -- 文档 ----------------------------------------------------------------

    def render_document(self, node: Node) -> str:
        # Reset per-document state to allow renderer reuse (重置每文档状态以支持复用)
        self._fn_defs.clear()
        # Pre-scan: collect all FootnoteDef nodes (预扫描：收集所有脚注定义)
        self._collect_footnote_defs(node)
        body = self.render_children(node)

        if self.mode in ("body", "fragment"):
            return body

        # full mode
        meta = node.metadata
        lines: list[str] = []

        # documentclass
        cls: str = str(meta.get("documentclass", "article") or "article")
        opts_raw = meta.get("classoptions", [])
        opts: list[str] = list(cast(list[str], opts_raw)) if opts_raw else []
        opts_str = f"[{','.join(opts)}]" if opts else ""
        lines.append(f"\\documentclass{opts_str}{{{cls}}}")

        # packages (带 options)
        pkg_opts: dict[str, str] = cast(dict[str, str], meta.get("package_options", {}))
        packages: list[str] = cast(list[str], meta.get("packages", []))
        for pkg in packages:
            if pkg in pkg_opts:
                lines.append(f"\\usepackage[{pkg_opts[pkg]}]{{{pkg}}}")
            else:
                lines.append(f"\\usepackage{{{pkg}}}")

        # 如果 package_options 中有不在 packages 列表中的包（extra packages in pkg_opts）
        for pkg, pkg_opt in pkg_opts.items():
            if pkg not in packages:
                lines.append(f"\\usepackage[{pkg_opt}]{{{pkg}}}")

        # bibliography_mode 决定是否输出参考文献相关命令
        # (bibliography_mode determines whether to emit bibliography commands)
        bib: str = str(meta.get("bibliography", "") or "")
        bib_mode: str = str(meta.get("bibliography_mode", "auto") or "auto")
        bib_active: bool = bib_mode in ("auto", "standalone")

        # bibstyle — 仅在参考文献激活时输出 (Only emit when bibliography is active)
        if bib_active:
            if bibstyle := meta.get("bibstyle"):
                lines.append(f"\\bibliographystyle{{{bibstyle}}}")

        # title/author/date
        for key in ("title", "author", "date"):
            if val := meta.get(key):
                lines.append(f"\\{key}{{{val}}}")

        # extra preamble
        if preamble := meta.get("preamble"):
            lines.append(str(preamble))

        lines.append("")
        lines.append("\\begin{document}")
        lines.append("\\maketitle")

        # abstract
        if abstract := meta.get("abstract"):
            lines.append("")
            lines.append("\\begin{abstract}")
            lines.append(str(abstract).strip())
            lines.append("\\end{abstract}")

        lines.append("")
        lines.append(body)

        # bibliography — 仅在激活且 bib 文件存在时输出
        # (Only emit when active and bib file specified)
        if bib and bib_active:
            bib_name = bib.removesuffix(".bib")
            lines.append(f"\\bibliography{{{bib_name}}}")

        lines.append("")
        lines.append("\\end{document}")
        return "\n".join(lines) + "\n"

    # -- 块级节点 ------------------------------------------------------------

    def render_heading(self, node: Node) -> str:
        if self.mode == "fragment":
            # fragment 模式：heading 输出为纯文本段落
            text = self.render_children(node)
            return f"{text}\n\n"

        h = cast(Heading, node)
        cmd = _HEADING_CMDS.get(h.level, "subparagraph")
        text = self.render_children(node)
        result = f"\\{cmd}{{{text}}}\n"
        if label := node.metadata.get("label"):
            result += f"\\label{{{label}}}\n"
        return result

    def render_paragraph(self, node: Node) -> str:
        text = self.render_children(node)
        return f"{text}\n\n"

    def render_math_block(self, node: Node) -> str:
        mb = cast(MathBlock, node)
        if label := node.metadata.get("label"):
            return (
                f"\\begin{{equation}}\n{mb.content}\n\\label{{{label}}}\n\\end{{equation}}\n"
            )
        return f"\\[\n{mb.content}\n\\]\n"

    def render_code_block(self, node: Node) -> str:
        """渲染代码块 (Render code block: lstlisting or minted)."""
        cb = cast(CodeBlock, node)
        if self.code_style == "minted":
            if cb.language:
                return (
                    f"\\begin{{minted}}{{{cb.language}}}\n"
                    f"{cb.content}\n"
                    f"\\end{{minted}}\n"
                )
            # No language: fall back to verbatim (无语言：回退到 verbatim)
            return f"\\begin{{verbatim}}\n{cb.content}\n\\end{{verbatim}}\n"
        # Default: lstlisting (默认：lstlisting)
        if cb.language:
            return (
                f"\\begin{{lstlisting}}[language={cb.language}]\n"
                f"{cb.content}\n"
                f"\\end{{lstlisting}}\n"
            )
        return f"\\begin{{lstlisting}}\n{cb.content}\n\\end{{lstlisting}}\n"

    def render_list(self, node: Node) -> str:
        lst = cast(List, node)
        env = "enumerate" if lst.ordered else "itemize"
        items = self.render_children(node)
        return f"\\begin{{{env}}}\n{items}\\end{{{env}}}\n"

    def render_list_item(self, node: Node) -> str:
        content = self.render_children(node).strip()
        return f"\\item {content}\n"

    def render_blockquote(self, node: Node) -> str:
        content = self.render_children(node)
        return f"\\begin{{quotation}}\n{content}\\end{{quotation}}\n"

    def render_raw_block(self, node: Node) -> str:
        rb = cast(RawBlock, node)
        if rb.kind == "html":
            # HTML passthrough has no LaTeX equivalent — skip (HTML 块无 LaTeX 等价，跳过)
            return ""
        return f"{rb.content}\n"

    def render_environment(self, node: Node) -> str:
        """渲染 LaTeX 环境（Render LaTeX environment with optional options and args）.

        Builds the \\begin{name}[options]{arg1}{arg2}...\\end{name} block.
        (构建 \\begin{name}[options]{arg1}{arg2}...\\end{name} 块。)

        Args:
            node: An Environment node (环境节点)

        Returns:
            LaTeX string for the environment (环境对应的 LaTeX 字符串)
        """
        env = cast(Environment, node)
        name = env.name
        meta = node.metadata
        opts = meta.get("options", "")
        args = meta.get("args", "")

        header = f"\\begin{{{name}}}"
        if opts:
            header += f"[{opts}]"
        # Handle args as list or string (处理列表或字符串参数)
        if isinstance(args, list):
            for arg in args:
                header += f"{{{arg}}}"
        elif args:
            header += f"{{{args}}}"

        content = self.render_children(node)

        # Early return with label when present (有 label 时提前返回)
        if label := meta.get("label"):
            return f"{header}\n\\label{{{label}}}\n{content}\\end{{{name}}}\n"

        return f"{header}\n{content}\\end{{{name}}}\n"

    def render_thematic_break(self, node: Node) -> str:
        """渲染分隔线 (Render thematic break: newpage | hrule | ignore)."""
        if self.thematic_break == "hrule":
            return "\\hrule\n"
        if self.thematic_break == "ignore":
            return ""
        return "\\newpage\n"

    def render_figure(self, node: Node) -> str:
        fig = cast(Figure, node)
        meta = node.metadata
        placement = str(meta.get("placement", "htbp"))
        width = str(meta.get("width", ""))
        caption = str(meta.get("caption", ""))
        label = str(meta.get("label", ""))

        lines = [f"\\begin{{figure}}[{placement}]"]
        lines.append("\\centering")

        gfx_opts = f"width={width}" if width else ""
        if gfx_opts:
            lines.append(f"\\includegraphics[{gfx_opts}]{{{fig.src}}}")
        else:
            lines.append(f"\\includegraphics{{{fig.src}}}")

        if caption:
            lines.append(f"\\caption{{{caption}}}")
        if label:
            lines.append(f"\\label{{{label}}}")

        lines.append("\\end{figure}")
        return "\n".join(lines) + "\n"

    def render_image(self, node: Node) -> str:
        # Image without figure wrapping — if metadata has caption/label,
        # promote to figure-like rendering (有 caption/label 时升级为 figure 环境)
        img = cast(Image, node)
        meta = node.metadata
        if meta.get("caption") or meta.get("label"):
            placement = str(meta.get("placement", "htbp"))
            width = str(meta.get("width", ""))
            caption = str(meta.get("caption", ""))
            label = str(meta.get("label", ""))

            lines = [f"\\begin{{figure}}[{placement}]"]
            lines.append("\\centering")

            gfx_opts = f"width={width}" if width else ""
            if gfx_opts:
                lines.append(f"\\includegraphics[{gfx_opts}]{{{img.src}}}")
            else:
                lines.append(f"\\includegraphics{{{img.src}}}")

            if caption:
                lines.append(f"\\caption{{{caption}}}")
            if label:
                lines.append(f"\\label{{{label}}}")

            lines.append("\\end{figure}")
            return "\n".join(lines) + "\n"

        return f"\\includegraphics{{{img.src}}}"

    def render_table(self, node: Node) -> str:
        tbl = cast(Table, node)
        meta = node.metadata
        caption = str(meta.get("caption", ""))
        label = str(meta.get("label", ""))
        placement = str(meta.get("placement", "htbp"))

        # Column alignment (列对齐)
        align_map = {"left": "l", "right": "r", "center": "c"}
        col_spec = "".join(align_map.get(a, "l") for a in tbl.alignments)
        if not col_spec:
            col_spec = "l" * len(tbl.headers)

        lines = [f"\\begin{{table}}[{placement}]"]
        lines.append("\\centering")

        if caption:
            lines.append(f"\\caption{{{caption}}}")
        if label:
            lines.append(f"\\label{{{label}}}")

        lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
        lines.append("\\hline")

        # 表头行 (Header row) — render inline nodes in each cell
        header_row = " & ".join(self._render_nodes(h) for h in tbl.headers)
        lines.append(f"{header_row} \\\\")
        lines.append("\\hline")

        # 数据行 (Data rows) — render inline nodes in each cell
        for row in tbl.rows:
            data_row = " & ".join(self._render_nodes(cell) for cell in row)
            lines.append(f"{data_row} \\\\")

        lines.append("\\hline")
        lines.append("\\end{tabular}")
        lines.append("\\end{table}")
        return "\n".join(lines) + "\n"

    def _render_nodes(self, nodes: list[Node]) -> str:
        """Render a list of inline nodes (渲染行内节点列表)."""
        return "".join(self.render(n) for n in nodes)

    # -- 行内节点 ------------------------------------------------------------

    def render_text(self, node: Node) -> str:
        txt = cast(Text, node)
        return escape_latex_with_protection(txt.content)

    def render_strong(self, node: Node) -> str:
        content = self.render_children(node)
        return f"\\textbf{{{content}}}"

    def render_emphasis(self, node: Node) -> str:
        content = self.render_children(node)
        return f"\\textit{{{content}}}"

    def render_code_inline(self, node: Node) -> str:
        ci = cast(CodeInline, node)
        return f"\\texttt{{{ci.content}}}"

    def render_math_inline(self, node: Node) -> str:
        mi = cast(MathInline, node)
        return f"${mi.content}$"

    def render_link(self, node: Node) -> str:
        lnk = cast(Link, node)
        text = self.render_children(node)
        return f"\\href{{{lnk.url}}}{{{text}}}"

    def render_softbreak(self, node: Node) -> str:
        return "\n"

    def render_hardbreak(self, node: Node) -> str:
        return "\\\\\n"

    def render_citation(self, node: Node) -> str:
        cit = cast(Citation, node)
        keys = ",".join(cit.keys)
        return f"\\{cit.cmd}{{{keys}}}"

    def render_cross_ref(self, node: Node) -> str:
        ref = cast(CrossRef, node)
        sep = "~" if self.ref_tilde else ""
        return f"{ref.display_text}{sep}\\ref{{{ref.label}}}"

    def render_footnote_ref(self, node: Node) -> str:
        """Expand footnote inline at reference site (在引用处展开脚注).

        Args:
            node: FootnoteRef node (FootnoteRef 节点)

        Returns:
            \\footnote{content} with the content from the matching def (内联展开的脚注)
        """
        fr = cast(FootnoteRef, node)
        fn_def = self._fn_defs.get(fr.ref_id)
        if fn_def is not None:
            # Render def children and strip whitespace (渲染定义内容并去除首尾空白)
            content = self.render_children(fn_def).strip()
            return f"\\footnote{{{content}}}"
        # Fallback: unknown ref — emit marker (回退：未知引用)
        return f"\\footnote{{[{fr.ref_id}]}}"

    def render_footnote_def(self, node: Node) -> str:
        """Skip — content already expanded at FootnoteRef site (跳过 — 内容已在引用处展开).

        Args:
            node: FootnoteDef node (FootnoteDef 节点)

        Returns:
            Empty string (空字符串)
        """
        return ""
