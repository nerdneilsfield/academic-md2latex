"""Block-level LaTeX rendering: figures, tables, environments.

块级 LaTeX 渲染：图片、表格、环境。
Extracted from latex.py to keep modules under 500 lines.
(从 latex.py 提取以保持模块在 500 行以内。)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from md_mid.nodes import (
    Environment,
    Figure,
    Image,
    Node,
    Table,
)

if TYPE_CHECKING:
    from md_mid.diagnostic import DiagCollector


class LaTeXBlockMixin:
    """Block-level LaTeX rendering mixin (块级 LaTeX 渲染混入).

    Provides render methods for figures, images, tables, environments,
    and their helper functions. Mixed into LaTeXRenderer.
    (提供图片、表格、环境的渲染方法和辅助函数。混入 LaTeXRenderer。)
    """

    # These attributes are defined on LaTeXRenderer (由 LaTeXRenderer 定义)
    diag: DiagCollector | None

    def render(self, node: Node) -> str:
        """Render a node (由子类实现)."""
        return ""

    def render_children(self, node: Node) -> str:
        """Render children (由子类实现)."""
        return ""

    @staticmethod
    def _sanitize_comment(text: str) -> str:
        """Strip newlines to prevent LaTeX comment injection (去除换行防注入)."""
        return str(text).replace("\n", " ").replace("\r", "")

    def _render_ai_comments(self, ai: object) -> list[str]:
        """Emit % AI ... comments from ai metadata dict (输出 AI 元数据 LaTeX 注释).

        Args:
            ai: ai sub-dict from node.metadata (节点 metadata 的 ai 子字典)

        Returns:
            List of LaTeX comment lines (LaTeX 注释行列表)
        """
        if not isinstance(ai, dict):
            return []
        lines: list[str] = []
        model = ai.get("model")
        if model:
            lines.append(f"  % AI Generated: {self._sanitize_comment(str(model))}")
        prompt = ai.get("prompt")
        if prompt:
            truncated = self._sanitize_comment(str(prompt))[:120]
            lines.append(f"  % Prompt: {truncated}")
        neg = ai.get("negative_prompt")
        if neg:
            truncated_neg = self._sanitize_comment(str(neg))[:120]
            lines.append(f"  % Negative: {truncated_neg}")
        params = ai.get("params")
        if params:
            pairs = ", ".join(
                f"{self._sanitize_comment(str(k))}={self._sanitize_comment(str(v))}"
                for k, v in params.items()
            )
            lines.append(f"  % Params: {pairs}")
        return lines

    def _render_figure_env(self, src: str, meta: dict[str, object]) -> str:
        """Build \\begin{figure}...\\end{figure} block (构建 figure 环境块).

        Shared by render_figure and render_image promote path
        (render_figure 和 render_image 升级路径共用).

        Args:
            src: Image source path (图片源路径)
            meta: Node metadata dict (节点元数据字典)

        Returns:
            LaTeX figure environment string (LaTeX figure 环境字符串)
        """
        placement = str(meta.get("placement", "htbp"))
        width = str(meta.get("width", ""))
        caption = str(meta.get("caption", ""))
        label = str(meta.get("label", ""))

        lines = [f"\\begin{{figure}}[{placement}]"]
        lines.append("\\centering")

        gfx_opts = f"width={width}" if width else ""
        if gfx_opts:
            lines.append(f"\\includegraphics[{gfx_opts}]{{{src}}}")
        else:
            lines.append(f"\\includegraphics{{{src}}}")

        if caption:
            lines.append(f"\\caption{{{caption}}}")
        if label:
            lines.append(f"\\label{{{label}}}")

        # AI metadata comments before closing figure (AI 元数据注释在关闭图环境之前)
        lines.extend(self._render_ai_comments(meta.get("ai")))

        lines.append("\\end{figure}")
        return "\n".join(lines) + "\n"

    def render_figure(self, node: Node) -> str:
        """Render Figure node as LaTeX figure environment (渲染 Figure 节点)."""
        fig = cast(Figure, node)
        return self._render_figure_env(fig.src, node.metadata)

    def render_image(self, node: Node) -> str:
        """Render Image node — promote to figure if caption/label present (渲染 Image 节点).

        有 caption/label 时升级为 figure 环境。
        """
        img = cast(Image, node)
        meta = node.metadata
        if meta.get("caption") or meta.get("label"):
            return self._render_figure_env(img.src, meta)
        return f"\\includegraphics{{{img.src}}}"

    def render_table(self, node: Node) -> str:
        """Render Table node as LaTeX table environment (渲染 Table 节点)."""
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

        # Header row (表头行) — render inline nodes in each cell
        header_row = " & ".join(self._render_nodes(h) for h in tbl.headers)
        lines.append(f"{header_row} \\\\")
        lines.append("\\hline")

        # Data rows (数据行) — render inline nodes in each cell
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

    def render_environment(self, node: Node) -> str:
        r"""Render LaTeX environment with optional options and args.

        渲染 LaTeX 环境（含可选 options 和 args）。
        Builds the \\begin{name}[options]{arg1}{arg2}...\\end{name} block.

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
