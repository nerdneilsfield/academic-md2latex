# PRD: md-mid — 学术写作中间格式与多目标转换工具

## 1. 项目定位

### 1.1 核心思想

定义一种**基于 Markdown 的学术写作中间格式**（下称 md-mid），作为论文写作的单一源文件（single source of truth）。md-mid 不是标准 Markdown 的子集，而是一种**带语义注释的 Markdown 方言**，服务于两个输出目标：

```
                    ┌──→  LaTeX (.tex)     用于论文投稿、编译 PDF
                    │
  md-mid (.md)  ────┤
                    │
                    └──→  Rich Markdown / HTML (.md / .html)  用于预览、分享、博客
```

**关键洞察**：论文写作过程中，作者需要在"写"和"看"之间频繁切换。md-mid 让你用一份源文件同时满足这两个需求——LaTeX 输出用于最终排版，Rich Markdown/HTML 输出用于日常阅读、分享和版本管理。

### 1.2 设计原则

- **源文件即主体**：md-mid 文件本身应具备良好的可读性，即使不经过任何转换，裸读也能理解内容
- **双向不丢信息**：所有在 LaTeX 中需要表达的语义（label、caption、cite、ref……），都能在 Rich Markdown 输出中找到对应的可视化表达
- **渐进式采用**：最简情况下，一个纯 Markdown 文件就能直接转换，注释指令全部可选
- **LaTeX 透传**：任何时候都可以直接写 LaTeX 命令，工具原样输出，不报错不干涉
- **输出范围可控**：可以生成完整 `.tex` 文档，也可以只生成 `\begin{document}...\end{document}` 内部的 body 片段，方便嵌入已有的 LaTeX 工程

### 1.3 非目标

- 不做 LaTeX → Markdown 反向转换
- 不做 LaTeX 编译（交给 `xelatex` / `latexmk`）
- 不做实时编辑器或 WYSIWYG 界面
- 不处理 BibTeX 文件本身的管理

---

## 2. 系统架构

```
                         md-mid source (.md)
                                │
                                ▼
                     ┌─────────────────────┐
                     │    Markdown Parser   │   mistune / markdown-it-py / remark
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
| **Parser** | 调用第三方 Markdown parser，生成 Raw AST |
| **Comment Processor** | 注释解析、metadata 附着、环境节点生成、链接类型标记 |
| **LaTeX Backend** | EAST → LaTeX 字符串，支持 full / body-only 模式 |
| **Markdown Backend** | EAST → 渲染增强的 Markdown（cite→脚注，ref→锚点跳转，figure→居中图片块） |
| **HTML Backend** | EAST → 自包含 HTML 页面（可选，作为 Markdown Backend 的进阶版本） |
| **Template Manager** | 管理 LaTeX preamble 模板（documentclass、packages、自定义命令） |
| **Config Resolver** | 合并配置优先级：CLI args > 文档内注释 > 模板文件 > 默认值 |
| **CLI** | 命令行入口 |

---

## 3. 输出模式

### 3.1 LaTeX 输出

#### 3.1.1 Full Document 模式（默认）

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

#### 3.1.2 Body-only 模式

仅生成 `\begin{document}` 和 `\end{document}` 之间的内容，不含 preamble，不含 `\begin{document}` / `\end{document}` 本身：

```latex
\section{绪论}
\label{chap:intro}

这是正文...

\subsection{研究背景}
...
```

**使用场景**：

- 论文各章节拆分为独立的 md-mid 文件，通过主 `.tex` 文件 `\input{chapter1}` 引入
- 已有 LaTeX 工程，只想用 md-mid 写某个章节的内容
- 与 Overleaf 等在线 LaTeX 编辑器配合，主文件在 Overleaf 维护，章节内容用 md-mid 生成

#### 3.1.3 Fragment 模式

更极端的片段模式：不生成 `\section` 等结构命令，只转换行内和基本块级元素。用于在 LaTeX 文档中嵌入一小段由 Markdown 写成的内容。

### 3.2 Rich Markdown 输出

将 md-mid 转换为标准 Markdown + 少量 HTML，使其在 GitHub / Obsidian / Typora 等环境下渲染良好。

核心转换规则：

| md-mid 语义 | Rich Markdown 输出 |
|---|---|
| `[text](cite:key)` | 脚注 `[^key]`，脚注内容为 BibTeX 条目或 key 本身 |
| `[text](ref:label)` | HTML 锚点跳转 `<a href="#label">text</a>` |
| `<!-- label: xxx -->` | 在目标元素上生成 `<a id="xxx"></a>` 锚点 |
| `<!-- caption: xxx -->` | 图片/表格下方生成居中的 caption 文字 |
| figure 指令组 | 居中图片 + caption + 编号 |
| table 指令组 | 表格 + caption + 编号 |
| `<!-- begin: equation -->` | 公式块，保留 `$$...$$` 或输出 MathJax-friendly 格式 |
| `<!-- raw -->...<!-- endraw -->` | 折叠块 `<details>` 显示原始 LaTeX 代码 |
| AI 图片 prompt | 折叠块展示 prompt 信息，或以 HTML comment 保留 |
| 文档级指令 | 生成 YAML front matter（供 Jekyll/Hugo 等使用） |

**示例**：

md-mid 源文件：
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

## 4. md-mid 语法规范

### 4.1 Markdown 基础语法（支持子集）

#### 4.1.1 块级元素

| 语法 | LaTeX 输出 | Rich MD 输出 |
|---|---|---|
| `# H1` | `\section{H1}` | `# H1` + 锚点 |
| `## H2` | `\subsection{H2}` | `## H2` + 锚点 |
| `### H3` | `\subsubsection{H3}` | `### H3` + 锚点 |
| `#### H4` | `\paragraph{H4}` | `#### H4` |
| 段落 | 段落 | 段落 |
| `> quote` | `\begin{quotation}` | `> quote` |
| `- item` | `\begin{itemize}` | `- item` |
| `1. item` | `\begin{enumerate}` | `1. item` |
| 代码块 | `\begin{lstlisting}` | 代码块 |
| `![](path)` | `\begin{figure}` | 居中图片 + caption |
| 表格 | `\begin{table}` + `\begin{tabular}` | 表格 + caption |
| `---` | 可配置：`\newpage` / `\hrule` / 忽略 | `---` |

#### 4.1.2 行内元素

| 语法 | LaTeX | Rich MD |
|---|---|---|
| `**bold**` | `\textbf{}` | `**bold**` |
| `*italic*` | `\textit{}` | `*italic*` |
| `` `code` `` | `\texttt{}` | `` `code` `` |
| `$formula$` | `$formula$` 透传 | `$formula$` |
| `$$block$$` | `\begin{equation}` 或 `\[...\]` | `$$block$$` |
| `[t](url)` | `\href{url}{t}` | `[t](url)` |
| `[t](cite:k)` | `\cite{k}` | 脚注 `[^k]` |
| `[t](ref:l)` | `\ref{l}` | `<a href="#l">t</a>` |
| LaTeX 命令 | 透传 | `<details>` 折叠 或 原样保留 |

### 4.2 注释指令系统

统一格式：`<!-- directive: value -->`

支持单行和多行值：

```markdown
<!-- directive: single line value -->

<!-- directive:
  multi
  line
  value
-->
```

#### 4.2.1 文档级指令

在文件开头（第一个正文内容之前）声明。

| 指令 | 值 | 说明 | 默认值 |
|---|---|---|---|
| `documentclass` | 类名 | 文档类 | `article` |
| `classoptions` | 逗号分隔 | 文档类选项 | `12pt, a4paper` |
| `packages` | 逗号分隔 | 额外宏包 | `amsmath, graphicx` |
| `package-options` | JSON-like | 带选项的宏包 | — |
| `bibliography` | bib 文件路径 | 参考文献 | — |
| `bibstyle` | 样式名 | 文献样式 | `plain` |
| `title` | 字符串 | 论文标题 | — |
| `author` | 字符串 | 作者 | — |
| `date` | 字符串 | 日期 | `\today` |
| `abstract` | 多行文本 | 摘要 | — |
| `preamble` | 多行 LaTeX | 追加到 preamble 末尾 | — |
| `output` | `full` / `body` / `fragment` | LaTeX 输出范围 | `full` |

**package-options 示例**：

```markdown
<!-- package-options: {geometry: "margin=1in", hyperref: "colorlinks=true,linkcolor=blue"} -->
```

→

```latex
\usepackage[margin=1in]{geometry}
\usepackage[colorlinks=true,linkcolor=blue]{hyperref}
```

#### 4.2.2 块级指令

| 指令 | 附着方向 | 适用目标 | 说明 |
|---|---|---|---|
| `label` | ↑ 前一个节点 | heading, figure, table, equation | 生成 `\label{}` |
| `caption` | ↑ 前一个节点 | figure, table | 生成 `\caption{}` |
| `width` | ↑ 前一个节点 | figure | `\includegraphics` 的 width 参数 |
| `placement` | ↑ 前一个节点 | figure, table | 浮动位置，如 `htbp` |
| `begin` | 向下，直到 `end` | 任意 | 开始 LaTeX 环境 |
| `end` | 向上，匹配 `begin` | 任意 | 结束 LaTeX 环境 |
| `raw` | 向下，直到 `endraw` | — | 原始 LaTeX 透传开始 |
| `endraw` | — | — | 原始 LaTeX 透传结束 |
| `options` | ↑ 前一个节点 | 任意环境 | 环境的可选参数 |
| `centering` | ↑ 前一个节点 | figure, table | 是否居中，默认 `true` |

#### 4.2.3 AI 图片指令

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
<!-- ai-prompt:
  Technical diagram showing point cloud registration pipeline,
  isometric 3D view, clean vector style, white background,
  showing: raw point cloud → keypoint extraction → congruent set matching → rigid transformation,
  arrows connecting each step, subtle blue-to-green gradient on point clouds,
  minimal labels, academic paper illustration style
-->
<!-- ai-negative-prompt:
  photorealistic, cluttered, dark background, text heavy,
  low resolution, cartoon style, hand drawn
-->
<!-- ai-params: {seed: 42, steps: 50, cfg: 7.5, aspect: 16:9} -->
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
```

链接文本（`Wang et al.`、`1-3`）是**显示文本**，仅用于 md-mid 源文件的可读性和 Rich Markdown 输出，LaTeX 输出时丢弃（由 `\cite` + bibstyle 自动生成格式）。

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

| Backend | 输出 |
|---|---|
| **LaTeX** | `\footnote{这是脚注内容，支持 \textbf{加粗} 和 \textit{斜体}。}` |
| **Rich MD** | 标准 Markdown 脚注语法，原样保留 |

---

## 6. Comment Processor 详细设计

### 6.1 注释解析

**单行注释**：

```
正则: /^<!--\s*([\w-]+)\s*:\s*(.+?)\s*-->$/s
捕获: (directive, value)
```

**多行注释**：

```
正则: /^<!--\s*([\w-]+)\s*:\s*\n([\s\S]+?)\s*-->$/
捕获: (directive, multiline_value)
```

**AI 指令前缀**：以 `ai-` 开头的指令自动归入 `metadata.ai` 命名空间。

### 6.2 附着策略

```
遍历顺序: 从上到下遍历 AST 兄弟节点列表

对每个注释节点:
  1. 解析 directive 和 value
  2. 判断类型:

     文档级指令 (documentclass, packages, title, author, ...):
       → 写入全局 document_metadata

     向上附着 (label, caption, width, placement, ai-*, centering, options):
       → 找前一个非注释兄弟节点
       → 写入该节点的 metadata[directive] = value
       → 从 AST 移除当前注释节点

     环境开始 (begin):
       → 扫描后续节点直到找到匹配的 end
       → 将区间内节点包裹为 environment 节点
       → environment.name = value
       → 后续的 label, caption 等指令附着到此 environment
       → 移除 begin/end 注释节点

     透传开始 (raw):
       → 扫描后续节点直到 endraw
       → 将区间内容合并为 raw_block 节点
       → 移除 raw/endraw 注释节点

     输出控制 (output):
       → 写入全局配置
```

### 6.3 错误处理

| 场景 | 行为 |
|---|---|
| `begin` 无匹配 `end` | **报错**，指出行号和环境名 |
| `raw` 无匹配 `endraw` | **报错** |
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
    "math_block":    render_math_block,     # → equation / \[...\]
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

def escape_latex(text: str, in_math: bool = False) -> str:
    """转义 LaTeX 特殊字符。公式环境内不转义。"""
    if in_math:
        return text
    for char, replacement in LATEX_ESCAPE_MAP.items():
        text = text.replace(char, replacement)
    return text
```

**LaTeX 命令保护**：透传的 LaTeX 命令（以 `\` 开头后跟字母）不应被转义。需要一个启发式规则：

```python
import re

def escape_latex_smart(text: str) -> str:
    """转义特殊字符，但保留 LaTeX 命令（如 \cite, \ref）不被转义。"""
    # 先提取 LaTeX 命令，用占位符替换
    commands = []
    def save_command(match):
        commands.append(match.group(0))
        return f"\x00CMD{len(commands)-1}\x00"

    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}|\\[a-zA-Z]+', save_command, text)

    # 转义剩余特殊字符
    text = escape_latex(text)

    # 恢复 LaTeX 命令
    for i, cmd in enumerate(commands):
        text = text.replace(f"\x00CMD{i}\x00", cmd)

    return text
```

---

## 8. Rich Markdown Renderer 详细设计

### 8.1 设计目标

输出一个在 GitHub / Obsidian / Typora 中渲染良好的标准 Markdown 文件，用 HTML 片段补充 Markdown 无法表达的语义。

### 8.2 转换规则

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

#### 8.2.2 文献引用 → 脚注

```markdown
根据[Wang et al.](cite:wang2024)的研究
```

输出：

```markdown
根据Wang et al.[^wang2024]的研究

[^wang2024]: Wang, et al. "Point Cloud Registration via 4PCS." CVPR, 2024.
```

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

自动编号（`图 N`）由 Renderer 维护全局计数器。

#### 8.2.4 Table → 表格 + caption

```markdown
| A | B |
|---|---|
| 1 | 2 |
<!-- caption: xxx -->
<!-- label: tab:xxx -->
```

输出：

```html
<div id="tab:xxx">

| A | B |
|---|---|
| 1 | 2 |

<p style="text-align:center"><strong>表 N</strong>: xxx</p>
</div>
```

#### 8.2.5 Raw LaTeX → 折叠块

```markdown
<!-- raw -->
\newcommand{\myop}[1]{\operatorname{#1}}
<!-- endraw -->
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

见 §4.2.3 的 Rich Markdown 输出示例。

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
md-mid <input> [options]

Arguments:
  input                    输入 .md 文件路径（支持 glob: chapters/*.md）

Output Target:
  -t, --target <target>    输出目标: latex | markdown | html  (默认: latex)
  -o, --output <path>      输出文件路径（默认: 同名替换扩展名）

LaTeX Options:
  --mode <mode>            输出模式: full | body | fragment  (默认: full)
  --template <path>        LaTeX 模板文件 (.yaml)

Markdown Options:
  --bib <path>             BibTeX 文件路径（用于 Rich MD 脚注生成）
  --heading-id-style <s>   heading 锚点风格: attr ({#id}) | html (<h2 id>)

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
md-mid paper.md -o paper.tex

# 只生成 body 片段，嵌入已有 LaTeX 工程
md-mid chapter3.md -t latex --mode body -o chapter3.tex

# 生成 Rich Markdown 预览
md-mid paper.md -t markdown --bib refs.bib -o paper.rendered.md

# 批量转换
md-mid chapters/*.md -t latex --mode body -o build/

# 调试 AST
md-mid paper.md --dump-east
```

---

## 10. 配置系统

### 10.1 优先级（高 → 低）

```
CLI 参数  >  文档内注释  >  外部配置文件  >  模板文件  >  内置默认值
```

### 10.2 外部配置文件

```yaml
# md-mid.yaml
default_target: latex

latex:
  mode: full
  documentclass: article
  classoptions: [12pt, a4paper]
  packages:
    - amsmath
    - graphicx
    - ctex
    - hyperref
  package_options:
    geometry: "margin=1in"
    hyperref: "colorlinks=true"
  bibstyle: IEEEtran
  thematic_break: newpage       # newpage | hrule | ignore
  code_style: lstlisting        # lstlisting | minted
  ref_tilde: true

markdown:
  heading_id_style: attr        # attr | html
  figure_numbering: true
  table_numbering: true
  ai_info_display: details      # details | comment | hidden
  bib_format: apa               # apa | ieee | raw

html:
  math_engine: mathjax           # mathjax | katex
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
extra_preamble: |
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
extra_preamble: |
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
    start: {line, column}
    end: {line, column}
  }
  raw: string               # 原始文本（仅叶子节点）
}

Document extends Node {
  type: "document"
  metadata: {
    documentclass, classoptions, packages, package_options,
    bibliography, bibstyle, title, author, date, abstract,
    preamble, output, ...
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
  headers: string[]
  alignments: ("left"|"center"|"right")[]
  rows: string[][]
  metadata: {caption?, label?, placement?}
}

Environment extends Node {
  type: "environment"
  name: string              # 环境名 (equation, algorithm, ...)
  children: Node[]          # 环境内的节点
  metadata: {label?, caption?, options?}
}

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
[WARNING] paper.md:42 - Unknown directive 'color', ignoring
[WARNING] paper.md:78 - Label 'fig:result' attached to paragraph (expected figure/table/heading)
[ERROR]   paper.md:120 - Unmatched '<!-- begin: algorithm -->', no corresponding '<!-- end: algorithm -->'
```

---

## 13. 完整示例

### 13.1 输入：paper.md

```markdown
<!-- documentclass: article -->
<!-- classoptions: 12pt, a4paper -->
<!-- packages: amsmath, graphicx, ctex, hyperref, algorithm2e -->
<!-- bibliography: refs.bib -->
<!-- bibstyle: IEEEtran -->
<!-- title: 基于 FPGA 的实时点云配准方法 -->
<!-- author: Wuchao -->
<!-- date: 2026 -->
<!-- abstract:
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
<!-- ai-prompt:
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

<!-- begin: equation -->
T = \begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix}
<!-- end: equation -->
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

### Phase 1: Core（MVP）

**目标**：能将一篇简单论文从 md-mid 转为可编译的 LaTeX。

- [ ] 项目脚手架 + CLI 基本框架
- [ ] Markdown Parser 接入（选定 parser 库）
- [ ] Comment Processor：单行注释解析、向上附着
- [ ] LaTeX Renderer：heading, paragraph, strong, emphasis, code_inline, math 透传
- [ ] `\cite` / `\ref` 链接语法
- [ ] Full / Body 输出模式
- [ ] 文档级指令：documentclass, packages, title, author
- [ ] 特殊字符转义（含 LaTeX 命令保护）
- [ ] 基本错误报告

### Phase 2: 完整论文要素

**目标**：支持所有常见论文元素。

- [ ] Figure 环境（caption, label, width, placement）
- [ ] Table 环境（caption, label, GFM → tabular）
- [ ] 代码块 → lstlisting / minted
- [ ] 列表（itemize / enumerate，含嵌套）
- [ ] 引用块 → quotation
- [ ] begin/end 自定义环境
- [ ] raw/endraw 透传区间
- [ ] 脚注
- [ ] bibliography 自动插入
- [ ] Fragment 输出模式
- [ ] 多行注释值支持

### Phase 3: Rich Markdown Backend

**目标**：md-mid → 渲染良好的 Markdown。

- [ ] Rich Markdown Renderer 框架
- [ ] cite → 脚注（含 .bib 解析）
- [ ] ref → HTML 锚点跳转
- [ ] figure → HTML figure 块 + 自动编号
- [ ] table → 表格 + caption + 编号
- [ ] raw → 折叠块
- [ ] 文档级指令 → YAML front matter

### Phase 4: AI 图片与增强

**目标**：AI 图片元信息、模板系统、高级配置。

- [ ] AI 图片指令集（ai-prompt, ai-negative-prompt, ai-model, ai-params）
- [ ] AI 信息在 LaTeX 中输出为注释
- [ ] AI 信息在 Rich MD 中输出为折叠块
- [ ] 模板系统（YAML 模板加载 + 合并）
- [ ] 配置系统（优先级链）
- [ ] 扩展引用命令（citeauthor, citeyear 等 query 参数）
- [ ] --strict 模式
- [ ] --dump-ast / --dump-east 调试命令

### Phase 5: HTML Backend 与生态

**目标**：HTML 输出 + 工具链集成。

- [ ] HTML Renderer（MathJax, 交叉引用跳转, 文献 tooltip）
- [ ] 批量文件处理（glob 输入）
- [ ] 文件 watch 模式（文件变更自动重新转换）
- [ ] VS Code 扩展（语法高亮 + 预览）
- [ ] 与 AI 图片生成 API 集成（自动出图 pipeline，可选）
