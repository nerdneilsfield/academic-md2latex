"""Block-level LaTeX rendering: figures, tables, environments.

块级 LaTeX 渲染：图片、表格、环境。
Extracted from latex.py to keep modules under 500 lines.
(从 latex.py 提取以保持模块在 500 行以内。)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from wenqiao.nodes import (
    Environment,
    Figure,
    Image,
    Node,
    Paragraph,
    Table,
)

if TYPE_CHECKING:
    from wenqiao.diagnostic import DiagCollector


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

    def _render_caption_latex(self, caption: str) -> str:
        """Parse and render a caption string as LaTeX inline content.

        Captions may contain inline Markdown such as [text](ref:label) or
        [text](cite:key). This method parses them through the document parser
        and renders each inline node via self.render() so that cross-refs
        become \\ref{} and citations become \\cite{}.
        Falls back to the raw string if parsing fails or yields no paragraphs.
        (解析图注字符串，将 ref/cite 转换为 LaTeX 命令；解析失败时回退原文。)

        Args:
            caption: Raw caption text possibly containing inline markup (图注原文)

        Returns:
            LaTeX-rendered caption string (LaTeX 渲染后的图注文本)
        """
        cap = caption.strip()
        if not cap:
            return ""
        # Lazy import to avoid circular dependency (延迟导入以避免循环依赖)
        try:
            from wenqiao.parser import parse as _parse  # noqa: PLC0415

            doc = _parse(cap)
        except Exception:
            return cap
        parts: list[str] = []
        for block in doc.children:
            if not isinstance(block, Paragraph):
                continue
            piece = "".join(self.render(child) for child in block.children).strip()
            if piece:
                parts.append(piece)
        return " ".join(parts) if parts else cap

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
        height = str(meta.get("height", ""))
        caption = self._render_caption_latex(str(meta.get("caption", "")))
        label = str(meta.get("label", ""))

        lines = [f"\\begin{{figure}}[{placement}]"]
        lines.append("\\centering")

        # Build includegraphics options from width and/or height (构建 includegraphics 选项)
        gfx_parts: list[str] = []
        if width:
            gfx_parts.append(f"width={width}")
        if height:
            gfx_parts.append(f"height={height}")
        gfx_opts = ", ".join(gfx_parts)
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

    # Estimated text width in "average characters" (估算文本宽度，以平均字符数表示).
    # 10pt a4paper with 2cm margins ≈ 170mm ≈ 48em; at ~0.5em/char → ~96 chars.
    # Use 80 as conservative baseline (保守取 80 作为基准文本宽度字符数).
    _TABLE_TEXT_WIDTH_CHARS: int = 80
    # Minimum allowed scale factor — never go below this (最小允许缩放因子).
    _TABLE_MIN_SCALE: float = 0.55
    # Cell content length above which \makecell line-breaks are inserted.
    # (单元格内容超过此长度时插入 \makecell 换行)
    _TABLE_CELL_WRAP_CHARS: int = 48

    # Regex to strip LaTeX commands of the form \cmd{...} keeping only content,
    # and bare \cmd (no braces) entirely. Used before width estimation so that
    # commands like \ref{sec:intro} or \textbf{word} don't inflate column widths.
    # (去除 LaTeX 命令名以减少宽度估算误差：\ref{x}→x，\cmd 裸命令→删除)
    _LATEX_CMD_BRACED_RE = re.compile(r"\\[A-Za-z]+\{([^{}]*)\}")
    _LATEX_CMD_BARE_RE = re.compile(r"\\[A-Za-z]+\b\s*")

    @classmethod
    def _strip_latex_for_width(cls, text: str) -> str:
        """Strip LaTeX commands before display-width estimation.

        Replaces \\cmd{content} with content, removes bare \\cmd.
        Applied iteratively to handle nested commands (one level deep is usually
        sufficient for table cells).
        (去除 LaTeX 命令名，保留花括号内容，用于宽度估算)

        Args:
            text: LaTeX cell string (LaTeX 单元格文本)

        Returns:
            Stripped string approximating visible content (近似可见内容的字符串)
        """
        # Strip up to 3 levels of nesting (最多迭代 3 次处理嵌套)
        result = text
        for _ in range(3):
            stripped = cls._LATEX_CMD_BRACED_RE.sub(r"\1", result)
            stripped = cls._LATEX_CMD_BARE_RE.sub("", stripped)
            if stripped == result:
                break
            result = stripped
        return result

    @staticmethod
    def _display_width(text: str) -> int:
        """Count display width treating CJK characters as width 2.

        CJK fullwidth characters occupy ~2× the horizontal space of ASCII chars
        when typeset. This correction prevents under-estimating table width for
        Chinese content. (CJK 字符排版宽度约为 ASCII 的 2 倍，需修正以避免低估。)

        Args:
            text: Rendered cell string (已渲染字符串)

        Returns:
            Weighted character count (加权字符数)
        """
        width = 0
        for ch in text:
            cp = ord(ch)
            # CJK Unified Ideographs, CJK Extension, Kana, fullwidth ASCII,
            # CJK Compatibility, etc. (CJK 统一汉字、片假名、全角字符等)
            if (
                0x1100 <= cp <= 0x115F  # Hangul Jamo
                or 0x2E80 <= cp <= 0x2EFF  # CJK Radicals
                or 0x2F00 <= cp <= 0x2FDF  # Kangxi Radicals
                or 0x3000 <= cp <= 0x303F  # CJK Symbols and Punctuation
                or 0x3040 <= cp <= 0x309F  # Hiragana
                or 0x30A0 <= cp <= 0x30FF  # Katakana
                or 0x3400 <= cp <= 0x9FFF  # CJK Unified Ideographs (main)
                or 0xAC00 <= cp <= 0xD7AF  # Hangul Syllables
                or 0xF900 <= cp <= 0xFAFF  # CJK Compatibility
                or 0xFF01 <= cp <= 0xFF60  # Fullwidth ASCII
                or 0x20000 <= cp <= 0x2A6DF  # CJK Extension B
            ):
                width += 2
            else:
                width += 1
        return width

    def _estimate_table_width(self, tbl: Table) -> int:
        """Estimate table width by summing max display width per column.

        估算表格宽度：各列最大显示宽度（CJK 字符计 2）之和。
        CJK chars are weighted 2× to reflect actual typeset width.
        (CJK 字符权重为 2，以反映实际排版宽度。)

        Args:
            tbl: Table node (表格节点)

        Returns:
            Sum of per-column max display widths (各列最大显示宽度之和)
        """
        n_cols = len(tbl.headers)
        total = 0
        for i in range(n_cols):
            col_max = self._display_width(self._render_nodes(tbl.headers[i]))
            for row in tbl.rows:
                if i < len(row):
                    col_max = max(col_max, self._display_width(self._render_nodes(row[i])))
            total += col_max
        return total

    def render_table(self, node: Node) -> str:
        """Render Table node as LaTeX table environment (渲染 Table 节点).

        Wide tables have an explicit scale factor computed from the estimated
        column widths and wrapped in \\scalebox{factor}{...}.
        The factor is visible in the .tex output for manual tuning.
        (宽表格计算明确的缩放因子并套 \\scalebox{factor}，因子写入 .tex 便于手动微调。)
        """
        tbl = cast(Table, node)
        meta = node.metadata
        caption = self._render_caption_latex(str(meta.get("caption", "")))
        label = str(meta.get("label", ""))
        placement = str(meta.get("placement", "htbp"))

        # Column alignment spec — center is mapped to left because academic
        # text tables read better left-aligned; right is kept for numeric columns.
        # (列对齐格式：center 映射为 l，学术文本列居左更清晰；右对齐保留给数字列)
        align_map = {"left": "l", "right": "r", "center": "l"}
        n_cols = max(len(tbl.headers), 1)
        col_spec = "".join(align_map.get(a, "l") for a in tbl.alignments)
        if not col_spec:
            col_spec = "l" * n_cols

        # Dynamic wrap threshold: each column gets at most text_width // n_cols
        # display chars per line. This ensures that wrapping alone can absorb the
        # full page width, so \scalebox is only needed for residual overflow.
        # Minimum 16 chars to keep cells readable; fixed constant is the fallback
        # for narrow tables that don't need per-column tightening.
        # (动态换行阈值：按列数等分页宽，让换行而非 scalebox 控制整体宽度)
        per_col_wrap = max(16, self._TABLE_TEXT_WIDTH_CHARS // n_cols)
        cell_wrap = min(per_col_wrap, self._TABLE_CELL_WRAP_CHARS)

        # Step 1: Render and wrap all cells first so that the subsequent width
        # estimation reflects the actual line-broken content, not the raw text.
        # (先渲染并换行所有单元格，后续宽度估算基于换行后的实际内容)
        wrapped_headers = [
            self._wrap_cell(self._render_nodes(h), cell_wrap) for h in tbl.headers
        ]
        wrapped_rows = [
            [self._wrap_cell(self._render_nodes(cell), cell_wrap) for cell in row]
            for row in tbl.rows
        ]

        # Step 2: Estimate table width from wrapped cells.
        # Use _wrapped_cell_width so \makecell cells contribute only their
        # longest single line, not the full pre-wrap length.
        # (用换行后内容估算宽度：\makecell 单元格取最长单行)
        estimated_width = 0
        for i in range(n_cols):
            col_max = self._wrapped_cell_width(wrapped_headers[i])
            for wrow in wrapped_rows:
                if i < len(wrow):
                    col_max = max(col_max, self._wrapped_cell_width(wrow[i]))
            estimated_width += col_max

        # Step 3: Build the tabular body from pre-wrapped cells.
        # (用已换行的单元格构建 tabular 主体)
        tabular_lines: list[str] = [f"\\begin{{tabular}}{{{col_spec}}}"]
        tabular_lines.append("\\hline")
        tabular_lines.append(f"{' & '.join(wrapped_headers)} \\\\")
        tabular_lines.append("\\hline")
        for wrow in wrapped_rows:
            tabular_lines.append(f"{' & '.join(wrow)} \\\\")
        tabular_lines.append("\\hline")
        tabular_lines.append("\\end{tabular}")
        tabular_body = "\n".join(tabular_lines)

        # Step 4: Apply \scalebox if the wrapped table is still too wide.
        # scale = text_width_chars / estimated_width, clamped to [min, 1.0].
        # Factor is written into .tex for manual tuning.
        # (换行后仍过宽时套 \scalebox；因子写入 .tex 便于手动微调)
        if estimated_width > self._TABLE_TEXT_WIDTH_CHARS:
            raw_scale = self._TABLE_TEXT_WIDTH_CHARS / estimated_width
            scale = round(max(self._TABLE_MIN_SCALE, min(1.0, raw_scale)), 2)
            tabular_body = f"\\scalebox{{{scale}}}{{\n{tabular_body}\n}}"

        lines = [f"\\begin{{table}}[{placement}]"]
        lines.append("\\centering")
        if caption:
            lines.append(f"\\caption{{{caption}}}")
        if label:
            lines.append(f"\\label{{{label}}}")
        lines.append(tabular_body)
        lines.append("\\end{table}")
        return "\n".join(lines) + "\n"

    def _render_nodes(self, nodes: list[Node]) -> str:
        """Render a list of inline nodes (渲染行内节点列表)."""
        return "".join(self.render(n) for n in nodes)

    def _wrapped_cell_width(self, wrapped: str) -> int:
        """Return the max single-line display width of a (possibly wrapped) cell.

        For plain cells, returns _display_width(wrapped).
        For \\makecell[t]{line1\\\\\\\\line2\\\\\\\\...} cells produced by _wrap_cell,
        extracts the logical lines and returns the max display width among them.
        This reflects the actual column footprint after line-breaking.
        (返回 wrap 后单元格的最大单行宽度，\\makecell 单元格取各行最大值)

        Args:
            wrapped: Output of _wrap_cell (已 wrap 的单元格文本)

        Returns:
            Max single-line display width (最大单行显示宽度)
        """
        prefix = "\\makecell[lt]{"
        if not wrapped.startswith(prefix):
            return self._display_width(self._strip_latex_for_width(wrapped))
        # Extract content between outer braces (提取外层花括号内容)
        inner = wrapped[len(prefix) : -1]
        # Lines are separated by \\\\ (possibly followed by \n) (行由 \\\\ 分隔)
        logical_lines = inner.split("\\\\\n")
        return max(
            (self._display_width(self._strip_latex_for_width(ln)) for ln in logical_lines),
            default=0,
        )

    def _wrap_cell(self, text: str, threshold: int | None = None) -> str:
        """Wrap long table cell content with \\makecell line breaks.

        When cell text exceeds the threshold, split at word boundaries and wrap
        in \\makecell[lt]{line1\\\\line2\\\\...}.
        Only splits at spaces to avoid cutting LaTeX commands.
        (超过阈值时在词边界处拆分，用 \\makecell[lt] 包裹，避免切断 LaTeX 命令。)

        Args:
            text: Rendered cell content (已渲染的单元格内容)
            threshold: Display-width limit per line; defaults to _TABLE_CELL_WRAP_CHARS
                       (每行最大显示宽度；默认使用类常量)

        Returns:
            Original text, or \\makecell-wrapped multi-line version (原文或多行版本)
        """
        limit = threshold if threshold is not None else self._TABLE_CELL_WRAP_CHARS
        # Use stripped text for threshold check to avoid wrapping cells that only
        # look wide due to LaTeX command names (e.g. \ref{...}, \textbf{...}).
        # (用去命令后文本决定是否换行，避免命令名虚增宽度触发不必要的换行)
        if self._display_width(self._strip_latex_for_width(text)) <= limit:
            return text
        words = text.split(" ")
        lines: list[str] = []
        current: list[str] = []
        current_len = 0
        for word in words:
            # +1 for the space separator between words (词间空格)
            space_width = 1 if current else 0
            new_len = current_len + self._display_width(
                self._strip_latex_for_width(word)
            ) + space_width
            if new_len > limit and current:
                lines.append(" ".join(current))
                current = [word]
                current_len = self._display_width(self._strip_latex_for_width(word))
            else:
                current.append(word)
                current_len = self._display_width(self._strip_latex_for_width(word))
        if current:
            lines.append(" ".join(current))
        if len(lines) <= 1:
            return text  # single word longer than threshold — cannot split (无法拆分)
        # [lt] = left-horizontal + top-vertical; avoids the default center-
        # horizontal that makes shorter wrapped lines appear indented.
        # ([lt] = 左对齐+顶对齐；避免默认居中导致换行后短行看起来缩进)
        return "\\makecell[lt]{" + "\\\\\n".join(lines) + "}"

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
