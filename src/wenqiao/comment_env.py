"""Environment processing for comment processor.

注释处理器的环境处理模块。
Extracted from comment.py to keep modules under 500 lines.
(从 comment.py 提取以保持模块在 500 行以内。)
"""

from __future__ import annotations

from wenqiao.diagnostic import DiagCollector
from wenqiao.nodes import (
    Environment,
    HardBreak,
    MathBlock,
    MathInline,
    Node,
    Paragraph,
    RawBlock,
    SoftBreak,
)


def _process_environments(doc: Node, diag: DiagCollector) -> None:
    """Phase 2: Process begin/end pairs into Environment or RawBlock.

    Phase 2: 处理 begin/end 对，将中间节点包裹为 Environment 或 RawBlock。
    """
    _process_environments_in(doc.children, diag)


def _process_environments_in(children: list[Node], diag: DiagCollector) -> None:
    """Find and process begin/end pairs in a children list.

    在一个子节点列表中查找并处理 begin/end 对。
    Pre-scans for end directives to avoid O(n²) on orphan begins
    (预扫描 end 指令，避免孤立 begin 导致 O(n²) 扫描).
    """
    # Import here to avoid circular import at module level (函数级导入避免循环)
    from wenqiao.comment import _parse_comment, _pos_from_node

    # Pre-scan: collect env names that have end directives (预扫描有 end 指令的环境名)
    names_with_ends: set[str] = set()
    for child in children:
        parsed = _parse_comment(child)
        if parsed is not None and parsed[0] == "end":
            names_with_ends.add(str(parsed[1]).strip())

    i = 0
    while i < len(children):
        child = children[i]
        parsed = _parse_comment(child)
        if parsed is not None:
            key, value = parsed
            if key == "begin":
                env_name = str(value).strip()
                # Fast-reject orphan begins without scanning (快速排除无匹配 end 的孤立 begin)
                if env_name not in names_with_ends:
                    diag.error(
                        f"Unmatched <!-- begin: {env_name} -->",
                        _pos_from_node(child),
                    )
                    i += 1
                    continue
                end_idx = _find_matching_end(children, i + 1, env_name)
                if end_idx is None:
                    diag.error(
                        f"Unmatched <!-- begin: {env_name} -->",
                        _pos_from_node(child),
                    )
                    i += 1
                    continue

                # Extract nodes between begin and end (提取 begin 和 end 之间的节点)
                inner = children[i + 1 : end_idx]

                # Replace with Environment or RawBlock (替换为 Environment 或 RawBlock)
                if env_name == "raw":
                    # raw environment: merge content as plain text (raw 环境：合并内容为纯文本)
                    content = _extract_raw_content(inner)
                    new_node: Node = RawBlock(content=content, position=child.position)
                else:
                    env_node = Environment(
                        name=env_name,
                        children=inner,
                        position=child.position,
                    )
                    # Collect environment-level directives (收集环境级指令)
                    _collect_env_directives(env_node, diag)
                    new_node = env_node

                # Replace children[i:end_idx+1] with new_node (替换切片为新节点)
                children[i : end_idx + 1] = [new_node]
                # Don't increment i, may have nesting (不递增 i，可能有嵌套)
                continue

            elif key == "end":
                # Orphan end directive without matching begin (孤立的 end 指令)
                env_name = str(value).strip()
                diag.error(
                    f"Orphan <!-- end: {env_name} --> without matching begin",
                    _pos_from_node(child),
                )
                i += 1
                continue

        # Recursively process child nodes (递归处理子节点)
        if hasattr(child, "children") and child.children:
            _process_environments_in(child.children, diag)

        i += 1


def _collect_env_directives(env: Environment, diag: DiagCollector) -> None:
    """Collect leading environment-level directives into env.metadata.

    收集环境节点开头的环境级指令，移入 environment.metadata。
    Stops at first non-directive node (遇到非指令节点时停止).
    """
    from wenqiao.comment import ENV_DIRECTIVES, _normalize_key, _parse_comment

    to_remove: list[int] = []
    for i, child in enumerate(env.children):
        parsed = _parse_comment(child)
        if parsed is None:
            # Non-directive node stops collection (非指令节点停止收集)
            break

        key, value = parsed
        if key not in ENV_DIRECTIVES:
            # Non-env-level directive stops collection (非环境级指令停止收集)
            break

        nkey = _normalize_key(key)
        env.metadata[nkey] = value
        to_remove.append(i)

    for i in reversed(to_remove):
        env.children.pop(i)


def _find_matching_end(
    children: list[Node],
    start: int,
    env_name: str,
) -> int | None:
    """Find matching end directive with nesting support.

    查找匹配的 <!-- end: env_name -->，支持嵌套同名环境。
    Uses depth counter for same-name nesting (使用深度计数器正确处理同名嵌套).
    """
    from wenqiao.comment import _parse_comment

    depth = 1  # Current nesting depth (当前嵌套深度)
    for j in range(start, len(children)):
        parsed = _parse_comment(children[j])
        if parsed is None:
            continue
        key, value = parsed
        if key == "begin" and str(value).strip() == env_name:
            depth += 1
        elif key == "end" and str(value).strip() == env_name:
            depth -= 1
            if depth == 0:
                return j
    return None


def _extract_raw_content(nodes: list[Node]) -> str:
    """Extract raw text content from node list (从节点列表中提取原始文本内容)."""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, RawBlock):
            parts.append(node.content)
        elif isinstance(node, MathBlock):
            # Preserve display-math delimiters inside raw blocks.
            # (在 raw 块中保留行间数学的 $$ 定界符。)
            parts.append(f"$$\n{node.content}\n$$")
        elif isinstance(node, MathInline):
            # Preserve inline-math delimiters inside raw blocks.
            # (在 raw 块中保留行内数学的 $ 定界符。)
            parts.append(f"${node.content}$")
        elif isinstance(node, Paragraph):
            parts.append(_text_from_paragraph(node))
        elif hasattr(node, "content"):
            parts.append(node.content)
        elif hasattr(node, "children"):
            parts.append(_extract_raw_content(node.children))
    return "\n".join(parts)


def _text_from_paragraph(para: Paragraph) -> str:
    """Extract text content from paragraph, preserving line breaks for raw blocks.

    从段落中提取文本内容，为 raw 块保留换行。
    HardBreak → \\\\\n；SoftBreak 通常 → \n，但如果前一个文本片段以奇数个反斜杠结尾，
    说明 Markdown 转义吞掉了一个 LaTeX 行分隔符反斜杠，需要补回 \\ + \n。
    """
    parts: list[str] = []

    def _append_softbreak() -> None:
        """Append preserved soft break, restoring escaped LaTeX row separators.

        追加 SoftBreak，并在需要时恢复被 Markdown 转义吞掉的 LaTeX 行分隔符。
        """
        prev = parts[-1] if parts else ""
        trailing_backslashes = len(prev) - len(prev.rstrip("\\"))
        if trailing_backslashes % 2 == 1:
            # Restore the missing slash in a LaTeX row separator.
            # (恢复 LaTeX 行分隔符中被吞掉的那个反斜杠。)
            parts.append("\\\n")
        else:
            parts.append("\n")

    def _append_children(children: list[Node]) -> None:
        """Flatten paragraph descendants into raw text (将段落后代压平为原始文本)."""
        for child in children:
            if isinstance(child, HardBreak):
                # LaTeX row separator \\ followed by newline (LaTeX 行分隔符 \\\\ 加换行)
                parts.append("\\\\\n")
            elif isinstance(child, SoftBreak):
                _append_softbreak()
            elif isinstance(child, MathInline):
                # Preserve inline-math delimiters when flattening raw paragraphs.
                # (压平 raw 段落时保留行内数学的 $ 定界符。)
                parts.append(f"${child.content}$")
            elif hasattr(child, "content"):
                parts.append(child.content)
            elif hasattr(child, "children"):
                _append_children(child.children)

    _append_children(para.children)
    return "".join(parts)
