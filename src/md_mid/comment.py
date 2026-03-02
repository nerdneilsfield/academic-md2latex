"""Comment Processor：解析 EAST 中的 HTML 注释节点，执行指令收集、附着和环境构建。

三阶段处理：
1. 收集文档级指令（头部区域）
2. 处理 begin/end 对（环境 + raw）
3. 向上附着指令（label/caption/width 等 → 前一个兄弟节点）
"""

from __future__ import annotations

import re

from ruamel.yaml import YAML

from md_mid.diagnostic import DiagCollector
from md_mid.nodes import (
    Document,
    Environment,
    Node,
    Paragraph,
    RawBlock,
)

_yaml = YAML()
_yaml.preserve_quotes = True

# <!-- key: value --> 模式
_COMMENT_RE = re.compile(r"^<!--\s*(.*?)\s*-->$", re.DOTALL)

# begin/end 指令
_BEGIN_RE = re.compile(r"^begin:\s*(.+)$")
_END_RE = re.compile(r"^end:\s*(.+)$")

# 文档级指令
DOCUMENT_DIRECTIVES = frozenset({
    "documentclass", "classoptions", "packages", "package-options",
    "bibliography", "bibstyle", "title", "author", "date", "abstract",
    "preamble", "latex-mode", "bibliography-mode",
})

# 向上附着指令
ATTACH_UP_DIRECTIVES = frozenset({
    "label", "caption", "width", "placement", "centering", "options", "args",
    "ai-generated", "ai-model", "ai-prompt", "ai-negative-prompt", "ai-params",
})


def process_comments(
    doc: Document,
    filename: str,
    *,
    diag: DiagCollector | None = None,
) -> Document:
    """处理 EAST 中的 HTML 注释节点，返回增强后的 EAST。"""
    if diag is None:
        diag = DiagCollector(filename)

    _collect_document_directives(doc, diag)
    _process_environments(doc, diag)
    _process_attachments(doc, diag)

    return doc


def _parse_comment(node: Node) -> tuple[str, object] | None:
    """尝试从 RawBlock 中解析出 <!-- key: value --> 结构。

    返回 (key, parsed_value) 或 None。
    """
    if not isinstance(node, RawBlock):
        return None
    m = _COMMENT_RE.match(node.content.strip())
    if m is None:
        return None
    body = m.group(1).strip()
    if not body:
        return None

    # 尝试解析为 YAML key: value
    colon_pos = body.find(":")
    if colon_pos < 0:
        return None

    key = body[:colon_pos].strip()
    value_str = body[colon_pos + 1:].strip()

    if not key:
        return None

    # 用 ruamel.yaml 解析值
    try:
        value = _yaml.load(value_str)
    except Exception:
        value = value_str

    return key, value


def _normalize_key(key: str) -> str:
    """kebab-case → snake_case。"""
    return key.replace("-", "_")


def _is_semantic_block(node: Node) -> bool:
    """判断节点是否为语义内容块（非注释）。"""
    if isinstance(node, RawBlock):
        return _parse_comment(node) is None
    return True


def _collect_document_directives(doc: Document, diag: DiagCollector) -> None:
    """Phase 1: 收集头部区域的文档级指令。

    头部区域定义为：第一个语义块（非注释节点）之前的区域。
    """
    to_remove: list[int] = []
    header_ended = False

    for i, child in enumerate(doc.children):
        if header_ended:
            break

        parsed = _parse_comment(child)
        if parsed is None:
            # 遇到非注释节点，头部区域结束
            header_ended = True
            continue

        key, value = parsed

        # 检查是否为 begin/end 指令
        if _BEGIN_RE.match(f"{key}: {value}" if isinstance(value, str) else key):
            header_ended = True
            continue
        if key in ("begin", "end"):
            header_ended = True
            continue

        if key in DOCUMENT_DIRECTIVES:
            nkey = _normalize_key(key)
            doc.metadata[nkey] = value
            to_remove.append(i)

    # 逆序删除已消费的注释节点
    for i in reversed(to_remove):
        doc.children.pop(i)


def _process_environments(doc: Document, diag: DiagCollector) -> None:
    """Phase 2: 处理 begin/end 对，将中间节点包裹为 Environment 或 RawBlock。"""
    _process_environments_in(doc.children, diag)


def _process_environments_in(children: list[Node], diag: DiagCollector) -> None:
    """在一个子节点列表中查找并处理 begin/end 对。"""
    i = 0
    while i < len(children):
        child = children[i]
        parsed = _parse_comment(child)
        if parsed is not None:
            key, value = parsed
            if key == "begin":
                env_name = str(value).strip()
                end_idx = _find_matching_end(children, i + 1, env_name)
                if end_idx is None:
                    pos = child.position
                    diag.error(
                        f"Unmatched <!-- begin: {env_name} -->",
                        _pos_from_node(child),
                    )
                    i += 1
                    continue

                # 提取 begin 和 end 之间的节点
                inner = children[i + 1:end_idx]

                # 替换为 Environment 或 RawBlock
                if env_name == "raw":
                    # raw 环境：合并内容为纯文本
                    content = _extract_raw_content(inner)
                    new_node = RawBlock(content=content, position=child.position)
                else:
                    new_node = Environment(
                        name=env_name,
                        children=inner,
                        position=child.position,
                    )

                # 替换 children[i:end_idx+1] 为 new_node
                children[i:end_idx + 1] = [new_node]
                # 不递增 i，因为可能有嵌套
                continue

        # 递归处理子节点
        if hasattr(child, "children") and child.children:
            _process_environments_in(child.children, diag)

        i += 1


def _find_matching_end(
    children: list[Node], start: int, env_name: str
) -> int | None:
    """查找匹配的 <!-- end: env_name -->。"""
    for j in range(start, len(children)):
        parsed = _parse_comment(children[j])
        if parsed is not None:
            key, value = parsed
            if key == "end" and str(value).strip() == env_name:
                return j
    return None


def _extract_raw_content(nodes: list[Node]) -> str:
    """从节点列表中提取原始文本内容。"""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, RawBlock):
            parts.append(node.content)
        elif isinstance(node, Paragraph):
            parts.append(_text_from_paragraph(node))
        elif hasattr(node, "content"):
            parts.append(node.content)
        elif hasattr(node, "children"):
            parts.append(_extract_raw_content(node.children))
    return "\n".join(parts)


def _text_from_paragraph(para: Paragraph) -> str:
    """从段落中提取文本内容。"""
    parts: list[str] = []
    for child in para.children:
        if hasattr(child, "content"):
            parts.append(child.content)
        elif hasattr(child, "children"):
            for sub in child.children:
                if hasattr(sub, "content"):
                    parts.append(sub.content)
    return "".join(parts)


def _process_attachments(doc: Document, diag: DiagCollector) -> None:
    """Phase 3: 向上附着指令。

    遍历文档子节点列表，如果当前节点是注释且 key 属于 ATTACH_UP_DIRECTIVES，
    将其值附着到前一个兄弟节点的 metadata 中。
    """
    _process_attachments_in(doc.children, diag)


def _process_attachments_in(children: list[Node], diag: DiagCollector) -> None:
    """在子节点列表中处理向上附着。"""
    to_remove: list[int] = []

    for i, child in enumerate(children):
        parsed = _parse_comment(child)
        if parsed is None:
            # 递归处理
            if hasattr(child, "children") and child.children:
                _process_attachments_in(child.children, diag)
            continue

        key, value = parsed
        nkey = _normalize_key(key)

        if key not in ATTACH_UP_DIRECTIVES:
            continue

        # 找到前一个非注释兄弟
        prev = _find_prev_sibling(children, i, to_remove)
        if prev is None:
            continue

        # ai-* 指令归入 ai 子字典
        if key.startswith("ai-"):
            ai_key = _normalize_key(key[3:])  # ai-model → model
            if "ai" not in prev.metadata:
                prev.metadata["ai"] = {}
            prev.metadata["ai"][ai_key] = value
        else:
            prev.metadata[nkey] = value

        to_remove.append(i)

    for i in reversed(to_remove):
        children.pop(i)


def _find_prev_sibling(
    children: list[Node], current_idx: int, skip_indices: list[int]
) -> Node | None:
    """找到 current_idx 之前第一个非注释、非已删除的兄弟节点。

    如果前一个兄弟是 Paragraph 且只包含一个子节点（如 Image），
    返回该子节点以便附着。
    """
    for j in range(current_idx - 1, -1, -1):
        if j in skip_indices:
            continue
        node = children[j]
        if not isinstance(node, RawBlock) or _parse_comment(node) is None:
            # 穿透单子节点段落
            if isinstance(node, Paragraph) and len(node.children) == 1:
                return node.children[0]
            return node
    return None


def _pos_from_node(node: Node):
    """从节点提取 Position 对象（用于诊断）。"""
    from md_mid.diagnostic import Position

    if node.position and isinstance(node.position, dict):
        start = node.position.get("start", {})
        return Position(line=start.get("line", 0), column=start.get("column", 1))
    return None
