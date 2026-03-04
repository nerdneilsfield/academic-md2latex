# md-mid

[![Python](https://img.shields.io/badge/Python-≥3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-425%2B%20passed-brightgreen)](tests/)
[![mypy](https://img.shields.io/badge/type%20check-mypy%20strict-blue)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230?logo=ruff)](https://docs.astral.sh/ruff/)
[![uv](https://img.shields.io/badge/pkg-uv-DE5FE9?logo=uv)](https://docs.astral.sh/uv/)

中文 · **[English](README.md)**

---

**学术写作中间格式与多目标转换工具**

md-mid 定义了一种基于 Markdown 的学术写作中间格式（`.mid.md`）。用纯 Markdown 编写
论文，通过 HTML 注释携带元数据，一次编写即可转换为 **LaTeX**、**富 Markdown** 或
**自包含 HTML** — 全部来自同一份源文件。

```mermaid
graph LR
    A["paper.mid.md"] --> B["md-mid"]
    B --> C["paper.tex"]
    B --> D["paper.html"]
    B --> E["paper.md"]
    style A fill:#f9f,stroke:#333
    style C fill:#ffa,stroke:#333
    style D fill:#aff,stroke:#333
    style E fill:#afa,stroke:#333
```

## 功能特性

- **多目标输出** — LaTeX (`.tex`)、富 Markdown (`.md`) 和带 MathJax 的 HTML
- **8 种引用命令** — `cite`、`citep`、`citet`、`citeauthor`、`citeyear`、`textcite`、
  `parencite`、`autocite`，支持 BibTeX 文件解析
- **数学公式** — 行内 `$...$` 与行间 `$$...$$`，支持标签和方程环境
- **交叉引用** — 标签和引用在不同目标中自动转换为 `\ref{}` / `<a href>` / `{#id}`
- **图表** — 通过 HTML 注释指令设置 caption、label、width、placement
- **环境块** — `<!-- begin: algorithm -->` / `<!-- end: algorithm -->`
- **TeX 嵌入** — `<!-- include-tex: fragment.tex -->` 引入外部 LaTeX 片段
- **AI 图片生成** — 可选的 nanobanana 兼容 runner 图片生成管线
- **5 层配置** — CLI > 行内指令 > 配置文件 > 模板 > 默认值
- **国际化** — 支持 `zh`（中文）和 `en`（英文）图表标签

## 架构

```mermaid
flowchart TD
    subgraph 输入
        SRC["paper.mid.md"]
    end

    subgraph "解析管线"
        P["Markdown 解析器<br/><i>markdown-it-py + 插件</i>"]
        C["注释处理器<br/><i>4 阶段指令提取</i>"]
        EAST["增强 AST (EAST)<br/><i>32 种节点类型</i>"]
    end

    subgraph 渲染器
        LTX["LaTeX 渲染器<br/><code>.tex</code>"]
        MD["Markdown 渲染器<br/><code>.md</code>"]
        HTML["HTML 渲染器<br/><code>.html</code> + MathJax"]
    end

    SRC --> P --> C --> EAST
    EAST --> LTX
    EAST --> MD
    EAST --> HTML
```

每个渲染器支持三种输出模式：

| 模式 | LaTeX | Markdown | HTML |
|------|-------|----------|------|
| `full` | 导言区 + `\begin{document}` + 参考文献 | YAML front matter + 正文 + 脚注 | `<!DOCTYPE html>` + CSS + MathJax CDN |
| `body` | `\begin{document}...\end{document}` 内部 | 正文 + 脚注（无 front matter） | `<body>` 内容 |
| `fragment` | 裸内容，标题降级一级 | 裸内容 | 裸内容 |

<details>
<summary><b>EAST 节点类型（共 32 种）</b></summary>

**块级节点 (16)：**
`Document` · `Heading` · `Paragraph` · `Blockquote` · `List` · `ListItem` · `CodeBlock` ·
`MathBlock` · `Figure` · `Table` · `Environment` · `RawBlock` · `ThematicBreak` ·
`FootnoteDef` · `HardBreak` · `SoftBreak`

**行内节点 (16)：**
`Text` · `Strong` · `Emphasis` · `CodeInline` · `MathInline` · `Link` · `Image` ·
`Citation` · `CrossRef` · `FootnoteRef` · `FootnoteDef` · `SoftBreak` · `HardBreak` ·
`RawInline` · `Strikethrough` · `Superscript`

所有节点继承 `Node` 基类，拥有 `children`、`metadata` 和 `position` 字段。

</details>

## 快速开始

### 前置条件

- **Python 3.14+**
- [**uv**](https://docs.astral.sh/uv/) 包管理器

### 安装

```bash
git clone https://github.com/<owner>/academic-md2latex.git
cd academic-md2latex
uv sync
```

### 基本用法

```bash
# Markdown → LaTeX（默认）
md-mid paper.mid.md -o paper.tex

# Markdown → HTML（带 MathJax）
md-mid paper.mid.md -o paper.html -t html

# Markdown → 富 Markdown
md-mid paper.mid.md -o paper.md -t markdown

# 从标准输入读取，仅正文模式
cat paper.mid.md | md-mid - --mode body -o paper.tex

# 导出增强 AST 用于调试
md-mid paper.mid.md --dump-east | jq .
```

<details>
<summary><b>完整 CLI 参考</b></summary>

```
用法: md-mid [OPTIONS] INPUT

选项:
  -o, --output PATH                   输出文件（省略则输出到 stdout）
  -t, --target [latex|markdown|html]  输出格式（默认: latex）
  --mode [full|body|fragment]         输出范围（默认: full）
  --config PATH                       配置文件（md-mid.yaml）
  --template PATH                     LaTeX 模板（.yaml）
  --bib PATH                          参考文献文件（.bib）
  --bibliography-mode MODE            auto | standalone | external | none
  --heading-id-style [attr|html]      标题锚点格式
  --locale [zh|en]                    标签语言（默认: zh）
  --generate-figures                  启用 AI 图片生成
  --figures-runner PATH               图片生成 runner 脚本
  --figures-config PATH               runner 配置（TOML）
  --force-regenerate                  强制重新生成已有图片
  --strict                            严格解析模式
  --verbose                           详细输出
  --dump-east                         导出增强 AST 为 JSON
  --version                           显示版本号
```

</details>

## 文档格式

md-mid 文档是标准 Markdown 文件，扩展名为 `.mid.md`。所有学术元数据通过
**HTML 注释**（`<!-- key: value -->`）编码，因此源文件在任何 Markdown 阅读器中
都完全可读，同时携带完整的 LaTeX 语义。

### 文档级指令

写在 `.mid.md` 文件顶部，控制 LaTeX 导言区：

```markdown
<!-- documentclass: article -->
<!-- classoptions: [12pt, a4paper] -->
<!-- packages: [amsmath, graphicx, hyperref] -->
<!-- bibliography: refs.bib -->
<!-- bibstyle: IEEEtran -->
<!-- title: 基于 FPGA 的实时点云配准方法 -->
<!-- author: 作者姓名 -->
<!-- date: 2026 -->
<!-- abstract: |
  本文提出了一种基于 FPGA 的实时点云配准方法……
-->
```

<details>
<summary><b>生成的 LaTeX 导言区</b></summary>

```latex
\documentclass[12pt,a4paper]{article}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{hyperref}
\bibliographystyle{IEEEtran}
\title{基于 FPGA 的实时点云配准方法}
\author{作者姓名}
\date{2026}

\begin{document}
\maketitle

\begin{abstract}
本文提出了一种基于 FPGA 的实时点云配准方法……
\end{abstract}

% ... 正文内容 ...

\bibliography{refs}

\end{document}
```

</details>

### 引用

使用 Markdown 链接语法，URL 中带 `cite:` 前缀：

```markdown
先前的工作 [Wang et al.](cite:wang2024) 表明……
经典方法 [1](citep:fischler1981) 存在局限性。
如 [Smith](citeauthor:smith2023) 所述……
```

| md-mid 语法 | LaTeX 输出 | HTML 输出 |
|-------------|-----------|-----------|
| `[text](cite:key)` | `\cite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citep:key)` | `\citep{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citet:key)` | `\citet{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citeauthor:key)` | `\citeauthor{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citeyear:key)` | `\citeyear{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](textcite:key)` | `\textcite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](parencite:key)` | `\parencite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](autocite:key)` | `\autocite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |

### 交叉引用

```markdown
# 绪论
<!-- label: sec:intro -->

详见 [第1节](ref:sec:intro)。
```

| 目标 | 输出 |
|------|------|
| LaTeX | `\label{sec:intro}` + `\ref{sec:intro}` |
| HTML | `<h1 id="sec:intro">` + `<a href="#sec:intro">` |
| Markdown | `{#sec:intro}` + `<a href="#sec:intro">` |

### 带元数据的图片

```markdown
![流程概览](figures/pipeline.png)
<!-- caption: 点云配准方法分类 -->
<!-- label: fig:pipeline -->
<!-- width: 0.85\textwidth -->
<!-- placement: htbp -->
```

<details>
<summary><b>生成的 LaTeX 图片环境</b></summary>

```latex
\begin{figure}[htbp]
\centering
\includegraphics[width=0.85\textwidth]{figures/pipeline.png}
\caption{点云配准方法分类}
\label{fig:pipeline}
\end{figure}
```

</details>

<details>
<summary><b>生成的 HTML 图片</b></summary>

```html
<figure id="fig:pipeline">
  <img src="figures/pipeline.png"
       alt="流程概览"
       loading="lazy">
  <figcaption>图 1: 点云配准方法分类</figcaption>
</figure>
```

</details>

<details>
<summary><b>生成的富 Markdown 图片</b></summary>

```html
<figure id="fig:pipeline">
  <img src="figures/pipeline.png"
       alt="流程概览"
       style="max-width:100%">
  <figcaption><strong>图 1</strong>: 点云配准方法分类</figcaption>
</figure>
```

</details>

### AI 生成图片

标记图片为 AI 生成，在输出中包含溯源元数据：

```markdown
![分类图](figures/taxonomy.png)
<!-- caption: 方法分类 -->
<!-- label: fig:taxonomy -->
<!-- ai-generated: true -->
<!-- ai-model: dall-e-3 -->
<!-- ai-prompt: |
  学术风格的方法分类图，
  简洁干净，白底蓝色点缀
-->
<!-- ai-negative-prompt: 写实风格, 3D渲染 -->
```

在 LaTeX 输出中，AI 元数据变为 `%` 注释；在 HTML 和富 Markdown 中，渲染为可折叠的
`<details>` 块。

使用 `--generate-figures` 从提示词自动生成图片：

```bash
md-mid paper.mid.md -o paper.tex \
  --generate-figures \
  --figures-runner ./runner.py \
  --figures-config api.toml
```

### 表格

```markdown
| 方法   | RMSE (cm) | 时间 (ms) | 平台   |
|--------|-----------|-----------|--------|
| RANSAC | 2.3       | 150       | CPU    |
| 本文   | 1.9       | 8         | FPGA   |
<!-- caption: ModelNet40 数据集性能对比 -->
<!-- label: tab:results -->
```

<details>
<summary><b>生成的 LaTeX 表格</b></summary>

```latex
\begin{table}[htbp]
\centering
\caption{ModelNet40 数据集性能对比}
\label{tab:results}
\begin{tabular}{llll}
\hline
方法 & RMSE (cm) & 时间 (ms) & 平台 \\
\hline
RANSAC & 2.3 & 150 & CPU \\
本文 & 1.9 & 8 & FPGA \\
\hline
\end{tabular}
\end{table}
```

</details>

### 数学公式

```markdown
行内公式：变换 $T \in SE(3)$ 定义为……

行间公式带标签：

$$
T = \begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix}
$$
<!-- label: eq:transform -->
```

| 目标 | 行内 | 行间 |
|------|------|------|
| LaTeX | `$T \in SE(3)$` | `\begin{equation} ... \label{eq:transform} \end{equation}` |
| HTML | `$T \in SE(3)$` (MathJax) | `\[ ... \]`，带 `id="eq:transform"` |
| Markdown | `$T \in SE(3)$` | `$$ ... $$`，带 `<a id="eq:transform">` |

### 环境块

```markdown
<!-- begin: algorithm -->
**输入：** 点云 $P$ 和 $Q$

1. 计算共面基
2. 寻找全等集
3. 验证与精炼

**输出：** 刚体变换 $T$
<!-- end: algorithm -->
```

<details>
<summary><b>生成的 LaTeX 环境</b></summary>

```latex
\begin{algorithm}
\textbf{输入：} 点云 $P$ 和 $Q$

\begin{enumerate}
\item 计算共面基
\item 寻找全等集
\item 验证与精炼
\end{enumerate}

\textbf{输出：} 刚体变换 $T$
\end{algorithm}
```

</details>

### TeX 嵌入

插入外部 LaTeX 片段（如复杂的 TikZ 图）：

```markdown
<!-- include-tex: figures/architecture.tex -->
```

读取文件内容并作为 `RawBlock` 节点插入，支持在环境块内递归使用。

### 完整示例

参见 [`tests/fixtures/full_example.mid.md`](tests/fixtures/full_example.mid.md)，
展示了所有功能的完整用例。

## 配置

```mermaid
flowchart LR
    CLI["CLI 参数"] --> R["解析器"]
    DIR["行内指令"] --> R
    CFG["配置文件<br/><code>md-mid.yaml</code>"] --> R
    TPL["模板<br/><code>ieee.yaml</code>"] --> R
    DEF["内置默认值"] --> R
    R --> OUT["最终配置"]

    style CLI fill:#ffa
    style DIR fill:#fda
    style CFG fill:#fca
    style TPL fill:#faa
    style DEF fill:#eee
```

优先级：**CLI > 行内指令 > 配置文件 > 模板 > 默认值**。高层覆盖低层。这让你可以在
模板中设置投稿目标默认值，在配置文件中按论文覆盖，在命令行中按次构建微调。

### 配置文件（`md-mid.yaml`）

```yaml
documentclass: article
classoptions: [12pt, a4paper]
packages: [amsmath, graphicx]
code_style: lstlisting       # 或: minted
locale: zh                    # 或: en
target: latex                 # 或: markdown, html
bibliography_mode: auto       # 或: standalone, external, none
heading_id_style: attr        # 或: html
extra-preamble: |
  \DeclareMathOperator{\argmin}{argmin}
```

<details>
<summary><b>全部配置字段</b></summary>

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `documentclass` | `str` | `"article"` | LaTeX 文档类 |
| `classoptions` | `list[str]` | `[]` | 类选项，如 `12pt`、`a4paper` |
| `packages` | `list[str]` | `[]` | 要加载的 LaTeX 包 |
| `title` | `str` | `""` | 文档标题 |
| `author` | `str` | `""` | 作者 |
| `date` | `str` | `""` | 日期 |
| `abstract` | `str` | `""` | 摘要文本 |
| `bibliography` | `str` | `""` | BibTeX 文件路径 |
| `bibstyle` | `str` | `"plain"` | 参考文献样式 |
| `code_style` | `str` | `"lstlisting"` | 代码块渲染样式 |
| `locale` | `str` | `"zh"` | 标签语言 |
| `target` | `str` | `"latex"` | 默认输出目标 |
| `bibliography_mode` | `str` | `"auto"` | 参考文献输出策略 |
| `heading_id_style` | `str` | `"attr"` | 标题锚点格式 |
| `extra-preamble` | `str` | `""` | 导言区原始 LaTeX |
| `thematic_break_style` | `str` | `"newpage"` | `newpage` / `hrule` / `ignore` |
| `tilde_ref` | `bool` | `true` | 使用 `~\ref` 代替 `\ref` |

</details>

### 模板文件

模板为特定投稿目标提供可复用的默认配置。示例 — IEEE 会议：

```yaml
# templates/ieee.yaml
documentclass: IEEEtran
classoptions: [conference]
packages:
  - amsmath
  - graphicx
  - cite
extra-preamble: |
  \IEEEoverridecommandlockouts
bibstyle: IEEEtran
```

```bash
md-mid paper.mid.md --template templates/ieee.yaml -o paper.tex
```

## 项目结构

```
academic-md2latex/
├── src/md_mid/              # 源代码（16 个模块）
│   ├── cli.py               #   Click CLI 入口
│   ├── parser.py            #   Markdown → EAST 解析器
│   ├── nodes.py             #   EAST 节点定义（32 种类型）
│   ├── comment.py           #   4 阶段注释指令处理器
│   ├── config.py            #   5 层配置解析
│   ├── latex.py             #   LaTeX 渲染器
│   ├── markdown.py          #   富 Markdown 渲染器（2 遍扫描）
│   ├── html.py              #   HTML 渲染器（MathJax CDN）
│   ├── bibtex.py            #   最小化 BibTeX 解析器
│   ├── genfig.py            #   AI 图片生成管线
│   ├── escape.py            #   LaTeX 特殊字符转义
│   ├── sanitize.py          #   HTML 输入清洗
│   ├── url_check.py         #   URL 安全验证
│   ├── ai_meta.py           #   共享 AI 元数据渲染
│   └── diagnostic.py        #   错误/警告诊断
├── tests/                   # 测试套件（16 个文件，425+ 测试）
│   ├── fixtures/            #   测试用 .mid.md 文档
│   └── conftest.py          #   共享 pytest fixtures
├── templates/               # LaTeX 投稿模板 (ieee.yaml, ...)
├── docs/                    # 文档与计划
├── pyproject.toml           # 项目元数据和工具配置
├── Makefile                 # 构建命令
└── CLAUDE.md                # AI 代理编码规范
```

<details>
<summary><b>注释处理器 4 阶段管线</b></summary>

```mermaid
flowchart TD
    A["阶段 1：文档指令<br/><i>documentclass, packages, title, ...</i>"]
    B["阶段 2：Begin/End 环境<br/><i>algorithm, theorem, proof, ...</i>"]
    C["阶段 3：Include-TeX<br/><i>插入外部 .tex 片段</i>"]
    D["阶段 4：Attach-Up 指令<br/><i>caption, label, width, placement, ai-*</i>"]

    A --> B --> C --> D
```

- **阶段 1** 提取顶层元数据（documentclass、packages、title、author 等）
- **阶段 2** 将 `<!-- begin: X -->` / `<!-- end: X -->` 配对为 `Environment` 节点
- **阶段 3** 将 `<!-- include-tex: file.tex -->` 替换为 `RawBlock` 内容（支持递归）
- **阶段 4** 将尾随注释元数据附加到前面的 figure/table/math 节点

</details>

## 开发

### 环境搭建

```bash
uv sync                      # 安装所有依赖
```

### 命令

| 命令 | 说明 |
|------|------|
| `make check` | 运行 lint + 类型检查 + 测试 **（提交前必须执行）** |
| `make test` | 运行 pytest（详细输出） |
| `make lint` | 运行 ruff 检查 |
| `make format` | 运行 ruff 格式化 |
| `make typecheck` | 运行 mypy（严格模式） |
| `make fix` | 自动修复 lint 问题并格式化 |

### 编码规范

| 规则 | 示例 |
|------|------|
| 所有函数必须有类型注解 | `def parse(text: str) -> Document:` |
| 双语注释（英文 + 中文） | `# Calculate average (计算平均值)` |
| Google 风格双语文档字符串 | 参见 [CLAUDE.md](CLAUDE.md) |
| 行长最大 100 字符 | 由 ruff 强制执行 |
| 函数 `snake_case`，类 `PascalCase` | `render_figure()`、`LaTeXRenderer` |

<details>
<summary><b>文档字符串示例</b></summary>

```python
def render_figure(self, node: Node) -> str:
    """Render a Figure node as LaTeX figure environment.

    将 Figure 节点渲染为 LaTeX figure 环境。

    Args:
        node: Figure node to render (待渲染的 Figure 节点)

    Returns:
        LaTeX figure environment string (LaTeX figure 环境字符串)
    """
```

</details>

### 测试

测试文件与源代码模块一一对应（`parser.py` → `test_parser.py`）。

```bash
make test                    # 运行全部 425+ 测试
```

| 测试文件 | 覆盖内容 |
|----------|----------|
| `test_parser.py` | Markdown 解析、节点创建 |
| `test_nodes.py` | EAST 序列化、类型属性 |
| `test_latex.py` | LaTeX 渲染（标题、公式、引用、表格、图片） |
| `test_markdown.py` | 富 Markdown 渲染、索引遍 |
| `test_html.py` | HTML 渲染、清洗、MathJax |
| `test_comment.py` | 4 阶段注释指令处理 |
| `test_config.py` | 配置加载、优先级、验证 |
| `test_cli.py` | CLI 选项、错误处理 |
| `test_e2e.py` | 端到端转换管线 |
| `test_bibtex.py` | BibTeX 文件解析 |
| `test_genfig.py` | AI 图片生成任务 |
| `test_escape.py` | LaTeX 特殊字符转义 |
| `test_sanitize.py` | HTML 输入清洗 |
| `test_url_check.py` | URL 安全验证 |
| `test_diagnostic.py` | 诊断错误/警告收集 |

测试夹具在 [`tests/fixtures/`](tests/fixtures/) 下提供可复用的 `.mid.md` 文档：
`minimal`、`heading_para`、`math`、`cite_ref`、`comments`、`full_example`。

## 贡献指南

1. Fork 本仓库
2. 创建功能分支
3. 先写测试（推荐 TDD）
4. 确保 `make check` 通过（ruff、mypy、pytest）
5. 提交 Pull Request

所有代码必须包含完整的类型注解和双语（英文 + 中文）注释。
详见 [CLAUDE.md](CLAUDE.md) 完整编码规范。
