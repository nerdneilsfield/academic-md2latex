"""LaTeX Renderer：EAST → LaTeX 文本。

支持三种输出模式：
- full: 完整 .tex 文档（含 preamble、title、abstract、bibliography）
- body: 仅 \\begin{document}...\\end{document} 内部正文
- fragment: 纯正文片段，heading 降级为纯文本
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import cast

from wenqiao.diagnostic import DiagCollector
from wenqiao.escape import escape_latex, escape_latex_with_protection
from wenqiao.latex_blocks import LaTeXBlockMixin
from wenqiao.nodes import (
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    FootnoteDef,
    FootnoteRef,
    Heading,
    Link,
    List,
    MathBlock,
    MathInline,
    Node,
    RawBlock,
    Text,
)


def _escape_url_for_latex(url: str) -> str:
    """Escape special chars in URL for \\href (URL LaTeX 特殊字符转义).

    Only escapes characters that break LaTeX \\href compilation:
    backslash, percent, hash, braces.
    (仅转义会破坏 LaTeX \\href 编译的字符。)

    Args:
        url: Raw URL string (原始 URL 字符串)

    Returns:
        Escaped URL safe for \\href first argument (适用于 \\href 第一参数的转义 URL)
    """
    return (
        url.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("#", "\\#")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


# Detect headings that already carry a numeric prefix like "1. 引言" or "2.1 相关工作".
# When matched, starred commands (\section* etc.) suppress LaTeX auto-numbering.
# (检测已含数字前缀的标题，使用星号命令避免 LaTeX 自动编号与文本编号重叠)
_NUMBERED_HEADING_RE = re.compile(r"^\d+[\.\d]*[\.\s]")

_HEADING_CMDS = {
    1: "section",
    2: "subsection",
    3: "subsubsection",
    4: "paragraph",
    5: "subparagraph",
    6: "subparagraph",
}


class LaTeXRenderer(LaTeXBlockMixin):
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
        self._expanding_fn_refs: set[str] = set()  # circular expansion guard (循环展开守卫)
        self._heading_offset: int = 0  # set per-document in render_document (每文档计算)
        self.diag = diag

    @staticmethod
    def _compute_heading_offset(doc: Node) -> int:
        """Return offset so the shallowest heading maps to \\section (level 1).

        最浅标题级别对齐到 \\section 的偏移量（offset = min_level - 1）。
        """
        min_level: int = 99
        stack = list(doc.children)
        while stack:
            n = stack.pop()
            if isinstance(n, Heading):
                if n.level < min_level:
                    min_level = n.level
            stack.extend(n.children)
        if min_level == 99:
            return 0
        return min_level - 1  # e.g. min_level=2 → offset=1 → h2 renders as \section

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
        self._expanding_fn_refs.clear()  # Reset circular expansion guard (重置循环展开守卫)
        # Pre-scan: collect all FootnoteDef nodes (预扫描：收集所有脚注定义)
        self._collect_footnote_defs(node)
        # Auto-detect minimum heading level to normalize top level to \section.
        # (自动检测最小标题级别，确保最高层标题渲染为 \section)
        self._heading_offset = self._compute_heading_offset(node)
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

        # Locale overrides for figure/table caption names (本地化标题名覆盖)
        if self.locale == "en":
            lines.append("\\renewcommand{\\figurename}{Figure}")
            lines.append("\\renewcommand{\\tablename}{Table}")

        # bibliography_mode 决定是否输出参考文献相关命令
        # (bibliography_mode determines whether to emit bibliography commands)
        bib: str = str(meta.get("bibliography", "") or "")
        bib_mode: str = str(meta.get("bibliography_mode", "auto") or "auto")
        bib_active: bool = bib_mode in ("auto", "standalone")

        # extra preamble — emitted before title/author so \usepackage calls land in preamble
        # (额外 preamble 先于 title/author 输出，确保 \usepackage 等命令在导言区生效)
        if preamble := meta.get("preamble"):
            lines.append(str(preamble))

        # bibstyle — 仅在参考文献激活时输出 (Only emit when bibliography is active)
        if bib_active:
            if bibstyle := meta.get("bibstyle"):
                lines.append(f"\\bibliographystyle{{{bibstyle}}}")

        # title/author/date
        for key in ("title", "author", "date"):
            if val := meta.get(key):
                lines.append(f"\\{key}{{{val}}}")

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
        # Apply per-document offset so shallowest heading → \section
        # (应用偏移使最浅标题对齐 \section)
        effective_level = h.level - self._heading_offset
        cmd = _HEADING_CMDS.get(effective_level, "subparagraph")
        text = self.render_children(node)
        # If heading text already has a numeric prefix (e.g. "1. 引言"), use starred
        # command to suppress LaTeX auto-numbering — avoids double numbering.
        # (标题文本已含数字前缀时用星号命令，避免 LaTeX 自动编号与文本编号重叠)
        if _NUMBERED_HEADING_RE.match(text):
            cmd = f"{cmd}*"
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
            return f"\\begin{{equation}}\n{mb.content}\n\\label{{{label}}}\n\\end{{equation}}\n"
        return f"\\[\n{mb.content}\n\\]\n"

    # Normalize common markdown language names to listings-compatible identifiers.
    # (将常见 markdown 语言名映射到 listings 包可识别的语言标识符)
    _LISTINGS_LANG_MAP: dict[str, str] = {
        "cpp": "C++",
        "c++": "C++",
        "cxx": "C++",
        "c#": "C",
        "csharp": "C",
        "js": "Java",
        "javascript": "Java",
        "ts": "Java",
        "typescript": "Java",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "py": "Python",
        "rb": "Ruby",
        "rs": "C",
        "golang": "Go",
        "yml": "Python",
        "yaml": "Python",
    }

    def render_code_block(self, node: Node) -> str:
        """渲染代码块 (Render code block: lstlisting or minted)."""
        cb = cast(CodeBlock, node)
        if self.code_style == "minted":
            if cb.language:
                return f"\\begin{{minted}}{{{cb.language}}}\n{cb.content}\n\\end{{minted}}\n"
            # No language: fall back to verbatim (无语言：回退到 verbatim)
            return f"\\begin{{verbatim}}\n{cb.content}\n\\end{{verbatim}}\n"
        # Default: lstlisting (默认：lstlisting)
        if cb.language:
            # Normalize language identifier for listings compatibility (规范化语言标识符)
            lang = self._LISTINGS_LANG_MAP.get(cb.language.lower(), cb.language)
            return (
                f"\\begin{{lstlisting}}[language={lang}]\n"
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

    def render_thematic_break(self, node: Node) -> str:
        """渲染分隔线 (Render thematic break: newpage | hrule | ignore)."""
        if self.thematic_break == "hrule":
            return "\\hrule\n"
        if self.thematic_break == "ignore":
            return ""
        return "\\newpage\n"

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
        # Escape special chars to prevent LaTeX breakage/injection (转义特殊字符防止编译错误/注入)
        return f"\\texttt{{{escape_latex(ci.content)}}}"

    def render_math_inline(self, node: Node) -> str:
        mi = cast(MathInline, node)
        return f"${mi.content}$"

    def render_link(self, node: Node) -> str:
        lnk = cast(Link, node)
        text = self.render_children(node)
        # Escape URL special chars for LaTeX \href (转义 URL 特殊字符)
        return f"\\href{{{_escape_url_for_latex(lnk.url)}}}{{{text}}}"

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

        Uses _expanding_fn_refs to detect and break circular expansion.
        (使用 _expanding_fn_refs 检测并中断循环展开。)

        Args:
            node: FootnoteRef node (FootnoteRef 节点)

        Returns:
            \\footnote{content} or circular/unknown fallback (内联展开的脚注或回退标记)
        """
        fr = cast(FootnoteRef, node)
        fn_def = self._fn_defs.get(fr.ref_id)
        if fn_def is not None:
            # Guard: if already expanding this def, break the cycle (守卫：避免循环展开)
            if fr.ref_id in self._expanding_fn_refs:
                return f"\\footnote{{[circular:{fr.ref_id}]}}"
            self._expanding_fn_refs.add(fr.ref_id)
            try:
                content = self.render_children(fn_def).strip()
            finally:
                self._expanding_fn_refs.discard(fr.ref_id)
            return f"\\footnote{{{content}}}"
        # Fallback: unknown ref (回退：未知引用)
        return f"\\footnote{{[{fr.ref_id}]}}"

    def render_footnote_def(self, node: Node) -> str:
        """Skip — content already expanded at FootnoteRef site (跳过 — 内容已在引用处展开).

        Args:
            node: FootnoteDef node (FootnoteDef 节点)

        Returns:
            Empty string (空字符串)
        """
        return ""
