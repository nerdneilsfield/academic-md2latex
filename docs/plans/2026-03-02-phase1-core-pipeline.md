# Phase 1: 核心管线实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 建立 md-mid → EAST → LaTeX 的完整转换管线，覆盖论文写作最常见的正文结构、引用系统和多输出模式。

**Architecture:** 四阶段管线：markdown-it-py 解析 → AST 构建（token stream → EAST 节点树）→ Comment Processor 增强（注释消化、环境成型）→ LaTeX Renderer 输出。所有阶段通过 EAST（Enhanced AST）这一统一数据结构解耦。

**Tech Stack:** Python 3.14, markdown-it-py, mdit-py-plugins (dollarmath, footnote), ruamel.yaml, pytest, click

---

## 项目结构

```
src/md_mid/
  __init__.py          # 版本号 + 公共 API
  __main__.py          # python -m md_mid 入口
  cli.py               # CLI (click)
  parser.py            # markdown-it-py 初始化 + token → EAST 节点转换
  comment.py           # Comment Processor（注释解析、附着、环境/raw 处理）
  nodes.py             # EAST 节点类型定义（dataclasses）
  latex.py             # LaTeX Renderer
  escape.py            # LaTeX 特殊字符转义
  diagnostic.py        # 诊断系统（ERROR/WARNING/INFO）
tests/
  __init__.py
  conftest.py          # 共享 fixtures
  test_diagnostic.py
  test_nodes.py
  test_escape.py
  test_parser.py
  test_comment.py
  test_latex.py
  test_cli.py
  test_e2e.py
  fixtures/
    minimal.mid.md     # 最简输入
    heading_para.mid.md
    math.mid.md
    comments.mid.md
    cite_ref.mid.md
    full_example.mid.md  # PRD §13 完整示例
```

---

## Phase 1a: 核心管线

### Task 1: 项目脚手架

**Files:**
- Modify: `pyproject.toml`
- Create: `src/md_mid/__init__.py`
- Create: `src/md_mid/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: 更新 pyproject.toml**

```toml
[project]
name = "academic-md2latex"
version = "0.1.0"
description = "md-mid: 学术写作中间格式与多目标转换工具"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "markdown-it-py>=3.0",
    "mdit-py-plugins>=0.4",
    "ruamel.yaml>=0.18",
    "click>=8.0",
]

[project.scripts]
md-mid = "md_mid.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/md_mid"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]
```

**Step 2: 创建包骨架**

`src/md_mid/__init__.py`:
```python
"""md-mid: 学术写作中间格式与多目标转换工具"""

__version__ = "0.1.0"
```

`src/md_mid/__main__.py`:
```python
from md_mid.cli import main

main()
```

`tests/__init__.py`: 空文件

`tests/conftest.py`:
```python
"""共享 test fixtures"""
```

**Step 3: 安装依赖并验证**

Run: `cd /home/dengqi/Source/langs/python/academic-md2latex && uv sync`
Expected: 依赖安装成功

Run: `uv run python -c "import md_mid; print(md_mid.__version__)"`
Expected: `0.1.0`

**Step 4: 删除 hello.py**

删除占位文件 `hello.py`（已无用）。

**Step 5: Commit**

```bash
git add src/ tests/ pyproject.toml
git rm hello.py
git commit -m "feat: project scaffolding with dependencies and package structure"
```

---

### Task 2: 诊断系统

**Files:**
- Create: `src/md_mid/diagnostic.py`
- Create: `tests/test_diagnostic.py`

**Step 1: 写失败测试**

`tests/test_diagnostic.py`:
```python
from md_mid.diagnostic import Diagnostic, DiagLevel, Position


def test_create_warning():
    pos = Position(line=42, column=1)
    d = Diagnostic(DiagLevel.WARNING, "Unknown directive 'color'", "paper.mid.md", pos)
    assert d.level == DiagLevel.WARNING
    assert d.message == "Unknown directive 'color'"
    assert d.file == "paper.mid.md"
    assert d.position.line == 42


def test_format_warning():
    pos = Position(line=42, column=1)
    d = Diagnostic(DiagLevel.WARNING, "Unknown directive 'color'", "paper.mid.md", pos)
    assert str(d) == "[WARNING] paper.mid.md:42 - Unknown directive 'color'"


def test_format_error_no_position():
    d = Diagnostic(DiagLevel.ERROR, "File not found", "missing.md")
    assert str(d) == "[ERROR] missing.md - File not found"


def test_collector():
    from md_mid.diagnostic import DiagCollector

    dc = DiagCollector("test.md")
    dc.warning("bad thing", Position(line=1, column=1))
    dc.error("worse thing", Position(line=2, column=1))
    dc.info("fyi", Position(line=3, column=1))
    assert len(dc.diagnostics) == 3
    assert dc.has_errors is True
    assert len(dc.errors) == 1
    assert len(dc.warnings) == 1
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_diagnostic.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 实现 diagnostic.py**

`src/md_mid/diagnostic.py`:
```python
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class DiagLevel(enum.Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Position:
    line: int
    column: int = 1
    offset: int | None = None


@dataclass
class Diagnostic:
    level: DiagLevel
    message: str
    file: str
    position: Position | None = None

    def __str__(self) -> str:
        loc = f"{self.file}:{self.position.line}" if self.position else self.file
        return f"[{self.level.value}] {loc} - {self.message}"


class DiagCollector:
    def __init__(self, file: str) -> None:
        self.file = file
        self.diagnostics: list[Diagnostic] = []

    def _add(self, level: DiagLevel, message: str, position: Position | None = None) -> None:
        self.diagnostics.append(Diagnostic(level, message, self.file, position))

    def error(self, message: str, position: Position | None = None) -> None:
        self._add(DiagLevel.ERROR, message, position)

    def warning(self, message: str, position: Position | None = None) -> None:
        self._add(DiagLevel.WARNING, message, position)

    def info(self, message: str, position: Position | None = None) -> None:
        self._add(DiagLevel.INFO, message, position)

    @property
    def has_errors(self) -> bool:
        return any(d.level == DiagLevel.ERROR for d in self.diagnostics)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level == DiagLevel.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level == DiagLevel.WARNING]
```

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_diagnostic.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/diagnostic.py tests/test_diagnostic.py
git commit -m "feat: diagnostic system with error/warning/info levels"
```

---

### Task 3: EAST 节点定义

**Files:**
- Create: `src/md_mid/nodes.py`
- Create: `tests/test_nodes.py`

**Step 1: 写失败测试**

`tests/test_nodes.py`:
```python
from md_mid.nodes import (
    Node, Document, Heading, Paragraph, Text, Strong, Emphasis,
    CodeInline, CodeBlock, MathInline, MathBlock, Link, Image,
    SoftBreak, HardBreak, RawBlock, Environment, ThematicBreak,
    List, ListItem, Blockquote, Citation, CrossRef,
    FootnoteRef, FootnoteDef, Figure, Table,
)


def test_text_node():
    t = Text(content="hello")
    assert t.type == "text"
    assert t.content == "hello"
    assert t.children == []
    assert t.metadata == {}


def test_heading_with_metadata():
    h = Heading(level=2, children=[Text(content="Related Work")])
    h.metadata["label"] = "sec:related"
    assert h.type == "heading"
    assert h.level == 2
    assert len(h.children) == 1
    assert h.metadata["label"] == "sec:related"


def test_document_metadata():
    doc = Document(children=[])
    doc.metadata["title"] = "My Paper"
    doc.metadata["documentclass"] = "article"
    assert doc.type == "document"


def test_math_block():
    m = MathBlock(content="E = mc^2")
    assert m.type == "math_block"
    assert m.content == "E = mc^2"


def test_environment():
    env = Environment(
        name="algorithm",
        children=[Text(content="step 1")],
    )
    env.metadata["label"] = "alg:main"
    assert env.type == "environment"
    assert env.name == "algorithm"


def test_citation():
    c = Citation(keys=["wang2024", "li2023"], display_text="Wang et al.", cmd="cite")
    assert c.type == "citation"
    assert c.keys == ["wang2024", "li2023"]


def test_cross_ref():
    r = CrossRef(label="fig:result", display_text="图1")
    assert r.type == "cross_ref"
    assert r.label == "fig:result"


def test_figure():
    f = Figure(src="figs/a.png", alt="图A")
    f.metadata["caption"] = "示意图"
    f.metadata["label"] = "fig:a"
    assert f.type == "figure"
    assert f.src == "figs/a.png"


def test_table():
    t = Table(
        headers=["A", "B"],
        alignments=["left", "right"],
        rows=[["1", "2"]],
    )
    assert t.type == "table"
    assert len(t.rows) == 1
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_nodes.py -v`
Expected: FAIL

**Step 3: 实现 nodes.py**

`src/md_mid/nodes.py`:
```python
"""EAST (Enhanced AST) 节点类型定义。

所有节点均为 dataclass，字段说明见 PRD §11。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """所有 EAST 节点的基类。"""

    children: list[Node] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    position: dict | None = None  # {"start": {"line":, "column":}, "end": ...}

    @property
    def type(self) -> str:
        raise NotImplementedError


# ── 块级节点 ────────────────────────────────────────────────

@dataclass
class Document(Node):
    @property
    def type(self) -> str:
        return "document"


@dataclass
class Heading(Node):
    level: int = 1

    @property
    def type(self) -> str:
        return "heading"


@dataclass
class Paragraph(Node):
    @property
    def type(self) -> str:
        return "paragraph"


@dataclass
class Blockquote(Node):
    @property
    def type(self) -> str:
        return "blockquote"


@dataclass
class List(Node):
    ordered: bool = False
    start: int = 1

    @property
    def type(self) -> str:
        return "list"


@dataclass
class ListItem(Node):
    @property
    def type(self) -> str:
        return "list_item"


@dataclass
class CodeBlock(Node):
    content: str = ""
    language: str = ""

    @property
    def type(self) -> str:
        return "code_block"


@dataclass
class MathBlock(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "math_block"


@dataclass
class Figure(Node):
    src: str = ""
    alt: str = ""

    @property
    def type(self) -> str:
        return "figure"


@dataclass
class Table(Node):
    headers: list[str] = field(default_factory=list)
    alignments: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "table"


@dataclass
class Environment(Node):
    name: str = ""

    @property
    def type(self) -> str:
        return "environment"


@dataclass
class RawBlock(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "raw_block"


@dataclass
class ThematicBreak(Node):
    @property
    def type(self) -> str:
        return "thematic_break"


# ── 行内节点 ────────────────────────────────────────────────

@dataclass
class Text(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "text"


@dataclass
class Strong(Node):
    @property
    def type(self) -> str:
        return "strong"


@dataclass
class Emphasis(Node):
    @property
    def type(self) -> str:
        return "emphasis"


@dataclass
class CodeInline(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "code_inline"


@dataclass
class MathInline(Node):
    content: str = ""

    @property
    def type(self) -> str:
        return "math_inline"


@dataclass
class Link(Node):
    url: str = ""
    title: str = ""

    @property
    def type(self) -> str:
        return "link"


@dataclass
class Image(Node):
    src: str = ""
    alt: str = ""
    title: str = ""

    @property
    def type(self) -> str:
        return "image"


@dataclass
class Citation(Node):
    keys: list[str] = field(default_factory=list)
    display_text: str = ""
    cmd: str = "cite"

    @property
    def type(self) -> str:
        return "citation"


@dataclass
class CrossRef(Node):
    label: str = ""
    display_text: str = ""

    @property
    def type(self) -> str:
        return "cross_ref"


@dataclass
class FootnoteRef(Node):
    ref_id: str = ""

    @property
    def type(self) -> str:
        return "footnote_ref"


@dataclass
class FootnoteDef(Node):
    def_id: str = ""

    @property
    def type(self) -> str:
        return "footnote_def"


@dataclass
class SoftBreak(Node):
    @property
    def type(self) -> str:
        return "softbreak"


@dataclass
class HardBreak(Node):
    @property
    def type(self) -> str:
        return "hardbreak"
```

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_nodes.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/nodes.py tests/test_nodes.py
git commit -m "feat: EAST node type definitions"
```

---

### Task 4: LaTeX 特殊字符转义

**Files:**
- Create: `src/md_mid/escape.py`
- Create: `tests/test_escape.py`

**Step 1: 写失败测试**

`tests/test_escape.py`:
```python
from md_mid.escape import escape_latex, escape_latex_with_protection


class TestEscapeLaTeX:
    def test_no_special_chars(self):
        assert escape_latex("hello world") == "hello world"

    def test_hash(self):
        assert escape_latex("Section #1") == r"Section \#1"

    def test_percent(self):
        assert escape_latex("100%") == r"100\%"

    def test_ampersand(self):
        assert escape_latex("A & B") == r"A \& B"

    def test_underscore(self):
        assert escape_latex("my_var") == r"my\_var"

    def test_braces(self):
        assert escape_latex("{x}") == r"\{x\}"

    def test_tilde(self):
        assert escape_latex("~") == r"\textasciitilde{}"

    def test_caret(self):
        assert escape_latex("^") == r"\textasciicircum{}"

    def test_backslash(self):
        assert escape_latex("\\") == r"\textbackslash{}"

    def test_dollar(self):
        assert escape_latex("$10") == r"\$10"

    def test_multiple_specials(self):
        assert escape_latex("a & b # c") == r"a \& b \# c"

    def test_chinese_text_untouched(self):
        assert escape_latex("这是中文") == "这是中文"


class TestEscapeWithProtection:
    def test_protect_cite(self):
        result = escape_latex_with_protection(r"\cite{wang2024}")
        assert result == r"\cite{wang2024}"

    def test_protect_ref(self):
        result = escape_latex_with_protection(r"\ref{fig:x}")
        assert result == r"\ref{fig:x}"

    def test_protect_href(self):
        result = escape_latex_with_protection(r"\href{http://x.com}{link}")
        assert result == r"\href{http://x.com}{link}"

    def test_mixed_text_and_command(self):
        result = escape_latex_with_protection(r"see \cite{w2024} for 100% details")
        assert result == r"see \cite{w2024} for 100\% details"

    def test_command_with_options(self):
        result = escape_latex_with_protection(r"\usepackage[utf8]{inputenc}")
        assert result == r"\usepackage[utf8]{inputenc}"

    def test_textbf(self):
        result = escape_latex_with_protection(r"\textbf{bold}")
        assert result == r"\textbf{bold}"
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_escape.py -v`
Expected: FAIL

**Step 3: 实现 escape.py**

`src/md_mid/escape.py`:
```python
"""LaTeX 特殊字符转义。

两层策略：
1. escape_latex: 纯文本转义（逐字符替换）
2. escape_latex_with_protection: 先保护 LaTeX 命令，再转义剩余文本
"""

from __future__ import annotations

import re

LATEX_ESCAPE_MAP = {
    "#": r"\#",
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}

# 匹配 LaTeX 命令及其参数：\cmd, \cmd[opt]{arg}, \cmd{arg1}{arg2}
_CMD_RE = re.compile(
    r"\\[a-zA-Z@]+"          # \commandname
    r"(?:\s*\[[^\]]*\])*"    # 可选 [options] (可多个)
    r"(?:\s*\{[^{}]*\})*"    # 可选 {args} (可多个)
)


def escape_latex(text: str) -> str:
    """对纯文本片段做逐字符转义。"""
    out: list[str] = []
    for ch in text:
        out.append(LATEX_ESCAPE_MAP.get(ch, ch))
    return "".join(out)


def escape_latex_with_protection(text: str) -> str:
    """保护 LaTeX 命令后转义剩余文本（启发式模式）。"""
    protected: list[str] = []

    def _protect(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"\x00CMD{len(protected) - 1}\x00"

    text = _CMD_RE.sub(_protect, text)
    text = escape_latex(text)

    for i, seg in enumerate(protected):
        text = text.replace(f"\x00CMD{i}\x00", seg)

    return text
```

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_escape.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/escape.py tests/test_escape.py
git commit -m "feat: LaTeX special character escaping with command protection"
```

---

### Task 5: Parser（markdown-it-py 集成 + AST 构建）

**Files:**
- Create: `src/md_mid/parser.py`
- Create: `tests/test_parser.py`
- Create: `tests/fixtures/minimal.mid.md`

此 Task 负责将 markdown-it-py 的 token stream / SyntaxTreeNode 转换为 EAST 节点树。**不含**注释处理逻辑（那是 Comment Processor 的职责）。

HTML 注释节点在此阶段保留为特殊的 `HtmlComment` 临时节点（或直接保留 raw text），供 Comment Processor 后续消费。

**Step 1: 创建 fixture 文件**

`tests/fixtures/minimal.mid.md`:
```markdown
# Hello World

This is a **bold** and *italic* paragraph.

Inline math: $E=mc^2$

$$
\int_0^\infty f(x) dx
$$

- item 1
- item 2

> a quote

`inline code`
```

**Step 2: 写失败测试**

`tests/test_parser.py`:
```python
from pathlib import Path

from md_mid.nodes import (
    Document, Heading, Paragraph, Text, Strong, Emphasis,
    MathInline, MathBlock, List, ListItem, Blockquote,
    CodeInline, SoftBreak,
)
from md_mid.parser import parse

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_returns_document():
    doc = parse("# Hello")
    assert isinstance(doc, Document)


def test_heading():
    doc = parse("# Hello World")
    assert len(doc.children) == 1
    h = doc.children[0]
    assert isinstance(h, Heading)
    assert h.level == 1
    texts = [c for c in h.children if isinstance(c, Text)]
    assert any("Hello World" in t.content for t in texts)


def test_paragraph_with_inline():
    doc = parse("This is **bold** and *italic*.")
    para = doc.children[0]
    assert isinstance(para, Paragraph)
    # 段落应包含 Text, Strong, Text, Emphasis, Text
    types = [type(c).__name__ for c in para.children]
    assert "Strong" in types
    assert "Emphasis" in types


def test_math_inline():
    doc = parse("Hello $E=mc^2$ world")
    para = doc.children[0]
    math_nodes = [c for c in para.children if isinstance(c, MathInline)]
    assert len(math_nodes) == 1
    assert math_nodes[0].content == "E=mc^2"


def test_math_block():
    doc = parse("$$\n\\int_0^\\infty f(x) dx\n$$")
    math_nodes = [c for c in doc.children if isinstance(c, MathBlock)]
    assert len(math_nodes) == 1
    assert "\\int" in math_nodes[0].content


def test_unordered_list():
    doc = parse("- a\n- b\n")
    lst = doc.children[0]
    assert isinstance(lst, List)
    assert lst.ordered is False
    assert len(lst.children) == 2
    assert all(isinstance(c, ListItem) for c in lst.children)


def test_blockquote():
    doc = parse("> hello\n")
    bq = doc.children[0]
    assert isinstance(bq, Blockquote)


def test_code_inline():
    doc = parse("use `printf`")
    para = doc.children[0]
    codes = [c for c in para.children if isinstance(c, CodeInline)]
    assert len(codes) == 1
    assert codes[0].content == "printf"


def test_fixture_minimal(tmp_path):
    text = (FIXTURES / "minimal.mid.md").read_text()
    doc = parse(text)
    assert isinstance(doc, Document)
    # 应至少有: heading, paragraph, math_block, list, blockquote
    types = {type(c).__name__ for c in doc.children}
    assert "Heading" in types
    assert "Paragraph" in types
    assert "MathBlock" in types
    assert "List" in types
    assert "Blockquote" in types
```

**Step 3: 运行测试确认失败**

Run: `uv run pytest tests/test_parser.py -v`
Expected: FAIL

**Step 4: 实现 parser.py**

`src/md_mid/parser.py`:

核心逻辑：
1. 用 markdown-it-py（commonmark preset + html + table + dollarmath + footnote）解析文本
2. 用 `SyntaxTreeNode` 折叠 token stream 为树
3. 递归遍历树，将每个 `SyntaxTreeNode` 转换为对应的 EAST `Node`

关键映射表：
```python
_BLOCK_MAP = {
    "heading":      _build_heading,
    "paragraph":    _build_paragraph,
    "blockquote":   _build_blockquote,
    "bullet_list":  lambda n: _build_list(n, ordered=False),
    "ordered_list": lambda n: _build_list(n, ordered=True),
    "list_item":    _build_list_item,
    "fence":        _build_code_block,
    "code_block":   _build_code_block,
    "math_block":   _build_math_block,
    "math_block_eqno": _build_math_block,
    "hr":           lambda n: ThematicBreak(),
    "html_block":   _build_html_block,    # 暂时保留为 RawBlock，供 Comment Processor 识别
    "table":        _build_table,
}

_INLINE_MAP = {
    "text":         lambda n: Text(content=n.content or ""),
    "code_inline":  lambda n: CodeInline(content=n.content or ""),
    "math_inline":  lambda n: MathInline(content=n.content or ""),
    "softbreak":    lambda n: SoftBreak(),
    "hardbreak":    lambda n: HardBreak(),
    "em":           _build_emphasis,
    "strong":       _build_strong,
    "link":         _build_link,
    "image":        _build_image,
    "html_inline":  _build_html_inline,
}
```

`parse(text: str) -> Document` 为公共入口，内部调用 `_build_node(syntax_tree_node)` 递归构建。

对于 `inline` 类型的中间节点（markdown-it-py 在块级节点和实际行内内容之间插入的），直接提升其子节点。

Position 信息从 `token.map` 提取（block token 有 `[start_line, end_line]`，1-based 输出）。

**Step 5: 运行测试确认通过**

Run: `uv run pytest tests/test_parser.py -v`
Expected: 全部 PASS

**Step 6: Commit**

```bash
git add src/md_mid/parser.py tests/test_parser.py tests/fixtures/
git commit -m "feat: markdown-it-py parser with EAST node conversion"
```

---

### Task 6: Comment Processor

**Files:**
- Create: `src/md_mid/comment.py`
- Create: `tests/test_comment.py`
- Create: `tests/fixtures/comments.mid.md`

Comment Processor 接收 `parse()` 的输出（含原始 HTML 注释节点），执行：
1. YAML 注释解析
2. 文档级指令收集（头部区域）
3. 向上附着（label/caption/width 等）
4. begin/end 环境包裹
5. begin/end raw 合并为 RawBlock

**Step 1: 创建 fixture**

`tests/fixtures/comments.mid.md`:
```markdown
<!-- title: My Paper -->
<!-- packages: [amsmath, graphicx] -->

# Introduction
<!-- label: sec:intro -->

A paragraph.

![figure](fig.png)
<!-- caption: My Figure -->
<!-- label: fig:a -->
<!-- width: 0.8\textwidth -->

<!-- begin: algorithm -->
Step 1
<!-- end: algorithm -->

<!-- begin: raw -->
\newcommand{\myop}{\operatorname}
<!-- end: raw -->
```

**Step 2: 写失败测试**

`tests/test_comment.py`:
```python
from md_mid.parser import parse
from md_mid.comment import process_comments
from md_mid.nodes import (
    Document, Heading, Paragraph, Figure, Environment, RawBlock, Image,
)


def test_document_level_directives():
    doc = parse("<!-- title: My Paper -->\n<!-- packages: [amsmath] -->\n\n# Intro\n")
    east = process_comments(doc, "test.md")
    assert east.metadata.get("title") == "My Paper"
    assert east.metadata.get("packages") == ["amsmath"]


def test_label_attaches_to_heading():
    doc = parse("# Introduction\n<!-- label: sec:intro -->\n")
    east = process_comments(doc, "test.md")
    h = east.children[0]
    assert isinstance(h, Heading)
    assert h.metadata.get("label") == "sec:intro"


def test_caption_label_attach_to_image():
    text = "![fig](a.png)\n<!-- caption: My Fig -->\n<!-- label: fig:a -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    # Image 应被提升为 Figure（或 Image 节点获得 metadata）
    fig = east.children[0]
    # 穿透 paragraph → image
    if isinstance(fig, Paragraph) and len(fig.children) == 1:
        fig = fig.children[0]
    assert fig.metadata.get("caption") == "My Fig"
    assert fig.metadata.get("label") == "fig:a"


def test_begin_end_creates_environment():
    text = "<!-- begin: algorithm -->\nStep 1\n<!-- end: algorithm -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    envs = [c for c in east.children if isinstance(c, Environment)]
    assert len(envs) == 1
    assert envs[0].name == "algorithm"


def test_begin_end_raw_creates_raw_block():
    text = '<!-- begin: raw -->\n\\newcommand{\\myop}{\\operatorname}\n<!-- end: raw -->\n'
    doc = parse(text)
    east = process_comments(doc, "test.md")
    raws = [c for c in east.children if isinstance(c, RawBlock)]
    assert len(raws) == 1
    assert "\\newcommand" in raws[0].content


def test_document_directive_after_content_ignored():
    text = "# Intro\n<!-- title: Late Title -->\n"
    doc = parse(text)
    east = process_comments(doc, "test.md")
    # title 不应被收集（已进入正文）
    assert "title" not in east.metadata


def test_unmatched_begin_raises():
    text = "<!-- begin: algorithm -->\nStep 1\n"
    doc = parse(text)
    from md_mid.diagnostic import DiagCollector
    dc = DiagCollector("test.md")
    east = process_comments(doc, "test.md", diag=dc)
    assert dc.has_errors
```

**Step 3: 运行测试确认失败**

Run: `uv run pytest tests/test_comment.py -v`
Expected: FAIL

**Step 4: 实现 comment.py**

`src/md_mid/comment.py`:

核心流程（PRD §6.2 的算法描述）：

```python
def process_comments(doc: Document, filename: str, *, diag: DiagCollector | None = None) -> Document:
    """处理 EAST 中的 HTML 注释节点，返回增强后的 EAST。"""
    if diag is None:
        diag = DiagCollector(filename)

    # Phase 1: 收集文档级指令（头部区域）
    _collect_document_directives(doc, diag)

    # Phase 2: 处理 begin/end（环境 + raw），从内到外
    _process_environments(doc, diag)

    # Phase 3: 处理向上附着指令
    _process_attachments(doc, diag)

    return doc
```

关键实现细节：
- 识别 HTML 注释：检查 `RawBlock`/`HtmlInline` 节点内容是否匹配 `<!-- ... -->` 模式
- YAML 解析：使用 `ruamel.yaml` 解析注释体
- 文档级指令列表：`DOCUMENT_DIRECTIVES = {"documentclass", "classoptions", "packages", "package-options", "bibliography", "bibstyle", "title", "author", "date", "abstract", "preamble", "latex-mode", "bibliography-mode"}`
- 向上附着指令列表：`ATTACH_UP_DIRECTIVES = {"label", "caption", "width", "placement", "centering", "options", "args", "ai-generated", "ai-model", "ai-prompt", "ai-negative-prompt", "ai-params"}`
- key 归一化：`kebab-case` → `snake_case`（如 `ai-negative-prompt` → `ai_negative_prompt`）
- `ai-*` 前缀指令归入 `metadata["ai"]` 子字典

**Step 5: 运行测试确认通过**

Run: `uv run pytest tests/test_comment.py -v`
Expected: 全部 PASS

**Step 6: Commit**

```bash
git add src/md_mid/comment.py tests/test_comment.py tests/fixtures/comments.mid.md
git commit -m "feat: Comment Processor with YAML parsing, attachment, and environment handling"
```

---

### Task 7: LaTeX Renderer（最小节点集）

**Files:**
- Create: `src/md_mid/latex.py`
- Create: `tests/test_latex.py`

本 Task 实现 PRD §7 的渲染器分发表，覆盖 Phase 1a 的最小节点集。输出模式暂时只实现 `full`（Phase 1b 补充 body/fragment）。

**Step 1: 写失败测试**

`tests/test_latex.py`:
```python
from md_mid.nodes import (
    Document, Heading, Paragraph, Text, Strong, Emphasis,
    CodeInline, CodeBlock, MathInline, MathBlock, Link, Image,
    SoftBreak, HardBreak, RawBlock, List, ListItem, Blockquote,
    ThematicBreak, Environment,
)
from md_mid.latex import LaTeXRenderer


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
        lst = List(ordered=False, children=[
            ListItem(children=[Paragraph(children=[Text(content="a")])]),
            ListItem(children=[Paragraph(children=[Text(content="b")])]),
        ])
        result = render(lst)
        assert "\\begin{itemize}" in result
        assert "\\item" in result

    def test_ordered_list(self):
        lst = List(ordered=True, children=[
            ListItem(children=[Paragraph(children=[Text(content="a")])]),
        ])
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
        env = Environment(name="theorem", children=[
            Paragraph(children=[Text(content="proof here")])
        ])
        result = render(env)
        assert "\\begin{theorem}" in result
        assert "\\end{theorem}" in result

    def test_thematic_break_default_newpage(self):
        result = render(ThematicBreak())
        assert "\\newpage" in result
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_latex.py -v`
Expected: FAIL

**Step 3: 实现 latex.py**

`src/md_mid/latex.py`:

核心结构：
```python
class LaTeXRenderer:
    def __init__(self, mode: str = "full") -> None:
        self.mode = mode

    def render(self, node: Node) -> str:
        method_name = f"render_{node.type}"
        method = getattr(self, method_name, None)
        if method is None:
            return self.render_children(node)
        return method(node)

    def render_children(self, node: Node) -> str:
        return "".join(self.render(child) for child in node.children)
```

每个 `render_*` 方法对照 PRD §7.1 的分发表实现。

- `render_text`: 调用 `escape_latex_with_protection(node.content)`
- `render_math_inline/math_block`: 内容不转义（绝对豁免区）
- `render_code_inline/code_block`: 不走普通转义
- `render_heading`: 按 level 映射到 `\section` ~ `\paragraph`，有 label 则追加 `\label{}`
- `render_figure`: `\begin{figure}` 环境（含 `\centering`, `\includegraphics`, `\caption`, `\label`）
- `render_environment`: 通用 `\begin{name}[options]{args}...\end{name}`

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_latex.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/latex.py tests/test_latex.py
git commit -m "feat: LaTeX Renderer with minimal node set"
```

---

### Task 8: CLI 骨架

**Files:**
- Create: `src/md_mid/cli.py`
- Create: `tests/test_cli.py`

**Step 1: 写失败测试**

`tests/test_cli.py`:
```python
from click.testing import CliRunner
from md_mid.cli import main


def test_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "md-mid" in result.output or "input" in result.output.lower()


def test_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_convert_minimal(tmp_path):
    src = tmp_path / "test.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "test.tex"
    result = CliRunner().invoke(main, [str(src), "-o", str(out)])
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\section{Hello}" in content
    assert "World." in content
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL

**Step 3: 实现 cli.py**

`src/md_mid/cli.py`:
```python
"""md-mid CLI 入口。"""

from __future__ import annotations

from pathlib import Path

import click

from md_mid import __version__
from md_mid.parser import parse
from md_mid.comment import process_comments
from md_mid.latex import LaTeXRenderer


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option("-t", "--target", type=click.Choice(["latex", "markdown", "html"]), default="latex")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None)
@click.option("--mode", type=click.Choice(["full", "body", "fragment"]), default="full")
@click.option("--strict", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--dump-east", is_flag=True, default=False)
@click.version_option(version=__version__)
def main(input: Path, target: str, output: Path | None, mode: str, strict: bool, verbose: bool, dump_east: bool) -> None:
    """md-mid: 学术写作中间格式转换工具"""
    text = input.read_text(encoding="utf-8")
    doc = parse(text)
    east = process_comments(doc, str(input))

    if target == "latex":
        renderer = LaTeXRenderer(mode=mode)
        result = renderer.render(east)
    else:
        click.echo(f"Target '{target}' not yet implemented.", err=True)
        raise SystemExit(1)

    if output is None:
        output = input.with_suffix(".tex" if target == "latex" else f".{target}")

    output.write_text(result, encoding="utf-8")
    click.echo(f"Written to {output}")
```

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/cli.py src/md_mid/__main__.py tests/test_cli.py
git commit -m "feat: CLI skeleton with click"
```

---

### Task 9: Phase 1a E2E 冒烟测试

**Files:**
- Create: `tests/fixtures/heading_para.mid.md`
- Create: `tests/fixtures/math.mid.md`
- Create: `tests/test_e2e.py`

**Step 1: 创建 fixtures**

`tests/fixtures/heading_para.mid.md`:
```markdown
# Introduction
<!-- label: sec:intro -->

This is a paragraph with **bold** and *italic*.

## Background

Some text with $x^2$ inline math.

$$
E = mc^2
$$
<!-- label: eq:einstein -->
```

`tests/fixtures/math.mid.md`:
```markdown
Inline: $a + b = c$

Block:

$$
\sum_{i=1}^{n} x_i = S
$$

$$
\int_0^1 f(x) dx
$$
<!-- label: eq:integral -->
```

**Step 2: 写 E2E 测试**

`tests/test_e2e.py`:
```python
"""端到端集成测试：md-mid source → LaTeX output"""

from pathlib import Path

from md_mid.parser import parse
from md_mid.comment import process_comments
from md_mid.latex import LaTeXRenderer

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
```

**Step 3: 运行测试**

Run: `uv run pytest tests/test_e2e.py -v`
Expected: 全部 PASS

**Step 4: Commit**

```bash
git add tests/test_e2e.py tests/fixtures/heading_para.mid.md tests/fixtures/math.mid.md
git commit -m "test: Phase 1a E2E smoke tests"
```

---

## Phase 1b: 引用与输出模式

### Task 10: Citation 与 CrossRef 解析

**Files:**
- Modify: `src/md_mid/parser.py` — `_build_link` 中识别 `cite:`/`ref:` 前缀
- Modify: `tests/test_parser.py` — 补充 cite/ref 测试

`cite:` 和 `ref:` 的识别在 Parser 层完成（不在 Comment Processor 中），因为它们是 Markdown 链接语法的变体。

**Step 1: 写失败测试**

追加到 `tests/test_parser.py`:
```python
from md_mid.nodes import Citation, CrossRef


def test_cite_single():
    doc = parse("[Wang et al.](cite:wang2024)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].keys == ["wang2024"]
    assert cites[0].display_text == "Wang et al."


def test_cite_multiple_keys():
    doc = parse("[1-3](cite:wang2024,li2023,zhang2025)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].keys == ["wang2024", "li2023", "zhang2025"]


def test_cite_empty_display():
    doc = parse("[](cite:wang2024)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].display_text == ""


def test_cite_with_cmd():
    doc = parse("[Wang](cite:wang2024?cmd=citeauthor)")
    para = doc.children[0]
    cites = [c for c in para.children if isinstance(c, Citation)]
    assert len(cites) == 1
    assert cites[0].cmd == "citeauthor"


def test_ref():
    doc = parse("[图1](ref:fig:result)")
    para = doc.children[0]
    refs = [c for c in para.children if isinstance(c, CrossRef)]
    assert len(refs) == 1
    assert refs[0].label == "fig:result"
    assert refs[0].display_text == "图1"


def test_regular_link_not_converted():
    doc = parse("[click](http://example.com)")
    para = doc.children[0]
    from md_mid.nodes import Link
    links = [c for c in para.children if isinstance(c, Link)]
    assert len(links) == 1
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_parser.py -v -k "cite or ref or regular_link"`
Expected: FAIL

**Step 3: 修改 parser.py 的 `_build_link`**

在 `_build_link` 中，根据 URL 前缀分流：
- `cite:` → 创建 `Citation` 节点（解析逗号分隔的 keys，解析 `?cmd=` 参数）
- `ref:` → 创建 `CrossRef` 节点
- 其他 → 创建 `Link` 节点

```python
def _build_link(node: SyntaxTreeNode) -> Node:
    url = node.attrGet("href") or ""
    children = _build_inline_children(node)
    display_text = _extract_text(children)

    if url.startswith("cite:"):
        raw = url[5:]  # 去掉 "cite:"
        cmd = "cite"
        if "?cmd=" in raw:
            raw, cmd = raw.split("?cmd=", 1)
        keys = [k.strip() for k in raw.split(",")]
        return Citation(keys=keys, display_text=display_text, cmd=cmd)

    if url.startswith("ref:"):
        label = url[4:]
        return CrossRef(label=label, display_text=display_text)

    return Link(url=url, children=children)
```

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_parser.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/parser.py tests/test_parser.py
git commit -m "feat: cite/ref link parsing into Citation and CrossRef nodes"
```

---

### Task 11: Citation 与 CrossRef LaTeX 渲染

**Files:**
- Modify: `src/md_mid/latex.py` — 添加 `render_citation` 和 `render_cross_ref`
- Modify: `tests/test_latex.py` — 补充测试

**Step 1: 写失败测试**

追加到 `tests/test_latex.py`:
```python
from md_mid.nodes import Citation, CrossRef


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
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_latex.py::TestCiteRef -v`
Expected: FAIL

**Step 3: 实现渲染方法**

在 `LaTeXRenderer` 中添加：

```python
def __init__(self, mode: str = "full", ref_tilde: bool = True) -> None:
    self.mode = mode
    self.ref_tilde = ref_tilde

def render_citation(self, node: Citation) -> str:
    keys = ",".join(node.keys)
    return f"\\{node.cmd}{{{keys}}}"

def render_cross_ref(self, node: CrossRef) -> str:
    sep = "~" if self.ref_tilde else ""
    return f"{node.display_text}{sep}\\ref{{{node.label}}}"
```

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_latex.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/latex.py tests/test_latex.py
git commit -m "feat: LaTeX rendering for citations and cross-references"
```

---

### Task 12: 文档级指令 + Full Mode 输出

**Files:**
- Modify: `src/md_mid/latex.py` — `render_document` 在 full 模式下生成 preamble
- Modify: `tests/test_latex.py` — 补充 full mode 测试

**Step 1: 写失败测试**

追加到 `tests/test_latex.py`:
```python
class TestFullDocument:
    def _make_doc(self):
        doc = Document(children=[
            Heading(level=1, children=[Text(content="Intro")]),
            Paragraph(children=[Text(content="Content.")]),
        ])
        doc.metadata.update({
            "documentclass": "article",
            "classoptions": ["12pt", "a4paper"],
            "packages": ["amsmath", "graphicx"],
            "title": "My Paper",
            "author": "Author",
            "date": "2026",
            "abstract": "This is abstract.",
            "bibliography": "refs.bib",
            "bibstyle": "IEEEtran",
        })
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
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_latex.py::TestFullDocument -v`
Expected: FAIL

**Step 3: 实现 render_document 的 full mode**

在 `LaTeXRenderer.render_document` 中：

```python
def render_document(self, node: Document) -> str:
    body = self.render_children(node)

    if self.mode in ("body", "fragment"):
        return body

    # full mode
    meta = node.metadata
    lines = []

    # documentclass
    cls = meta.get("documentclass", "article")
    opts = meta.get("classoptions", [])
    opts_str = f"[{','.join(opts)}]" if opts else ""
    lines.append(f"\\documentclass{opts_str}{{{cls}}}")

    # packages (带 options)
    pkg_opts = meta.get("package_options", {})
    for pkg in meta.get("packages", []):
        if pkg in pkg_opts:
            lines.append(f"\\usepackage[{pkg_opts[pkg]}]{{{pkg}}}")
        else:
            lines.append(f"\\usepackage{{{pkg}}}")

    # bibstyle
    if bibstyle := meta.get("bibstyle"):
        lines.append(f"\\bibliographystyle{{{bibstyle}}}")

    # title/author/date
    for key in ("title", "author", "date"):
        if val := meta.get(key):
            lines.append(f"\\{key}{{{val}}}")

    # extra preamble
    if preamble := meta.get("preamble"):
        lines.append(preamble)

    lines.append("")
    lines.append("\\begin{document}")
    lines.append("\\maketitle")

    # abstract
    if abstract := meta.get("abstract"):
        lines.append("")
        lines.append("\\begin{abstract}")
        lines.append(abstract.strip())
        lines.append("\\end{abstract}")

    lines.append("")
    lines.append(body)

    # bibliography
    bib = meta.get("bibliography", "")
    bib_mode = meta.get("bibliography_mode", "auto")
    if bib and bib_mode in ("auto", "standalone"):
        bib_name = bib.removesuffix(".bib")
        lines.append(f"\\bibliography{{{bib_name}}}")

    lines.append("")
    lines.append("\\end{document}")
    return "\n".join(lines) + "\n"
```

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_latex.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/latex.py tests/test_latex.py
git commit -m "feat: full document mode with preamble, title, abstract, bibliography"
```

---

### Task 13: Body 与 Fragment 输出模式

**Files:**
- Modify: `src/md_mid/latex.py` — body/fragment 分支
- Modify: `tests/test_latex.py` — 补充测试
- Modify: `src/md_mid/comment.py` — body/fragment 下文档级指令的警告逻辑

**Step 1: 写失败测试**

追加到 `tests/test_latex.py`:
```python
class TestBodyMode:
    def test_body_no_preamble(self):
        doc = Document(children=[
            Heading(level=1, children=[Text(content="Intro")]),
            Paragraph(children=[Text(content="Content.")]),
        ])
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
        doc = Document(children=[
            Heading(level=1, children=[Text(content="Title")]),
            Paragraph(children=[Text(content="Content.")]),
        ])
        result = render(doc, mode="fragment")
        assert "\\section" not in result
        assert "Content." in result

    def test_fragment_preserves_inline(self):
        doc = Document(children=[
            Paragraph(children=[
                Text(content="This is "),
                Strong(children=[Text(content="bold")]),
            ]),
        ])
        result = render(doc, mode="fragment")
        assert "\\textbf{bold}" in result
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_latex.py -k "Body or Fragment" -v`
Expected: FAIL

**Step 3: 实现 body/fragment 模式**

- `render_document`：body 模式只返回 `render_children()`，fragment 同理
- `render_heading`：fragment 模式下不输出 `\section` 等命令，仅输出标题文本作为段落

**Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_latex.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add src/md_mid/latex.py tests/test_latex.py
git commit -m "feat: body and fragment output modes"
```

---

### Task 14: Figure 与 Table LaTeX 渲染

**Files:**
- Modify: `src/md_mid/latex.py` — `render_figure`, `render_table`
- Modify: `src/md_mid/parser.py` — 确保 image 和 table 正确转换
- Modify: `tests/test_latex.py` — 补充测试

**Step 1: 写失败测试**

追加到 `tests/test_latex.py`:
```python
from md_mid.nodes import Figure, Table


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
            headers=["Method", "RMSE"],
            alignments=["left", "left"],
            rows=[["RANSAC", "2.3"], ["Ours", "1.9"]],
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
```

**Step 2-5: 实现、测试、提交**

Run: `uv run pytest tests/test_latex.py -k "Figure or Table" -v`

```bash
git add src/md_mid/latex.py src/md_mid/parser.py tests/test_latex.py
git commit -m "feat: figure and table LaTeX rendering"
```

---

### Task 15: Footnote 支持

**Files:**
- Modify: `src/md_mid/parser.py` — 脚注解析（footnote plugin 已启用）
- Modify: `src/md_mid/latex.py` — `render_footnote_ref`
- Modify: `tests/test_latex.py` — 脚注测试

**Step 1: 写失败测试**

```python
def test_footnote_e2e():
    text = "Text[^note1].\n\n[^note1]: Footnote content.\n"
    result = convert(text)
    assert "\\footnote{Footnote content.}" in result
```

**Step 2-5: 实现两次扫描（收集定义 → 在引用点展开）、测试、提交**

```bash
git commit -m "feat: footnote support with inline expansion"
```

---

### Task 16: Phase 1 完整 E2E 测试（PRD §13 示例）

**Files:**
- Create: `tests/fixtures/full_example.mid.md` — PRD §13.1 的完整输入
- Modify: `tests/test_e2e.py` — 对照 PRD §13.2 验证输出

**Step 1: 创建 fixture**

将 PRD §13.1 的完整示例复制到 `tests/fixtures/full_example.mid.md`。

**Step 2: 写 E2E 测试**

```python
class TestFullExample:
    """对照 PRD §13.2 验证完整输出。"""

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
```

**Step 3: 运行测试**

Run: `uv run pytest tests/test_e2e.py::TestFullExample -v`
Expected: 全部 PASS

**Step 4: Commit**

```bash
git add tests/fixtures/full_example.mid.md tests/test_e2e.py
git commit -m "test: Phase 1 E2E tests with full PRD example"
```

---

## 验收标准

Phase 1 完成后，应满足以下条件：

1. **`uv run pytest` 全部通过**
2. **`uv run md-mid tests/fixtures/full_example.mid.md -o /tmp/paper.tex`** 能正确生成与 PRD §13.2 基本一致的 LaTeX 输出
3. **`uv run md-mid tests/fixtures/full_example.mid.md --mode body -o /tmp/body.tex`** 仅输出 body 内容
4. **诊断系统**：对未匹配的 `begin/end`、未知指令、重复 label 等输出清晰的 WARNING/ERROR
5. **数学公式完整性**：`$...$` 和 `$$...$$` 内部内容不被转义

## 任务总览

| # | Task | Phase | 预计步骤 |
|---|------|-------|---------|
| 1 | 项目脚手架 | 1a | 5 |
| 2 | 诊断系统 | 1a | 5 |
| 3 | EAST 节点定义 | 1a | 5 |
| 4 | LaTeX 特殊字符转义 | 1a | 5 |
| 5 | Parser（markdown-it-py + AST 构建）| 1a | 6 |
| 6 | Comment Processor | 1a | 6 |
| 7 | LaTeX Renderer（最小节点集）| 1a | 5 |
| 8 | CLI 骨架 | 1a | 5 |
| 9 | Phase 1a E2E 冒烟测试 | 1a | 4 |
| 10 | Citation/CrossRef 解析 | 1b | 5 |
| 11 | Citation/CrossRef LaTeX 渲染 | 1b | 5 |
| 12 | 文档级指令 + Full Mode | 1b | 5 |
| 13 | Body/Fragment 输出模式 | 1b | 5 |
| 14 | Figure/Table 渲染 | 1b | 5 |
| 15 | Footnote 支持 | 1b | 5 |
| 16 | Phase 1 完整 E2E 测试 | 1b | 4 |
