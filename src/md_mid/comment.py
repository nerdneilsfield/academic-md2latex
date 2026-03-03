"""Comment Processor：解析 EAST 中的 HTML 注释节点，执行指令收集、附着和环境构建。

四阶段处理（Four-phase processing）：
1. 收集文档级指令（头部区域）Collect document-level directives from header region
2. 处理 begin/end 对（环境 + raw）Process begin/end pairs into Environment/RawBlock
2.5. 处理 include-tex 指令（引入外部 TeX 文件）Process include-tex directives
3. 向上附着指令（label/caption/width 等 → 前一个兄弟节点）Attach-up directives
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import cast

from ruamel.yaml import YAML

from md_mid.diagnostic import DiagCollector, Position
from md_mid.nodes import (
    Document,
    Environment,
    Image,
    MathBlock,
    Node,
    Paragraph,
    RawBlock,
)

_yaml = YAML(typ="safe")

# <!-- key: value --> 模式 (Pattern for HTML comment directives)
_COMMENT_RE = re.compile(r"^<!--\s*(.*?)\s*-->$", re.DOTALL)

# 文档级指令（Document-level directives）
DOCUMENT_DIRECTIVES = frozenset(
    {
        "documentclass",
        "classoptions",
        "packages",
        "package-options",
        "bibliography",
        "bibstyle",
        "title",
        "author",
        "date",
        "abstract",
        "preamble",
        "latex-mode",
        "bibliography-mode",
    }
)

# 向上附着指令（Attach-up directives attached to previous sibling）
ATTACH_UP_DIRECTIVES = frozenset(
    {
        "label",
        "caption",
        "width",
        "placement",
        "centering",
        "options",
        "args",
        "ai-generated",
        "ai-model",
        "ai-prompt",
        "ai-negative-prompt",
        "ai-params",
    }
)

# 环境级指令（Environment-level directives collected into Environment.metadata）
ENV_DIRECTIVES = frozenset(
    {
        "options",
        "args",
        "centering",
        "placement",
        "label",
        "caption",
    }
)

# 所有已知指令键（All known directive keys, for unknown key detection）
_ALL_KNOWN_DIRECTIVES = (
    DOCUMENT_DIRECTIVES | ATTACH_UP_DIRECTIVES | frozenset({"begin", "end", "include-tex"})
)


def process_comments(
    doc: Document,
    filename: str,
    *,
    diag: DiagCollector | None = None,
) -> Document:
    """处理 EAST 中的 HTML 注释节点，返回增强后的 EAST。

    Process HTML comment nodes in EAST, return enhanced EAST.
    """
    if diag is None:
        diag = DiagCollector(filename)

    # Resolve source directory for include-tex path resolution (解析源目录用于 include-tex 路径解析)
    source_dir = Path(filename).parent if filename != "<stdin>" else Path(".")

    _collect_document_directives(doc, diag)
    _process_environments(doc, diag)
    _process_includes(doc.children, source_dir, diag)  # Phase 2.5: include-tex (引入处理)
    _process_attachments(doc, diag)

    return doc


def _parse_comment(node: Node) -> tuple[str, object] | None:
    """尝试从 RawBlock 中解析出 <!-- key: value --> 结构。

    Try to parse <!-- key: value --> structure from a RawBlock.
    返回 (key, parsed_value) 或 None（Returns (key, parsed_value) or None）.
    """
    if not isinstance(node, RawBlock):
        return None
    m = _COMMENT_RE.match(node.content.strip())
    if m is None:
        return None
    body = m.group(1).strip()
    if not body:
        return None

    # 尝试解析为 YAML key: value（Try to parse as YAML key: value）
    colon_pos = body.find(":")
    if colon_pos < 0:
        return None

    key = body[:colon_pos].strip()
    value_str = body[colon_pos + 1 :].strip()

    if not key:
        return None

    # 用 ruamel.yaml 解析值（Parse value with ruamel.yaml）
    try:
        value = _yaml.load(value_str)
    except Exception:
        value = value_str

    # 日期/数值归一化（Date/number normalization）：
    # date: 2024 → "2024", date: 2024-01-15 → "2024-01-15"
    if isinstance(value, (datetime.date, datetime.datetime)):
        value = str(value)
    elif isinstance(value, (int, float)) and key in ("date",):
        value = str(value)

    return key, value


def _normalize_key(key: str) -> str:
    """kebab-case → snake_case。"""
    return key.replace("-", "_")


def _collect_document_directives(doc: Document, diag: DiagCollector) -> None:
    """Phase 1: 收集头部区域的文档级指令。

    Phase 1: Collect document-level directives from the header region.
    头部区域定义为：第一个语义块（非注释节点）之前的区域。
    Header region: before the first non-comment node.
    重复指令触发 warning，正文中的文档指令触发 warning。
    Duplicate directives trigger warning; post-content doc directives trigger warning.
    """
    to_remove: list[int] = []
    header_ended = False
    seen_keys: set[str] = set()  # 追踪已见过的文档指令键（Track seen document directive keys）

    for i, child in enumerate(doc.children):
        parsed = _parse_comment(child)

        if parsed is None:
            if not header_ended:
                # 遇到非注释节点，头部区域结束（Non-comment node ends header region）
                header_ended = True
            continue

        key, value = parsed

        # 检查是否为 begin/end 指令（Check for begin/end directives）
        if key in ("begin", "end"):
            if not header_ended:
                header_ended = True
            continue

        if key not in DOCUMENT_DIRECTIVES:
            continue

        if header_ended:
            # 正文中出现文档级指令（Document directive found after content, ignored）
            diag.warning(
                f"Document directive '<!-- {key}: ... -->' found after content, ignored",
                _pos_from_node(child),
            )
            to_remove.append(i)  # remove leaked directive node (删除泄漏的指令节点)
            continue

        # 重复指令（Duplicate directive）
        if key in seen_keys:
            diag.warning(
                f"Duplicate document directive '<!-- {key}: ... -->', using first occurrence",
                _pos_from_node(child),
            )
            to_remove.append(i)
            continue

        seen_keys.add(key)
        nkey = _normalize_key(key)
        doc.metadata[nkey] = value
        to_remove.append(i)

    # 逆序删除已消费的注释节点（Remove consumed comment nodes in reverse order）
    for i in reversed(to_remove):
        doc.children.pop(i)


def _process_environments(doc: Document, diag: DiagCollector) -> None:
    """Phase 2: 处理 begin/end 对，将中间节点包裹为 Environment 或 RawBlock。

    Phase 2: Process begin/end pairs, wrapping inner nodes as Environment or RawBlock.
    """
    _process_environments_in(doc.children, diag)


def _process_environments_in(children: list[Node], diag: DiagCollector) -> None:
    """在一个子节点列表中查找并处理 begin/end 对。

    Find and process begin/end pairs in a children list.
    """
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
                    diag.error(
                        f"Unmatched <!-- begin: {env_name} -->",
                        _pos_from_node(child),
                    )
                    i += 1
                    continue

                # 提取 begin 和 end 之间的节点（Extract nodes between begin and end）
                inner = children[i + 1 : end_idx]

                # 替换为 Environment 或 RawBlock（Replace with Environment or RawBlock）
                if env_name == "raw":
                    # raw 环境：合并内容为纯文本（raw environment: merge content as plain text）
                    content = _extract_raw_content(inner)
                    new_node: Node = RawBlock(content=content, position=child.position)
                else:
                    env_node = Environment(
                        name=env_name,
                        children=inner,
                        position=child.position,
                    )
                    # 收集环境级指令（Collect environment-level directives into metadata）
                    _collect_env_directives(env_node, diag)
                    new_node = env_node

                # 替换 children[i:end_idx+1] 为 new_node（Replace slice with new_node）
                children[i : end_idx + 1] = [new_node]
                # 不递增 i，因为可能有嵌套（Don't increment i, may have nesting）
                continue

            elif key == "end":
                # 孤立的 end 指令（Orphan end directive without matching begin）
                env_name = str(value).strip()
                diag.error(
                    f"Orphan <!-- end: {env_name} --> without matching begin",
                    _pos_from_node(child),
                )
                i += 1
                continue

        # 递归处理子节点（Recursively process child nodes）
        if hasattr(child, "children") and child.children:
            _process_environments_in(child.children, diag)

        i += 1


def _collect_env_directives(env: Environment, diag: DiagCollector) -> None:
    """收集环境节点开头的环境级指令，移入 environment.metadata。

    Collect leading environment-level directives from env.children into env.metadata.
    遇到非指令节点时停止（Stops at first non-directive node）.
    """
    to_remove: list[int] = []
    for i, child in enumerate(env.children):
        parsed = _parse_comment(child)
        if parsed is None:
            # 遇到非指令节点，停止收集（Non-directive node stops collection）
            break

        key, value = parsed
        if key not in ENV_DIRECTIVES:
            # 非环境级指令，停止收集（Non-env-level directive stops collection）
            break

        nkey = _normalize_key(key)
        env.metadata[nkey] = value
        to_remove.append(i)

    for i in reversed(to_remove):
        env.children.pop(i)


def _find_matching_end(children: list[Node], start: int, env_name: str) -> int | None:
    """查找匹配的 <!-- end: env_name -->，支持嵌套同名环境。

    Find matching end directive with nesting support (嵌套感知的结束指令查找).
    使用深度计数器正确处理同名嵌套（Uses depth counter for same-name nesting）.
    """
    depth = 1  # 当前嵌套深度（Current nesting depth）
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
    """从节点列表中提取原始文本内容（Extract raw text content from node list）."""
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
    """从段落中提取文本内容（Extract text content from paragraph）."""
    parts: list[str] = []
    for child in para.children:
        if hasattr(child, "content"):
            parts.append(child.content)
        elif hasattr(child, "children"):
            for sub in child.children:
                if hasattr(sub, "content"):
                    parts.append(sub.content)
    return "".join(parts)


def _process_includes(
    children: list[Node],
    source_dir: Path,
    diag: DiagCollector,
) -> None:
    """处理 include-tex 指令，将注释节点替换为 RawBlock（Process include-tex directives）.

    Scans children list for include-tex directives and replaces each with a RawBlock
    containing the verbatim content of the referenced .tex file.
    Includes are one-level only — included content is not scanned for further
    include-tex directives. This prevents circular inclusion.
    (引入为单层 — 引入的内容不再扫描 include-tex，防止循环引入。)

    Args:
        children: Node list to scan (待扫描的节点列表)
        source_dir: Directory of source file for relative path resolution (源文件目录)
        diag: Diagnostic collector (诊断收集器)
    """
    i = 0
    while i < len(children):
        child = children[i]
        parsed = _parse_comment(child)
        if parsed is not None:
            key, value = parsed
            if key == "include-tex":
                tex_rel = str(value).strip()
                tex_path = (source_dir / tex_rel).resolve()
                # Security: path traversal check (安全：路径遍历检查)
                try:
                    tex_path.relative_to(source_dir.resolve())
                except ValueError:
                    diag.error(
                        f"include-tex path outside source directory"
                        f" (path traversal rejected): {tex_rel}",
                        _pos_from_node(child),
                    )
                    i += 1
                    continue
                if not tex_path.exists():
                    diag.error(
                        f"include-tex file not found: {tex_rel}",
                        _pos_from_node(child),
                    )
                    i += 1
                    continue
                # Read verbatim — no strip() (原样读取 — 不去空白)
                content = tex_path.read_text(encoding="utf-8")
                children[i] = RawBlock(content=content, position=child.position)
                i += 1
                continue
        i += 1


def _process_attachments(doc: Document, diag: DiagCollector) -> None:
    """Phase 3: 向上附着指令。

    Phase 3: Attach-up directives.
    遍历文档子节点列表，如果当前节点是注释且 key 属于 ATTACH_UP_DIRECTIVES，
    将其值附着到前一个兄弟节点的 metadata 中。
    If current node is a comment with key in ATTACH_UP_DIRECTIVES,
    attach its value to the previous sibling's metadata.
    """
    _process_attachments_in(doc.children, diag)


def _process_attachments_in(children: list[Node], diag: DiagCollector) -> None:
    """在子节点列表中处理向上附着（Process attach-up directives in children list）."""
    to_remove: list[int] = []

    for i, child in enumerate(children):
        parsed = _parse_comment(child)
        if parsed is None:
            # 递归处理（Recursively process child nodes）
            if hasattr(child, "children") and child.children:
                _process_attachments_in(child.children, diag)
            continue

        key, value = parsed
        nkey = _normalize_key(key)

        if key not in ATTACH_UP_DIRECTIVES:
            # 检查未知指令键（Check for unknown directive keys）
            if key not in _ALL_KNOWN_DIRECTIVES:
                diag.info(
                    f"Unknown directive key '<!-- {key}: ... -->'",
                    _pos_from_node(child),
                )
            continue

        # 找到前一个非注释兄弟（Find previous non-comment sibling）
        prev = _find_prev_sibling(children, i, to_remove)
        if prev is None:
            continue

        # ai-* 指令归入 ai 子字典（ai-* directives go into ai sub-dict）
        if key.startswith("ai-"):
            ai_key = _normalize_key(key[3:])  # ai-model → model
            if "ai" not in prev.metadata:
                prev.metadata["ai"] = {}
            ai_dict = cast(dict[str, object], prev.metadata["ai"])
            ai_dict[ai_key] = value
        else:
            prev.metadata[nkey] = value

        to_remove.append(i)

    for i in reversed(to_remove):
        children.pop(i)


def _find_prev_sibling(
    children: list[Node], current_idx: int, skip_indices: list[int]
) -> Node | None:
    """找到 current_idx 之前第一个非注释、非已删除的兄弟节点。

    Find the first non-comment, non-removed sibling before current_idx.
    只穿透包含单个 Image 或 MathBlock 子节点的 Paragraph。
    Only penetrates Paragraph containing a single Image or MathBlock child.
    """
    for j in range(current_idx - 1, -1, -1):
        if j in skip_indices:
            continue
        node = children[j]
        if not isinstance(node, RawBlock) or _parse_comment(node) is None:
            # 只穿透含单个 Image/MathBlock 的段落（Only penetrate para with Image/MathBlock）
            if isinstance(node, Paragraph) and len(node.children) == 1:
                child = node.children[0]
                if isinstance(child, (Image, MathBlock)):
                    return child
            return node
    return None


def _pos_from_node(node: Node) -> Position | None:
    """从节点提取 Position 对象（用于诊断）。

    Extract Position object from node (for diagnostics).
    """
    if node.position and isinstance(node.position, dict):
        start = node.position.get("start", {})
        if isinstance(start, dict):
            return Position(
                line=int(start.get("line", 0)),
                column=int(start.get("column", 1)),
            )
    return None
