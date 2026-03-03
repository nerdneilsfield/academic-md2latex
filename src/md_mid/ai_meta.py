"""Shared AI metadata rendering utilities.

跨渲染器共享的 AI 元数据渲染工具。
"""

from __future__ import annotations

from collections.abc import Callable


def render_ai_details_html(
    ai: dict[str, object],
    esc: Callable[[str], str],
    *,
    summary: str = "AI Generation Info",
    indent: str = "  ",
) -> list[str]:
    """Render AI metadata as an HTML details/summary fold.

    将 AI 元数据渲染为 HTML details/summary 折叠块。

    Args:
        ai: AI metadata dict with model/prompt/negative_prompt/params keys
            (含 model/prompt/negative_prompt/params 键的 AI 元数据字典)
        esc: HTML escape function (HTML 转义函数)
        summary: Summary text for the details element (details 元素摘要文本)
        indent: Base indentation prefix (基础缩进前缀)

    Returns:
        List of HTML lines (HTML 行列表)
    """
    inner = indent + "  "
    lines = [
        f"{indent}<details>",
        f"{inner}<summary>{summary}</summary>",
    ]
    if model := ai.get("model"):
        lines.append(f"{inner}<p><strong>Model</strong>: {esc(str(model))}</p>")
    if prompt := ai.get("prompt"):
        lines.append(f"{inner}<p><strong>Prompt</strong>: {esc(str(prompt))}</p>")
    if neg := ai.get("negative_prompt"):
        lines.append(f"{inner}<p><strong>Negative</strong>: {esc(str(neg))}</p>")
    if params := ai.get("params"):
        lines.append(f"{inner}<p><strong>Params</strong>: {esc(str(params))}</p>")
    lines.append(f"{indent}</details>")
    return lines
