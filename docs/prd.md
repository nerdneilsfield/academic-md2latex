# PRD: Wenqiao — Wenqiao MID Markdown 学术写作中间格式与多目标转换工具

说明：

- **wenqiao**：项目/仓库名
- **Wenqiao MID Markdown**：本项目定义的“学术写作中间格式”（历史称呼：md-mid）
- **wenqiao**：CLI 工具名（历史命令：md-mid）

## 1. 项目定位

### 1.1 核心思想

定义一种**基于 Markdown 的学术写作中间格式**（下称 Wenqiao MID Markdown，简称 MID），作为论文写作的单一源文件（single source of truth）。MID 不是标准 Markdown 的子集，而是一种**带语义注释的 Markdown 方言**，服务于两个输出目标：

```
                    ┌──→  LaTeX (.tex)     用于论文投稿、编译 PDF
                    │
  MID (.mid.md) ────┤
                    │
                    └──→  Rich Markdown / HTML (.md / .html)  用于预览、分享、博客
```

**关键洞察**：论文写作过程中，作者需要在"写"和"看"之间频繁切换。MID 让你用一份源文件同时满足这两个需求——LaTeX 输出用于最终排版，Rich Markdown/HTML 输出用于日常阅读、分享和版本管理。

### 1.2 设计原则

- **源文件即主体**：MID 文件本身应具备良好的可读性，即使不经过任何转换，裸读也能理解内容
- **双向不丢信息**：所有在 LaTeX 中需要表达的语义（label、caption、cite、ref……），都能在 Rich Markdown 输出中找到对应的可视化表达
- **渐进式采用**：最简情况下，一个纯 Markdown 文件就能直接转换，注释指令全部可选
- **LaTeX 透传**：任何时候都可以直接写 LaTeX 命令，工具原样输出，不报错不干涉
- **输出范围可控**：可以生成完整 `.tex` 文档，也可以只生成 `\begin{document}...\end{document}` 内部的 body 片段，方便嵌入已有的 LaTeX 工程

### 1.3 非目标

- 不做 LaTeX → Markdown 反向转换
- 不做 LaTeX 编译（交给 `xelatex` / `latexmk`）
- 不做实时编辑器或 WYSIWYG 界面
- 不处理 BibTeX 文件本身的管理

### 1.4 典型写作工作流

MID 主要覆盖两类写作流，对应两种常见的 LaTeX 工程组织方式：

#### A. 工程式写作（章节拆分，主 LaTeX 框架已存在）

**适用场景**：你已经有一个主 `main.tex`（或模板工程），并通过 `\include{sec1.tex}` / `\input{...}` 预留章节位置；preamble、宏包、版式、bibliography 由主工程统一管理。

**流程**：

1. 按章节/小节拆分写作：每个章节一个 MID 文件（建议命名为 `sec1.mid.md` 之类，便于区分源文件与生成物）。
2. 出图（可选）：对带 `ai-generated: true` 元信息的 figure，调用图片生成工具生成/更新图片资源；若图片暂缺，则插入/引用占位图（placeholder），并保留 prompt 等信息用于复现。
3. 生成章节 `.tex`：使用 **Body-only 模式**输出（只生成正文片段，不重复主工程的 preamble/bib）。
4. 编译主工程：用 `latexmk` / `xelatex` 编译 `main.tex`；需要修改内容时，只编辑 MID，再重新生成对应章节 `.tex`。

#### B. 独立写作（单文件输出可编译 LaTeX）

**适用场景**：你希望一份 MID 直接生成完整、可编译的 `paper.tex`（standalone）。

**流程**：

1. 单文件写作：`paper.mid.md`
2. 出图（可选）：同上
3. 生成完整 `.tex`：使用 **Full Document 模式**输出（包含 preamble、title/author/abstract、bibliography 等）
4. 编译：直接编译生成的 `paper.tex`
5. 提供预定义的 preamble, bibliography  配置；比如对图片、表格、代码高亮、bibtex 中文等的支持

---

## 2. 系统架构

```
                         MID source (.mid.md)
                                │
                                ▼
                     ┌─────────────────────┐
                     │    Markdown Parser   │   markdown-it-py
                     └──────────┬──────────┘
                                │ Raw AST
                                ▼
                     ┌─────────────────────┐
                     │  Comment Processor   │   解析注释 → metadata，处理 begin/end 配对
                     └──────────┬──────────┘
                                │ Enhanced AST (EAST)
                                ▼
               ┌────────────────┼────────────────┐
               │                │                │
               ▼                ▼                ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │ LaTeX Renderer│  │  MD Renderer │  │ HTML Renderer│
     │   (Backend)   │  │  (Backend)   │  │  (Backend)   │
     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
            │                 │                  │
            ▼                 ▼                  ▼
        .tex file       .rendered.md         .html file
```

### 2.1 Enhanced AST (EAST)

EAST 是系统的核心数据结构。它在标准 Markdown AST 的基础上：

1. **注释已消化**：HTML 注释节点已被移除，其 key-value 内容合并到相邻节点的 `metadata` 字段
2. **环境已成型**：`begin/end` 配对已转化为 `environment` 类型的包裹节点
3. **引用已标记**：`cite:` 和 `ref:` 前缀的链接节点已被标记为 `citation` 和 `cross_ref` 类型
4. **图片已增强**：AI 图片的 prompt 信息已附着到 `image` 节点的 metadata

EAST 对所有 Renderer Backend 是统一的输入，各 Backend 只负责"怎么输出"，不做语义分析。

### 2.2 模块清单

| 模块 | 职责 |
|---|---|
| **Parser** | 使用 markdown-it-py 解析 Markdown，生成 Raw AST / token stream |
| **Comment Processor** | 注释解析、metadata 附着、环境节点生成、链接类型标记 |
| **LaTeX Backend** | EAST → LaTeX 字符串，支持 full / body / fragment 模式 |
| **Markdown Backend** | EAST → 渲染增强的 Markdown（cite→脚注，ref→锚点跳转，figure→居中图片块） |
| **HTML Backend** | EAST → 自包含 HTML 页面（可选，作为 Markdown Backend 的进阶版本） |
| **Template Manager** | 管理 LaTeX preamble 模板（documentclass、packages、自定义命令） |
| **Config Resolver** | 合并配置优先级：CLI args > 文档内注释 > 外部配置文件 > 模板文件 > 默认值 |
| **CLI** | 命令行入口 |

### 2.3 技术选型：Markdown Parser（markdown-it-py）

本项目选定 **markdown-it-py** 作为唯一 Markdown 解析器（Python 生态、CommonMark 兼容、插件机制成熟），避免混用 JS 工具造成实现与依赖混乱。

推荐的初始化方式（可按需裁剪）：

- preset：`commonmark`（可预测、规范明确）
- 语法增强：启用 `table`；按需加载 `mdit-py-plugins`（如 footnote）
- 数学公式：`$...$` / `$$...$$` **需要额外插件或自定义 rule** 才能解析为 `math_inline/math_block`（否则会被当作普通文本）
  - 推荐：使用 `mdit-py-plugins` 的数学插件（例如 texmath/dollarmath 系列）来产出独立的 math token
  - 目的：让 Renderer 能在 math 节点上执行“绝对豁免区”，避免 `_`/`^` 等被转义破坏公式

示例（说明性伪代码）：

```python
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin

md = (
    MarkdownIt("commonmark", {"html": True})
    .use(footnote_plugin)
    .enable("table")
    # TODO: use math plugin to parse $...$ / $$...$$ into math_inline/math_block tokens
)
tokens = md.parse(text)
```

验收标准（Parser + Renderer 协作）：

- `$$ ... $$` 必须被解析为独立 `math_block`（或等价结构），其 raw 内容应完整保留
- `math_inline/math_block/raw_block/code_*` 必须走转义豁免路径（见 §7.3）

解析流程建议：

1. `MarkdownIt(...).parse(text)` 得到 token stream（便于拿到块级结构与行号范围）
2. 需要树结构时，用 `SyntaxTreeNode(tokens)` 将 open/close token 折叠为层级节点
3. Comment Processor 从 `html_block/html_inline` 中识别 `<!-- ... -->`，再按本 PRD 的 YAML 规则解析并附着

位置信息建议：

- markdown-it-py 的 block token 通常带有 `token.map = [start_line, end_line]`（行范围）
- 本项目对外的 `position.line/column` 统一使用 **1-based**；offset 为可选（best-effort）

---

## 3. 输出模式

### 3.1 LaTeX 输出

`--mode` 参数控制 LaTeX 输出的范围：

#### 3.1.1 Full Document 模式（默认，standalone）

生成完整的 `.tex` 文件，包含 preamble 和 document 环境：

```latex
\documentclass[12pt,a4paper]{article}
\usepackage{amsmath}
\usepackage{graphicx}
% ...

\begin{document}
\maketitle

% === body 内容 ===
\section{绪论}
...

\bibliography{refs}
\end{document}
```

**bibliography 输出**：由 `bibliography-mode` 控制。standalone 模式通常需要插入 `\bibliographystyle` / `\bibliography`；章节/局部模式通常由主工程负责。

#### 3.1.2 Body-only 模式（章节/局部模式）

仅生成 `\begin{document}` 和 `\end{document}` 之间的内容，不含 preamble，不含 `\begin{document}` / `\end{document}` 本身：

```latex
\section{绪论}
\label{chap:intro}

这是正文...

\subsection{研究背景}
...
```

**使用场景**：

- 论文各章节拆分为独立的 MID 文件，通过主 `.tex` 文件 `\input{chapter1}` 引入
- 已有 LaTeX 工程，只想用 MID 写某个章节的内容
- 与 Overleaf 等在线 LaTeX 编辑器配合，主文件在 Overleaf 维护，章节内容用 MID 生成

**章节模式约定**（建议默认行为）：

- 文档级指令（如 `documentclass` / `packages` / `title` / `abstract`）在 LaTeX 输出中默认忽略（因为应由主工程控制）
- bibliography 相关输出（如 `\bibliographystyle` / `\bibliography`）默认不生成（主工程已处理）
- 但这些信息仍可用于 Rich Markdown/HTML 预览（例如 `.bib` 用于生成 cite 脚注）

#### 3.1.3 Fragment 模式

更极端的片段模式：不生成 `\section` 等结构命令，只转换行内和基本块级元素。用于在 LaTeX 文档中嵌入一小段由 Markdown 写成的内容。

建议约定（可配置）：

- heading：默认降级为普通段落文本（不输出任何结构命令）
- list/blockquote 等结构：可通过 `latex.fragment.preserve-structure` 控制是否保留为 LaTeX 环境
  - `false`（默认）：尽量“纯内容提取”
  - `true`：保留 `itemize/enumerate/quotation` 等环境，但仍不生成 `\section` 系列

### 3.2 Rich Markdown 输出

将 MID 转换为标准 Markdown + 少量 HTML，使其在 GitHub / Obsidian / Typora 等环境下渲染良好。

`--mode` 参数同样控制 Markdown 输出的范围：

- **Full Document 模式 (`full`)**：输出包含 YAML front matter（由文档级指令生成）、正文内容以及集中的脚注（如适用）。
- **Body-only 模式 (`body`)**：仅输出正文内容和脚注，不生成 YAML front matter。
- **Fragment 模式 (`fragment`)**：仅输出最小片段内容，不生成 front matter，也不收集和输出脚注定义。

核心转换规则：

| MID 语义 | Rich Markdown 输出 |
|---|---|
| `[text](cite:key)` / `[](cite:key)` | 脚注 `[^key]`（可选带显示文本），脚注内容为 BibTeX 条目或 key 本身 |
| `[text](ref:label)` | HTML 锚点跳转 `<a href="#label">text</a>` |
| `<!-- label: xxx -->` | 在目标元素上生成 `<a id="xxx"></a>` 锚点 |
| `<!-- caption: xxx -->` | 图片/表格下方生成居中的 caption 文字 |
| figure 指令组 | 居中图片 + caption + 编号 |
| table 指令组 | HTML table + caption + 编号 |
| `$$...$$`（可附加 `<!-- label: eq:... -->`） | 保留 `$$...$$`（并生成锚点，便于 ref 跳转） |
| `<!-- begin: raw -->...<!-- end: raw -->` | 折叠块 `<details>` 显示原始 LaTeX 代码 |
| AI 图片 prompt | 折叠块展示 prompt 信息，或以 HTML comment 保留 |
| 文档级指令 | 生成 YAML front matter（供 Jekyll/Hugo 等使用） |

**示例**：

MID 源文件：

```markdown
根据[Wang et al.](cite:wang2024)的研究，如[图1](ref:fig:result)所示。
```

Rich Markdown 输出：

```markdown
根据Wang et al.[^wang2024]的研究，如<a href="#fig:result">图1</a>所示。

[^wang2024]: Wang et al., 2024. *Point Cloud Registration via 4PCS*. CVPR.
```

### 3.3 HTML 输出（可选，Phase 5）

自包含的单 HTML 文件，带：

- MathJax 公式渲染
- 可点击的交叉引用跳转
- 自动编号的图表
- 文献引用弹窗/tooltip
- 响应式布局

---

## 4. MID 语法规范

### 4.1 Markdown 基础语法（支持子集）

#### 4.1.1 块级元素

| 语法 | LaTeX 输出 | Rich MD 输出 |
|---|---|---|
| `# H1` | `\section{H1}` | `# H1` + 锚点 |
| `## H2` | `\subsection{H2}` | `## H2` + 锚点 |
| `### H3` | `\subsubsection{H3}` | `### H3` + 锚点 |
| `#### H4` | `\paragraph{H4}`（默认，可由模板/配置改为其他层级） | `#### H4` |
| 段落 | 段落 | 段落 |
| `> quote` | `\begin{quotation}` | `> quote` |
| `- item` | `\begin{itemize}` | `- item` |
| `1. item` | `\begin{enumerate}` | `1. item` |
| 代码块 | `\begin{lstlisting}` | 代码块 |
| `![](path)` | `\begin{figure}` | 居中图片 + caption |
| 表格 | `\begin{table}` + `\begin{tabular}` | 表格 + caption |
| `---` | 可配置：`\newpage` / `\hrule` / 忽略 | `---` |

**表格支持范围（MVP）**：

- 仅支持“简单表格”（GFM 风格、单行单元格、无 rowspan/colspan、无多行单元格）
- 复杂表格建议用 `<!-- begin: raw -->...\n<!-- end: raw -->` 直接透传 LaTeX（或后续扩展“外部 `.tex` 表格片段引入”）

#### 4.1.2 行内元素

| 语法 | LaTeX | Rich MD |
|---|---|---|
| `**bold**` | `\textbf{}` | `**bold**` |
| `*italic*` | `\textit{}` | `*italic*` |
| `` `code` `` | `\texttt{}` | `` `code` `` |
| `$formula$` | `$formula$` 透传 | `$formula$` |
| `$$block$$` | 默认 `\[...\]`；若附着 `label` 则输出 `equation` 环境 + `\label{}` | `$$block$$` |
| `[t](url)` | `\href{url}{t}` | `[t](url)` |
| `[t](cite:k)` | `\cite{k}` | 脚注 `[^k]` |
| `[t](ref:l)` | `\ref{l}` | `<a href="#l">t</a>` |
| LaTeX 命令 | 透传 | `<details>` 折叠 或 原样保留 |

### 4.2 注释指令系统

统一格式：HTML 注释中写一条 **YAML 的单键映射**（`key: value`），并保持“就近附着”的语义：

```markdown
<!-- label: sec:intro -->

<!-- packages: [amsmath, graphicx, ctex] -->

<!-- abstract: |
  第一行摘要
  第二行摘要
-->
```

**命名约定（对外一致）**：

- 指令 key 统一使用 `kebab-case`（如 `package-options`、`heading-id-style`、`ref-tilde`）
- Comment Processor 会将 key 归一化后写入 EAST（内部可使用 `snake_case`，例如 `package_options`）

#### 4.2.1 文档级指令

在文件开头（第一个正文内容之前）声明。

**约束**：

- 仅在“文件头部区域”生效：从文件开始到 **第一个语义内容块**之前
  - 头部区域允许出现空行、仅空白的 paragraph、以及任意数量的 HTML 注释指令
  - 当遇到第一个语义内容块（如 heading/paragraph(text)/list/table/image/code/math/blockquote/environment/raw）即结束头部区域
- 若源文件包含 YAML front matter（`--- ... ---`）且启用了相关解析插件，则 front matter 会被视为语义内容块并结束头部区域（建议将 MID 文档级指令放在 front matter 之前；或仅使用本项目的 HTML 注释指令系统）
- 若在正文开始后再次出现文档级指令：默认 **忽略并 WARNING**（`--strict` 下可升级为 ERROR）
- 同一 key 在文件头部区域重复定义：默认 **WARNING + 后者覆盖前者**（建议保持单次定义）
- `--verbose`：输出“已收集文档级指令数量/键列表”，便于定位指令是否生效

| 指令 | 值 | 说明 | 默认值 |
|---|---|---|---|
| `documentclass` | 类名 | 文档类 | `article` |
| `classoptions` | YAML 序列 | 文档类选项 | `[12pt, a4paper]` |
| `packages` | YAML 序列 | 额外宏包 | `[amsmath, graphicx]` |
| `package-options` | YAML 映射 | 带选项的宏包 | — |
| `bibliography` | bib 文件路径 | 参考文献 | — |
| `bibstyle` | 样式名 | 文献样式 | `plain` |
| `title` | 字符串 | 论文标题 | — |
| `author` | 字符串 | 作者 | — |
| `date` | 字符串 | 日期 | `\today` |
| `abstract` | YAML 块标量 | 摘要（建议用 `|`） | — |
| `preamble` | YAML 块标量 | 追加到 preamble 末尾（建议用 `|`） | — |
| `latex-mode` | `full` / `body` / `fragment` | LaTeX 输出范围 | `full` |
| `bibliography-mode` | `auto` / `standalone` / `external` / `none` | bibliography 输出策略 | `auto` |

**补充说明**：

- `bibliography-mode: auto` 的推荐行为：
  - `latex-mode: full` → 等价于 `standalone`
  - `latex-mode: body|fragment` → 等价于 `external`
- 文档内指令与外部配置文件可同时存在，最终以优先级链（§10.1）合并，CLI 参数最高优先级。

**package-options 示例**：

```markdown
<!-- package-options:
  geometry: "margin=1in"
  hyperref: "colorlinks=true,linkcolor=blue"
-->
```

→

```latex
\usepackage[margin=1in]{geometry}
\usepackage[colorlinks=true,linkcolor=blue]{hyperref}
```

#### 4.2.2 块级指令

| 指令 | 附着方向 | 适用目标 | 说明 |
|---|---|---|---|
| `label` | ↑ 前一个节点 | heading, figure, table, math_block, environment | 生成 `\label{}` |
| `caption` | ↑ 前一个节点 | figure, table, environment | 生成 `\caption{}`（对环境则注入到环境内部） |
| `width` | ↑ 前一个节点 | figure | `\includegraphics` 的 width 参数 |
| `placement` | ↑ 前一个节点 | figure, table | 浮动位置，如 `htbp` |
| `begin` | 向下，直到 `end` | 任意 | 开始 LaTeX 环境 |
| `end` | 向上，匹配 `begin` | 任意 | 结束 LaTeX 环境 |
| `include-tex` | — | — | 将外部 `.tex` 文件内容插入为 `raw_block`（复杂表格/复杂排版的 fallback） |
| `options` | ↑ 前一个节点 | environment | 环境的可选参数（方括号 `[...]`，值建议为字符串） |
| `args` | ↑ 前一个节点 | environment | 环境的必选参数（花括号 `{...}`，值建议为 YAML 序列） |
| `centering` | ↑ 前一个节点 | figure, table, environment | 是否居中，默认 `true`（对 `figure/table` 或同名环境生效） |

**Raw LaTeX 透传区间**：使用 `begin/end` 的保留值 `raw`：

```markdown
<!-- begin: raw -->
\newcommand{\myop}[1]{\operatorname{#1}}
<!-- end: raw -->
```

**外部 `.tex` 片段引入**（可选扩展）：

```markdown
<!-- include-tex: tables/complex.tex -->
```

建议约定：

- 路径默认相对当前输入文件目录解析
- 为安全起见可限制为 project root 之下（或显式允许的 include roots）

#### 4.2.3 复杂排版示例：子图（Subfigure）

学术写作常见的子图排版可以用 `begin/end` 环境与 `args` 指令表达，且不需要扩展 Markdown 语法。

> 约定：想把 `caption/label` 附着到某个 `begin/end` 环境上，推荐把指令放在该环境的 `end` 之后（这样“向上附着”能命中环境节点）。Renderer 渲染环境时会把 `caption/label` 注入到环境内部合适位置。

```markdown
<!-- begin: figure -->
<!-- options: htbp -->
<!-- centering: true -->

<!-- begin: subfigure -->
<!-- options: b -->
<!-- args: [0.45\textwidth] -->
![图A](a.png)
<!-- end: subfigure -->
<!-- caption: 子图 A -->
<!-- label: fig:sub_a -->

\hfill

<!-- begin: subfigure -->
<!-- options: b -->
<!-- args: [0.45\textwidth] -->
![图B](b.png)
<!-- end: subfigure -->
<!-- caption: 子图 B -->
<!-- label: fig:sub_b -->

<!-- end: figure -->
<!-- caption: 主图标题 -->
<!-- label: fig:main -->
```

#### 4.2.4 AI 图片指令

针对 AI 生成图片的场景，扩展 figure 的 metadata。这些指令不影响 LaTeX 输出的主体结构，用于：

- 记录图片的生成参数，方便复现和修改
- 在 Rich Markdown 输出中展示 prompt 信息
- 未来可对接图片生成 API 自动化出图

```markdown
![点云配准流程示意图](figures/pipeline.png)
<!-- caption: 基于 4PCS 的点云配准流程 -->
<!-- label: fig:pipeline -->
<!-- width: 0.9\textwidth -->
<!-- ai-generated: true -->
<!-- ai-model: midjourney-v6 -->
<!-- ai-prompt: |
  Technical diagram showing point cloud registration pipeline,
  isometric 3D view, clean vector style, white background,
  showing: raw point cloud → keypoint extraction → congruent set matching → rigid transformation,
  arrows connecting each step, subtle blue-to-green gradient on point clouds,
  minimal labels, academic paper illustration style
-->
<!-- ai-negative-prompt: |
  photorealistic, cluttered, dark background, text heavy,
  low resolution, cartoon style, hand drawn
-->
<!-- ai-params: {seed: 42, steps: 50, cfg: 7.5, aspect: "16:9"} -->
```

**EAST 中的表示**：

```json
{
  "type": "figure",
  "src": "figures/pipeline.png",
  "alt": "点云配准流程示意图",
  "metadata": {
    "caption": "基于 4PCS 的点云配准流程",
    "label": "fig:pipeline",
    "width": "0.9\\textwidth",
    "ai": {
      "generated": true,
      "model": "midjourney-v6",
      "prompt": "Technical diagram showing point cloud registration pipeline...",
      "negative_prompt": "photorealistic, cluttered, dark background...",
      "params": {"seed": 42, "steps": 50, "cfg": 7.5, "aspect": "16:9"}
    }
  }
}
```

**LaTeX 输出**（AI 信息作为注释保留）：

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.9\textwidth]{figures/pipeline.png}
  \caption{基于 4PCS 的点云配准流程}
  \label{fig:pipeline}
  % AI Generated: midjourney-v6
  % Prompt: Technical diagram showing point cloud registration pipeline...
  % Negative: photorealistic, cluttered, dark background...
  % Params: seed=42, steps=50, cfg=7.5, aspect=16:9
\end{figure}
```

**Rich Markdown 输出**：

```html
<figure id="fig:pipeline" style="text-align:center">
  <img src="figures/pipeline.png" alt="点云配准流程示意图" style="max-width:90%">
  <figcaption><strong>图 3</strong>：基于 4PCS 的点云配准流程</figcaption>
  <details>
    <summary>🎨 AI Generation Info</summary>
    <p><strong>Model</strong>: midjourney-v6</p>
    <p><strong>Prompt</strong>: Technical diagram showing point cloud registration pipeline,
    isometric 3D view, clean vector style...</p>
    <p><strong>Negative</strong>: photorealistic, cluttered, dark background...</p>
    <p><strong>Params</strong>: seed=42, steps=50, cfg=7.5, aspect=16:9</p>
  </details>
</figure>
```

---

## 5. 引用与交叉引用

### 5.1 文献引用 (`\cite`)

#### 5.1.1 语法

```markdown
根据[Wang et al.](cite:wang2024)的研究...
已有多项工作[1-3](cite:wang2024,li2023,zhang2025)证明了这一点。
也支持空显示文本[](cite:wang2024)，用于避免手动维护显示格式。
```

链接文本（`Wang et al.`、`1-3`）是**显示文本**，仅用于 MID 源文件的可读性和 Rich Markdown 输出，LaTeX 输出时丢弃（由 `\cite` + bibstyle 自动生成格式）。显示文本允许为空（如 `[](cite:wang2024)`）。

#### 5.1.2 各 Backend 输出

| Backend | 输出 |
|---|---|
| **LaTeX** | `\cite{wang2024}` / `\cite{wang2024,li2023,zhang2025}` |
| **Rich MD** | 脚注 `Wang et al.[^wang2024]`，脚注内容尝试从 `.bib` 解析，否则输出 key |
| **HTML** | tooltip 或侧边栏显示文献信息 |

#### 5.1.3 扩展引用命令

对于 `\citeauthor`、`\citeyear`、`\parencite` 等变体，使用 query 参数语法：

```markdown
[Wang](cite:wang2024?cmd=citeauthor)在[2024年](cite:wang2024?cmd=citeyear)提出...
```

LaTeX 输出：`\citeauthor{wang2024} 在 \citeyear{wang2024} 提出...`

**或者直接透传**：`\citeauthor{wang2024}` 写在 Markdown 中，原样输出。

**可选简写（非 MVP，可讨论）**：

```markdown
[@wang2024]           # → \cite{wang2024}
[author@wang2024]     # → \citeauthor{wang2024}
[year@wang2024]       # → \citeyear{wang2024}

[citeauthor:wang2024] # → \citeauthor{wang2024}
```

### 5.2 交叉引用 (`\ref`)

#### 5.2.1 语法

```markdown
如[图1](ref:fig:result)所示...
见[第2章](ref:chap:method)...
由[公式3](ref:eq:einstein)可得...
```

#### 5.2.2 各 Backend 输出

| Backend | 输出 |
|---|---|
| **LaTeX** | `图~\ref{fig:result}` / `第~\ref{chap:method}章` |
| **Rich MD** | `<a href="#fig:result">图1</a>` 可点击跳转 |
| **HTML** | 同 Rich MD，带滚动高亮效果 |

#### 5.2.3 `\ref` 的波浪号处理

LaTeX 中 `\ref` 前通常加 `~`（不可断空格），但插入位置取决于上下文中文/英文语境：

- 英文：`Figure~\ref{fig:x}` → 波浪号在 Figure 和 `\ref` 之间
- 中文：`图~\ref{fig:x}` → 同上，但有些风格不需要

默认行为：在 `\ref` 前插入 `~`。可通过配置关闭：

```markdown
<!-- ref-tilde: false -->
```

### 5.3 脚注

```markdown
这是一段文字[^note1]。

[^note1]: 这是脚注内容，支持 **加粗** 和 *斜体*。
```

#### 5.3.1 建议的实现策略

- **两次扫描**：
  1. Pass 1 收集 `FootnoteDef`（`id -> content`），并统计 `FootnoteRef` 的引用次数
  2. Pass 2 渲染时在引用点展开脚注，且从输出中移除原始 `FootnoteDef` 节点
- **多次引用同一脚注 id**：
  - `--strict`：报错（避免在 LaTeX 中生成难以预测的重复脚注）
  - 非严格：默认 WARNING 并“重复展开”为多个脚注（实现简单、可预期）
  - 可选增强（后续）：第一次引用输出 `\footnote{\label{fn:<id>} ...}`，后续引用输出 `\textsuperscript{\ref{fn:<id>}}`

| Backend | 输出 |
|---|---|
| **LaTeX** | `\footnote{这是脚注内容，支持 \textbf{加粗} 和 \textit{斜体}。}` |
| **Rich MD** | 标准 Markdown 脚注语法，原样保留 |

---

## 6. Comment Processor 详细设计

### 6.1 注释解析

Comment Processor 将每个 HTML 注释节点视为一段“可解析的 YAML”，并要求其解析结果是一个 **key/value 映射**（推荐每个注释只包含一个 key，便于就近附着）。

解析实现建议：

- YAML 解析库：推荐 `ruamel.yaml`（对块标量 `|`/`>` 更友好，且更易保留换行语义）
- 单注释单指令：每个注释必须解析为 **仅包含 1 个 key 的映射**
  - 若解析得到多个 key：默认 WARNING 并仅取第一个（`--strict` 下 ERROR）
  - 若 value 为 `null`（如 `<!-- label: -->`）：默认 WARNING 并忽略该指令
  - 若 YAML 解析失败：默认 WARNING 并保留原注释节点（`--strict` 下 ERROR）

**解析步骤**：

1. 提取注释正文（去掉 `<!--` 与 `-->`）
2. 使用 YAML 解析得到映射（例如 `{"packages": ["amsmath", "graphicx"]}`）
3. 取出 `(directive, value)`，并做 key 归一化：
   - 对外 key 使用 `kebab-case`
   - 内部写入 EAST 前归一化为 `snake_case`

**AI 指令前缀**：以 `ai-` 开头的指令自动归入 `metadata.ai` 命名空间（例如 `ai-negative-prompt` → `metadata.ai.negative_prompt`）。

### 6.2 附着策略

```
遍历顺序: 从上到下遍历 AST 兄弟节点列表

对每个注释节点:
  1. 解析 directive 和 value
  2. 判断类型:

     文档级指令 (documentclass, packages, title, author, ...):
       → 仅在“文件头部区域”写入全局 document_metadata
       → 若已进入正文：WARNING 并忽略（`--strict` 可升级为 ERROR）

     向上附着 (label, caption, width, placement, ai-*, centering, options, args):
       → 向上回溯找到前一个“可附着节点”
          - 跳过 comment 节点
          - 跳过空段落/仅空白的节点（允许与目标之间存在空行）
       → 穿透规则（重要）：
          - 若候选节点是 paragraph，且其仅包含一个“有意义子节点”，则附着到该唯一子节点
            常见场景：`paragraph -> image`（独占一行的图片）、`paragraph -> math_inline`/`math_block`（取决于 parser）
       → 写入目标节点的 metadata[directive] = value
       → 从 AST 移除当前注释节点

     环境开始 (begin):
       → 扫描后续节点直到找到匹配的 end
       → 将区间内节点包裹为 environment 节点
       → environment.name = value
       → 若 begin 后紧跟环境级指令（如 options/args/centering），则写入 environment.metadata 并从 children 移除
       → 后续的 label/caption 等也可附着到此 environment（推荐写在 end 之后）
       → 移除 begin/end 注释节点

     透传开始 (begin: raw):
       → 扫描后续节点直到匹配的 end: raw
       → 将区间内容合并为 raw_block 节点
       → 移除 begin/end 注释节点

     外部片段 (include-tex):
       → 读取 value 指定的文件内容（建议相对输入文件目录解析）
       → 生成 raw_block 节点并替换当前注释节点

     输出控制 (latex-mode / bibliography-mode 等):
       → 写入全局配置
```

实现提示：`options/args/centering` 建议紧跟在对应 `<!-- begin: ... -->` 后（作为环境级元数据）；`caption/label` 建议写在对应 `<!-- end: ... -->` 后（便于“向上附着”命中 `environment` 节点）。

### 6.3 错误处理

| 场景 | 行为 |
|---|---|
| `begin` 无匹配 `end` | **报错**，指出行号和环境名 |
| `begin: raw` 无匹配 `end: raw` | **报错** |
| `include-tex` 文件不存在/不可读 | **报错**（或在非严格模式下 WARNING 并保留原注释节点） |
| `label` / `caption` 上方无可附着节点 | **警告**，指令被忽略 |
| 未知 directive | **警告**，保留为未处理的注释节点 |
| 重复的 `label` 值 | **警告**（LaTeX 编译时也会报） |
| AI 指令附着到非 figure 节点 | **警告**，仍保留在 metadata 中 |

---

## 7. LaTeX Renderer 详细设计

### 7.1 渲染器分发表

```python
RENDERER_MAP = {
    # 块级
    "document":      render_document,      # 顶层，处理 preamble 包裹
    "heading":       render_heading,        # → \section{} + \label{}
    "paragraph":     render_paragraph,      # → 段落文本 + \n\n
    "blockquote":    render_blockquote,     # → quotation 环境
    "list":          render_list,           # → itemize / enumerate
    "list_item":     render_list_item,      # → \item
    "code_block":    render_code_block,     # → lstlisting / minted
    "figure":        render_figure,         # → figure 环境 (含 AI 注释)
    "table":         render_table,          # → table + tabular 环境
    "math_block":    render_math_block,     # → \[...\] / equation(+label)
    "environment":   render_environment,    # → \begin{name}...\end{name}
    "raw_block":     render_raw_block,      # → 直接输出
    "thematic_break": render_thematic_break,# → \newpage / \hrule / 忽略

    # 行内
    "text":          render_text,           # → 转义特殊字符后的文本
    "strong":        render_strong,         # → \textbf{}
    "emphasis":      render_emphasis,       # → \textit{}
    "code_inline":   render_code_inline,    # → \texttt{} / \lstinline
    "math_inline":   render_math_inline,    # → $...$
    "link":          render_link,           # → \href / \cite / \ref (按 target 前缀)
    "image":         render_image,          # → \includegraphics (非 figure 上下文)
    "footnote_ref":  render_footnote_ref,   # → \footnote{}
    "softbreak":     render_softbreak,      # → 空格或换行
    "hardbreak":     render_hardbreak,      # → \\
}
```

**公式块渲染规则（建议）**：

- 若 `math_block.metadata.label` 存在：输出 `equation` 环境，并在环境内写入 `\label{...}`
- 否则：输出 `\[...\]`（避免强制编号）
- 对 `align`/`gather` 等特殊环境：优先用 `begin/end` 或 raw 透传

**表格渲染约束**：`render_table` 仅覆盖简单表格（见 §4.1.1）。遇到复杂表格（合并单元格/多行等）建议使用 `begin/end: raw` 直接透传 LaTeX 表格环境。

### 7.2 输出模式控制

```python
class LaTeXRenderer:
    def __init__(self, mode="full"):
        """
        mode:
          - "full":     完整文档，含 preamble + \begin{document} + body + \end{document}
          - "body":     仅 body 内容，不含任何包裹
          - "fragment": 最小片段，不生成 \section 等结构命令
        """
        self.mode = mode

    def render_document(self, node):
        body = self.render_children(node)

        if self.mode == "body":
            return body

        if self.mode == "fragment":
            return body  # fragment 模式下 heading 等节点的 render 行为也不同

        # full mode
        preamble = self.build_preamble(node.metadata)
        return f"{preamble}\n\\begin{{document}}\n\\maketitle\n\n{body}\n\\end{{document}}\n"
```

### 7.3 特殊字符转义

**目标**：对工具生成的 LaTeX 文本（普通段落等）做安全转义；对用户显式写入的 LaTeX（raw 区间、math、以及可识别的命令片段）尽量不干预。

**建议：转义策略可配置**（见 §10.2 `latex.escape`），支持白名单/黑名单/启发式三种模式。

**绝对豁免区（必须）**：

- `math_inline` / `math_block`：内部内容完全不做转义（`_`、`^`、`&` 等必须保留）
- `raw_block`：原样透传
- `code_inline` / `code_block`：不走普通文本转义流程，分别走 `\texttt` / `lstlisting|minted` 渲染

```python
LATEX_ESCAPE_MAP = {
    '#': r'\#',
    '$': r'\$',
    '%': r'\%',
    '&': r'\&',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
    '\\': r'\textbackslash{}',
}

def escape_latex(text: str) -> str:
    """对“纯文本片段”做单遍扫描转义，避免二次替换导致的错误转义。"""
    out = []
    for ch in text:
        out.append(LATEX_ESCAPE_MAP.get(ch, ch))
    return "".join(out)
```

**LaTeX 命令保护**：透传的 LaTeX 命令（如 `\cite{...}`、`\ref{...}`）不应被转义。建议把转义拆成两步：先“切分/保护”命令片段，再对剩余纯文本做转义。

```python
import re

def escape_latex_with_protection(text: str, cfg) -> str:
    """
    cfg.latex.escape.mode:
      - "whitelist": 仅保护 cfg.latex.escape.protect_commands 中列出的命令
      - "blacklist": 保护所有命令，除非在 blacklist 中
      - "heuristic": 保护所有看起来像 LaTeX 命令的片段（默认）
      - "off": 不做命令保护（不推荐）
    """
    protected = []
    def protect(match):
        protected.append(match.group(0))
        return f"\x00CMD{len(protected)-1}\x00"

    # 示例：启发式保护 \cmd, \cmd[opt]{arg} 这类常见形态（实现可随配置收紧/放宽）
    text = re.sub(r'\\[a-zA-Z@]+\\*?(\\[[^\\]]*\\])?(\\{[^{}]*\\})*', protect, text)

    text = escape_latex(text)

    for i, seg in enumerate(protected):
        text = text.replace(f"\x00CMD{i}\x00", seg)

    return text
```

---

## 8. Rich Markdown Renderer 详细设计

### 8.1 设计目标

输出一个在 GitHub / Obsidian / Typora 中渲染良好的标准 Markdown 文件，用 HTML 片段补充 Markdown 无法表达的语义。

### 8.2 转换规则

#### 8.2.0 预扫描（编号与索引）

为支持 **图/表自动编号**、**前向引用** 与 **引用/脚注集中输出**，Rich Markdown Renderer 建议采用两次扫描：

1. **Pass 1（Index）**：遍历 EAST，按出现顺序为 figure/table 分配编号，建立 `label -> number` 映射，并收集 citation keys、脚注定义等信息。
2. **Pass 2（Render）**：实际渲染时使用索引结果输出稳定的编号与脚注内容。

#### 8.2.1 交叉引用 → HTML 锚点

源文件中的 heading + label：

```markdown
## 研究方法
<!-- label: chap:method -->
```

输出：

```markdown
## 研究方法 {#chap:method}

<!-- 如果渲染器不支持 {#id} 语法，则输出： -->
<h2 id="chap:method">研究方法</h2>
```

引用处：

```markdown
见[第2章](ref:chap:method)
```

输出：

```markdown
见<a href="#chap:method">第2章</a>
```

**公式锚点**：若 `math_block` 带有 `label`，建议在 Rich Markdown 输出中为其生成锚点（例如在 `$$...$$` 前插入 `<a id="eq:transform"></a>`），以支持 `ref:` 跳转。

#### 8.2.2 文献引用 → 脚注

```markdown
根据[Wang et al.](cite:wang2024)的研究
```

输出：

```markdown
根据Wang et al.[^wang2024]的研究

[^wang2024]: Wang, et al. "Point Cloud Registration via 4PCS." CVPR, 2024.
```

空显示文本的情况：

- 源：`[](cite:wang2024)`
- 输出（默认）：`[^wang2024]`（仅脚注标记）
- 可选增强：若可解析 `.bib`，可用 author-year 作为显示文本（例如 `Wang et al., 2024[^wang2024]`）

建议策略（Rich Markdown）：

| 场景 | 建议输出 |
|---|---|
| `.bib` 可用且 key 存在，空显示文本 `[](cite:k)` | `Author, Year[^k]`（可配置 author-year/其他格式） |
| `.bib` 不可用或 key 缺失，空显示文本 | `[^k]` |
| 多 key `[](cite:k1,k2)` | `[^k1][^k2]`（默认不合并脚注，避免非标准 footnote id） |

实现提示：Pass 1 收集所有 cite keys → 解析 `.bib`（可缓存）→ Pass 2 对空显示文本的 citation 注入 display_text。

脚注内容来源优先级：

1. 解析 `bibliography` 指令指定的 `.bib` 文件，格式化为可读文本
2. 如果 `.bib` 不可用或找不到 key，输出 key 本身（如 `wang2024`）

#### 8.2.3 Figure → HTML figure 块

```markdown
![alt](path.png)
<!-- caption: xxx -->
<!-- label: fig:xxx -->
```

输出：

```html
<figure id="fig:xxx">
  <img src="path.png" alt="alt" style="max-width:100%">
  <figcaption><strong>图 N</strong>: xxx</figcaption>
</figure>
```

自动编号（`图 N`）建议由 Pass 1 统一分配，Pass 2 仅消费分配结果。

#### 8.2.4 Table → HTML table + caption

```markdown
| A | B |
|---|---|
| 1 | 2 |
<!-- caption: xxx -->
<!-- label: tab:xxx -->
```

输出：

```html
<figure id="tab:xxx">
  <table>
    <thead>
      <tr><th>A</th><th>B</th></tr>
    </thead>
    <tbody>
      <tr><td>1</td><td>2</td></tr>
    </tbody>
  </table>
  <figcaption><strong>表 N</strong>: xxx</figcaption>
</figure>
```

#### 8.2.5 Raw LaTeX → 折叠块

```markdown
<!-- begin: raw -->
\newcommand{\myop}[1]{\operatorname{#1}}
<!-- end: raw -->
```

输出：

````html
<details>
<summary>📄 Raw LaTeX</summary>

```latex
\newcommand{\myop}[1]{\operatorname{#1}}
```

</details>
````

#### 8.2.6 AI 图片信息 → 折叠块

见 §4.2.4 的 Rich Markdown 输出示例。

#### 8.2.7 文档级指令 → YAML Front Matter

```markdown
<!-- title: 基于 FPGA 的点云配准加速方法 -->
<!-- author: Wuchao -->
<!-- date: 2026 -->
```

输出到 Rich Markdown 文件头部：

```yaml
---
title: 基于 FPGA 的点云配准加速方法
author: Wuchao
date: 2026
---
```

---

## 9. CLI 设计

```
wenqiao <input> [options]

Arguments:
  input                    输入 .md 文件路径（支持 glob: chapters/*.md）

Output Target:
  -t, --target <target>    输出目标: latex | markdown | html  (默认: latex)
  -o, --output <path>      输出文件路径，支持 "-" 输出到 stdout（默认: 同名替换扩展名）

Output Options:
  --mode <mode>            输出模式: full | body | fragment  (默认: full)

LaTeX Options:
  --bibliography-mode <m>  bibliography 输出策略: auto | standalone | external | none  (默认: auto)
  --template <path>        LaTeX 模板文件 (.yaml)

Markdown Options:
  --bib <path>             BibTeX 文件路径（用于 Rich MD 脚注生成）
  --heading-id-style <s>   heading 锚点风格: attr ({#id}) | html (<h2 id>)
  --locale <lang>          图表标签语言: zh | en  (默认: zh)

General:
  --strict                 严格模式，不支持的语法报错
  --verbose                输出 EAST 中间结果
  --dump-ast               输出 Raw AST（调试用）
  --dump-east              输出 Enhanced AST（调试用）
  --config <path>          外部配置文件 (.yaml)
  -h, --help               帮助信息
  -v, --version            版本号
```

**使用示例**：

```bash
# 生成完整 LaTeX 文档
wenqiao paper.mid.md -o paper.tex

# 只生成 body 片段，嵌入已有 LaTeX 工程
wenqiao chapter3.mid.md -t latex --mode body -o chapter3.tex

# 生成 Rich Markdown 预览
wenqiao paper.mid.md -t markdown --bib refs.bib -o paper.rendered.md

# 批量转换
wenqiao chapters/*.mid.md -t latex --mode body -o build/

# 调试 AST
wenqiao paper.mid.md --dump-east
```

---

## 10. 配置系统

### 10.1 优先级（高 → 低）

```
CLI 参数  >  文档内注释  >  外部配置文件  >  模板文件  >  内置默认值
```

### 10.2 外部配置文件

```yaml
# wenqiao.yaml
default-target: latex

latex:
  mode: full
  bibliography-mode: auto      # auto | standalone | external | none
  documentclass: article
  classoptions: [12pt, a4paper]
  packages:
    - amsmath
    - graphicx
    - ctex
    - hyperref
  package-options:
    geometry: "margin=1in"
    hyperref: "colorlinks=true"
  bibstyle: IEEEtran
  thematic-break: newpage       # newpage | hrule | ignore
  code-style: lstlisting        # lstlisting | minted
  ref-tilde: true
  escape:
    enabled: true
    mode: heuristic             # heuristic | whitelist | blacklist | off
    protect-commands: [cite, ref, eqref, autoref, href, url]  # whitelist/blacklist 时使用
  fragment:
    preserve-structure: false

markdown:
  heading-id-style: attr        # attr | html
  figure-numbering: true
  table-numbering: true
  ai-info-display: details      # details | comment | hidden
  bib-format: apa               # apa | ieee | raw

html:
  math-engine: mathjax           # mathjax | katex
  theme: academic                # academic | minimal | dark
```

### 10.3 LaTeX 模板

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
  \def\BibTeX{{\rm B\kern-.05em{\sc i\kern-.025em b}\kern-.08em T\kern-.1667em\lower.7ex\hbox{E}\kern-.125emX}}
bibstyle: IEEEtran
```

```yaml
# templates/thesis-zju.yaml
documentclass: zjuthesis
classoptions: [doctor, chinese]
packages:
  - amsmath
  - algorithm2e
extra-preamble: |
  \zjusetup{
    author = {作者},
    title = {论文标题},
  }
```

---

## 11. EAST 节点类型定义

```
Node {
  type: string              # 节点类型
  children: Node[]          # 子节点（叶子节点为空）
  metadata: dict            # 注释指令注入的元信息
  position: {               # 源文件位置（用于错误报告）
    start: {line, column, offset?}
    end: {line, column, offset?}
  }
  raw: string               # 原始文本（仅叶子节点）
}

Document extends Node {
  type: "document"
  metadata: {
    documentclass, classoptions, packages, package_options,
    bibliography, bibstyle, title, author, date, abstract,
    preamble, latex_mode, bibliography_mode, ...
  }
}

Heading extends Node {
  type: "heading"
  level: 1-4
  metadata: {label?, ...}
}

Figure extends Node {
  type: "figure"
  src: string
  alt: string
  metadata: {
    caption?, label?, width?, placement?, centering?,
    ai?: {generated, model, prompt, negative_prompt, params}
  }
}

Table extends Node {
  type: "table"
  headers: Node[][]           # 表头单元格，包含行内节点
  alignments: ("left"|"center"|"right")[]
  rows: Node[][][]            # 数据行，包含单元格，单元格包含行内节点
  metadata: {caption?, label?, placement?}
}

Environment extends Node {
  type: "environment"
  name: string              # 环境名 (equation, algorithm, ...)
  children: Node[]          # 环境内的节点
  metadata: {label?, caption?, options?, args?, centering?}
}

Environment 渲染约定（LaTeX）：

- `options`：渲染为 `\begin{name}[<options>]`
- `args`：渲染为 `\begin{name}...{arg1}{arg2}`（按序追加多个花括号参数）
- `caption/label`：若环境支持（如 `figure/table/subfigure`），Renderer 可将其注入到环境内部合适位置

RawBlock extends Node {
  type: "raw_block"
  content: string           # 原始 LaTeX 文本
}

Citation extends Node {
  type: "citation"
  keys: string[]            # cite keys, e.g. ["wang2024", "li2023"]
  display_text: string      # 链接文本
  cmd: string               # 引用命令，默认 "cite"
}

CrossRef extends Node {
  type: "cross_ref"
  label: string             # ref label
  display_text: string      # 链接文本
}

# 其余标准节点: Paragraph, Strong, Emphasis, CodeInline, CodeBlock,
# MathInline, MathBlock, Link, List, ListItem, Blockquote,
# FootnoteRef, FootnoteDef, Text, SoftBreak, HardBreak, ThematicBreak
```

`position` 字段约定：

- `line` / `column`：**1-based**
- `offset`：可选，**0-based** 字符偏移（best-effort，取决于 parser 能否提供足够信息）

示例：

```json
{
  "position": {
    "start": {"line": 10, "column": 1, "offset": 245},
    "end": {"line": 10, "column": 20, "offset": 264}
  }
}
```

---

## 12. 错误与诊断

### 12.1 错误级别

| 级别 | 行为 | 示例 |
|---|---|---|
| **ERROR** | 终止转换 | `begin` 无匹配 `end`；输入文件不存在 |
| **WARNING** | 继续转换，输出提示 | 未知指令；label 重复；AI 指令附着到非 figure |
| **INFO** | 仅 `--verbose` 模式下显示 | 已处理的指令列表；AST 节点统计 |

### 12.2 诊断输出格式

```
[WARNING] paper.mid.md:42 - Unknown directive 'color', ignoring
[WARNING] paper.mid.md:78 - Label 'fig:result' attached to paragraph (expected figure/table/heading)
[ERROR]   paper.mid.md:120 - Unmatched '<!-- begin: algorithm -->', no corresponding '<!-- end: algorithm -->'
```

---

## 13. 完整示例

### 13.1 输入：paper.mid.md

```markdown
<!-- documentclass: article -->
<!-- classoptions: [12pt, a4paper] -->
<!-- packages: [amsmath, graphicx, ctex, hyperref, algorithm2e] -->
<!-- bibliography: refs.bib -->
<!-- bibstyle: IEEEtran -->
<!-- title: 基于 FPGA 的实时点云配准方法 -->
<!-- author: Wuchao -->
<!-- date: 2026 -->
<!-- abstract: |
  本文提出了一种基于 FPGA 的实时点云配准方法，
  通过硬件加速 4PCS 算法实现了 10 倍性能提升。
-->

# 绪论
<!-- label: sec:intro -->

点云配准是三维视觉领域的基础问题[Wang et al.](cite:wang2024)。
传统方法如 RANSAC[1](cite:fischler1981) 存在计算效率低的问题，
而 4PCS 方法[Aiger et al.](cite:aiger2008)提供了更优的理论保证。

本文的贡献如下：

1. 提出了一种适合 FPGA 实现的 4PCS 变体算法
2. 设计了流水线化的硬件架构
3. 在 ZCU102 平台上实现了实时处理

## 相关工作
<!-- label: sec:related -->

如[图1](ref:fig:pipeline)所示，现有方法可分为三类。

![点云配准流程](figures/pipeline.png)
<!-- caption: 点云配准方法分类与本文方法定位 -->
<!-- label: fig:pipeline -->
<!-- width: 0.85\textwidth -->
<!-- ai-generated: true -->
<!-- ai-model: dall-e-3 -->
<!-- ai-prompt: |
  Academic diagram showing taxonomy of point cloud registration methods,
  tree structure with three branches: correspondence-based, global, learning-based,
  clean minimal style, white background, blue accent color
-->
<!-- ai-negative-prompt: photorealistic, 3D render, complex -->

实验结果对比见[表1](ref:tab:results)。

| Method   | RMSE (cm) | Time (ms) | Platform |
|----------|-----------|-----------|----------|
| RANSAC   | 2.3       | 150       | CPU      |
| 4PCS     | 1.8       | 80        | CPU      |
| Ours     | 1.9       | 8         | FPGA     |
<!-- caption: 不同方法在 ModelNet40 数据集上的性能对比 -->
<!-- label: tab:results -->

由[公式1](ref:eq:transform)定义刚体变换：

$$
T = \begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix}
$$
<!-- label: eq:transform -->

## 结论

实验证明本文方法在保持精度的同时实现了 $10\times$ 加速，
详见[第2节](ref:sec:related)的分析。
```

### 13.2 输出：paper.tex（full mode）

```latex
\documentclass[12pt,a4paper]{article}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{ctex}
\usepackage{hyperref}
\usepackage{algorithm2e}
\bibliographystyle{IEEEtran}
\title{基于 FPGA 的实时点云配准方法}
\author{Wuchao}
\date{2026}

\begin{document}
\maketitle

\begin{abstract}
本文提出了一种基于 FPGA 的实时点云配准方法，
通过硬件加速 4PCS 算法实现了 10 倍性能提升。
\end{abstract}

\section{绪论}
\label{sec:intro}

点云配准是三维视觉领域的基础问题~\cite{wang2024}。
传统方法如 RANSAC~\cite{fischler1981} 存在计算效率低的问题，
而 4PCS 方法~\cite{aiger2008}提供了更优的理论保证。

本文的贡献如下：

\begin{enumerate}
  \item 提出了一种适合 FPGA 实现的 4PCS 变体算法
  \item 设计了流水线化的硬件架构
  \item 在 ZCU102 平台上实现了实时处理
\end{enumerate}

\subsection{相关工作}
\label{sec:related}

如图~\ref{fig:pipeline}所示，现有方法可分为三类。

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.85\textwidth]{figures/pipeline.png}
  \caption{点云配准方法分类与本文方法定位}
  \label{fig:pipeline}
  % AI Generated: dall-e-3
  % Prompt: Academic diagram showing taxonomy of point cloud registration methods...
  % Negative: photorealistic, 3D render, complex
\end{figure}

实验结果对比见表~\ref{tab:results}。

\begin{table}[htbp]
  \centering
  \caption{不同方法在 ModelNet40 数据集上的性能对比}
  \label{tab:results}
  \begin{tabular}{llll}
    \hline
    Method & RMSE (cm) & Time (ms) & Platform \\
    \hline
    RANSAC & 2.3 & 150 & CPU \\
    4PCS & 1.8 & 80 & CPU \\
    Ours & 1.9 & 8 & FPGA \\
    \hline
  \end{tabular}
\end{table}

由公式~\ref{eq:transform}定义刚体变换：

\begin{equation}
  T = \begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix}
  \label{eq:transform}
\end{equation}

\section{结论}

实验证明本文方法在保持精度的同时实现了 $10\times$ 加速，
详见第~\ref{sec:related}节的分析。

\bibliography{refs}

\end{document}
```

---

## 14. 开发计划

### Phase 1a: 核心管线（2–3 周）

**目标**：建立可运行的转换主干（MID → EAST → LaTeX），覆盖最常见正文结构，并输出可定位的诊断信息。

- [ ] 项目脚手架 + CLI 基本框架
- [ ] markdown-it-py Parser 接入（token stream / SyntaxTreeNode）
- [ ] 数学公式解析插件接入（`$...$` / `$$...$$` → `math_inline/math_block`）
- [ ] Comment Processor：YAML 注释解析、就近附着、begin/end 环境与 raw 区间
- [ ] EAST 最小节点集（document/heading/paragraph/text/strong/emphasis/code/math/link/break）
- [ ] LaTeX Renderer（最小节点集）
- [ ] 特殊字符转义策略（可配置，含命令保护）
- [ ] 诊断输出（ERROR/WARNING/INFO + position）

### Phase 1b: 引用与输出模式（1–2 周）

**目标**：打通论文写作关键能力：引用、交叉引用、standalone 与章节模式的输出差异。

- [ ] cite/ref 解析（`cite:` / `ref:` 前缀链接 → EAST 标记）
- [ ] `latex-mode`: `full` / `body` / `fragment`
- [ ] `bibliography-mode`: `auto` / `standalone` / `external` / `none`
- [ ] 文档级指令在 `full` 模式生效（title/author/abstract/documentclass/packages/preamble 等）
- [ ] `body/fragment` 模式下的“文档级指令忽略 + 警告”策略落地

### Phase 2: Rich Markdown MVP（预览优先）

**目标**：尽早形成“写作—预览—修订”的快速反馈闭环（GitHub/Obsidian/Typora 可读）。

- [ ] Rich Markdown Renderer 框架（两次扫描：Index/Render）
- [ ] ref → 锚点 + 可点击跳转
- [ ] cite → 脚注（可选解析 `.bib`）
- [ ] figure/table → HTML `figure/table` + caption/label + 自动编号
- [ ] begin/end raw → `<details>` 折叠块
- [ ] 文档级指令 → YAML front matter（可选）

### Phase 3: 完整论文要素（LaTeX 强化）

**目标**：覆盖常见论文元素，并更好支持工程式写作（章节拆分、主工程编译）。

- [ ] Figure 环境（caption/label/width/placement/centering）
- [ ] Table 环境（简单表格：GFM → `tabular`）
- [ ] 代码块（`lstlisting` / `minted`，可配置）
- [ ] 列表（含嵌套）、引用块（`quotation`）
- [ ] begin/end 自定义环境（含 `options`）
- [ ] 脚注策略定稿（见 §5.3.1）
- [ ] Fragment 模式细化
- [ ] 复杂表格/复杂片段：raw 透传（必要时可扩展“外部 `.tex` 片段引入”）

### Phase 4: 模板系统与 AI 元信息

**目标**：模板/配置体系完善，AI 元信息可记录、可展示、可复现。

- [ ] 模板系统（YAML 模板加载 + 合并）
- [ ] 配置系统（优先级链 + schema 校验）
- [ ] i18n/文案可配置（如图/表编号前缀、ref 前缀策略）
- [ ] AI 图片指令集（ai-prompt/ai-negative-prompt/ai-model/ai-params）
- [ ] AI 信息在 LaTeX 中输出为注释；在 Rich MD 中输出为 `<details>`
- [ ] 引用命令扩展语法（可选简写）
- [ ] `--strict` / `--dump-ast` / `--dump-east` 调试命令完善

### Phase 5: HTML Backend 与生态

**目标**：HTML 输出 + 工具链集成。

- [ ] HTML Renderer（MathJax/KaTeX、交叉引用跳转、文献 tooltip）
- [ ] 批量文件处理（glob 输入）
- [ ] 文件 watch 模式（文件变更自动重新转换）
- [ ] VS Code 扩展（语法高亮 + 预览）
- [ ] 与 AI 图片生成 API 集成（自动出图 pipeline，可选）

---

## 15. 测试策略

### 15.1 单元测试（Unit）

- Comment Processor：指令解析（YAML）、附着策略、begin/end 配对、错误与 WARNING 行为
- LaTeX Renderer：按节点类型的渲染快照（最小节点集 → 可预测输出）
- Rich Markdown Renderer：编号/索引（Pass 1）、渲染（Pass 2）与引用一致性
- escape：不同 `latex.escape.mode` 下的转义行为（白名单/黑名单/启发式）

### 15.2 集成测试（E2E）

- 固定输入样例：`.mid.md` → `.tex` / `.rendered.md` 的端到端转换（golden files）
- 多文件场景：章节拆分 + body 输出，验证生成物可被主工程 `\include{...}` 引用
- 错误场景：缺失 `end`、指令位置错误、重复 label 等，验证诊断文本稳定

### 15.3 回归测试套件（Regression）

- 收集“真实论文片段”作为 fixtures（含图/表/公式/引用/脚注/列表）
- 每次新增语法/指令时补充对应用例，避免破坏既有行为

---

## 16. 性能与规模（非 MVP 重点）

- 初期假设输入规模为“论文/学位论文级别”，不做流式解析与复杂缓存
- 后续可选优化：多文件并行转换、增量构建（仅重渲染变更文件）、缓存 `.bib` 解析结果
- 可选工具：`--profile` 输出各阶段耗时（Parser/Comment/Render），用于基准与回归
