# `.mid.md` Format Specification / `.mid.md` 格式规范

> Version 1.0 — Wenqiao (文桥): Academic Markdown Intermediate Format

## Overview / 概述

`.mid.md` is a superset of CommonMark Markdown designed for academic writing. It adds
structured metadata via HTML comments (`<!-- key: value -->`), LaTeX-style citations
and cross-references via link syntax, and dollar-sign math delimiters.

`.mid.md` 是 CommonMark Markdown 的超集，专为学术写作设计。通过 HTML 注释添加结构化元数据，
通过链接语法实现 LaTeX 风格的引用和交叉引用，并支持美元符号数学公式。

A `.mid.md` file is valid Markdown — it renders correctly in any Markdown viewer,
while carrying enough semantic information to generate LaTeX, HTML, or
round-trip Markdown output.

---

## 1. File Structure / 文件结构

A `.mid.md` document has two regions:

```
┌──────────────────────────────┐
│  Header Region (文档头部区域)  │  ← Document-level directives only
│  <!-- documentclass: ... -->  │
│  <!-- title: ... -->          │
│  <!-- abstract: | ... -->     │
├──────────────────────────────┤
│  Body Region (正文区域)       │  ← Markdown content + inline directives
│  # Introduction               │
│  <!-- label: sec:intro -->    │
│  ...                          │
└──────────────────────────────┘
```

The **header region** is everything before the first non-comment content node.
Once a heading, paragraph, or any content appears, the header region ends.

---

## 2. Document-Level Directives / 文档级指令

These directives MUST appear in the header region. They configure the output document.

| Directive | Type | Description (描述) | Example |
|-----------|------|-------|---------|
| `documentclass` | `string` | LaTeX document class (文档类) | `article`, `report`, `IEEEtran` |
| `classoptions` | `list` | Class options (类选项) | `[12pt, a4paper, twocolumn]` |
| `packages` | `list` | LaTeX packages to load (额外宏包) | `[amsmath, graphicx, ctex]` |
| `package-options` | `dict` | Per-package options (宏包选项) | `{hyperref: [colorlinks]}` |
| `bibliography` | `string` | BibTeX file path (参考文献文件) | `refs.bib` |
| `bibstyle` | `string` | Bibliography style (参考文献样式) | `IEEEtran`, `plainnat` |
| `title` | `string` | Document title (标题) | any text |
| `author` | `string` | Author(s) (作者) | any text |
| `date` | `string` | Date (日期) | `2026`, `2026-03-05` |
| `abstract` | `string` | Abstract text (摘要), use YAML `\|` for multiline | see below |
| `preamble` | `string` | Raw LaTeX preamble (原始 LaTeX 前言) | `\newcommand{...}` |
| `latex-mode` | `string` | LaTeX compilation mode (编译模式) | `pdflatex`, `xelatex` |
| `bibliography-mode` | `string` | Bibliography compilation mode (文献编译模式) | `bibtex`, `biber` |

### Multiline abstract example / 多行摘要示例

```markdown
<!-- abstract: |
  This paper proposes a novel method for point cloud registration.
  We achieve 10x speedup on FPGA platforms.
-->
```

### Full header example / 完整头部示例

```markdown
<!-- documentclass: article -->
<!-- classoptions: [12pt, a4paper] -->
<!-- packages: [amsmath, graphicx, ctex, hyperref, algorithm2e] -->
<!-- bibliography: refs.bib -->
<!-- bibstyle: IEEEtran -->
<!-- title: A Survey on Point Cloud Registration -->
<!-- author: Zhang San, Li Si -->
<!-- date: 2026 -->
<!-- abstract: |
  This survey reviews point cloud registration methods
  including ICP and its variants, with emphasis on
  hardware acceleration techniques.
-->
```

---

## 3. Headings / 标题

Standard Markdown ATX headings. Use `<!-- label: ... -->` on the next line to add
a LaTeX label.

```markdown
# Introduction
<!-- label: sec:intro -->

## Related Work
<!-- label: sec:related -->

### ICP Algorithm
<!-- label: sec:icp -->
```

Maps to LaTeX `\section{...}\label{...}`, `\subsection{...}`, etc.

---

## 4. Paragraphs and Inline Formatting / 段落与行内格式

Standard Markdown:

| Syntax | Rendering | LaTeX |
|--------|-----------|-------|
| `**bold**` | **bold** | `\textbf{bold}` |
| `*italic*` | *italic* | `\textit{italic}` |
| `` `code` `` | `code` | `\texttt{code}` |
| `[text](url)` | link | `\href{url}{text}` |

---

## 5. Math / 数学公式

### Inline math / 行内公式

```markdown
The transform $T \in SE(3)$ maps source to target.
```

Renders: The transform $T \in SE(3)$ maps source to target.

### Block math / 行间公式

```markdown
$$
\min_{R,t} \sum_{i=1}^{n} \| R p_i + t - q_i \|^2
$$
<!-- label: eq:icp-objective -->
```

The `<!-- label: eq:... -->` after a math block creates a numbered equation
(`\begin{equation}...\label{eq:...}\end{equation}`).

Math blocks without labels produce unnumbered equations (`\[...\]`).

---

## 6. Citations / 引用

Citations use Markdown link syntax with `cite:` URL scheme:

```markdown
[Author et al.](cite:key)
```

Bare shortcut syntax is also supported:

```markdown
[cite:wang2024]
[cite:wang2024?cmd=citet]
```

The bare cite shortcut behaves like an empty-display citation.

裸速记语法同样支持；其行为等价于空显示文本的引用。

### Citation variants / 引用变体

| Syntax | LaTeX | Description |
|--------|-------|-------------|
| `[Wang](cite:wang2024)` | `\cite{wang2024}` | Default cite |
| `[1-3](cite:a,b,c)` | `\cite{a,b,c}` | Multiple keys |
| `[Wang](cite:wang2024?cmd=citet)` | `\citet{wang2024}` | Textual cite |
| `[Wang](cite:wang2024?cmd=citep)` | `\citep{wang2024}` | Parenthetical cite |
| `[Wang](cite:wang2024?cmd=citeauthor)` | `\citeauthor{wang2024}` | Author only |
| `[2024](cite:wang2024?cmd=citeyear)` | `\citeyear{wang2024}` | Year only |

### Valid `?cmd=` values / 合法引用命令

`cite`, `citep`, `citet`, `citeauthor`, `citeyear`, `textcite`, `parencite`, `autocite`

---

## 7. Cross-References / 交叉引用

Cross-references use Markdown link syntax with `ref:` URL scheme:

```markdown
As shown in [Figure 1](ref:fig:pipeline), the method...
See [Section 2](ref:sec:related) for details.
Equation [1](ref:eq:transform) defines the transform.
```

Bare shortcut syntax is also supported:

```markdown
[ref:fig:pipeline]
[ref:eq:transform]
```

Generates `\ref{label}` in LaTeX. The display text is kept for Markdown/HTML output.

For bare ref shortcuts, the label itself is used as display text in Markdown/HTML output.

对于裸 ref 速记，Markdown/HTML 输出中的显示文本默认就是 label 本身。

---

## 8. Figures / 图片

Standard Markdown image syntax, with metadata comments attached below:

```markdown
![Alt text](figures/pipeline.png)
<!-- caption: Pipeline overview of the proposed method -->
<!-- label: fig:pipeline -->
<!-- width: 0.85\textwidth -->
<!-- placement: h -->
```

### Attach-up directives for figures / 图片附着指令

| Directive | Type | Description (描述) |
|-----------|------|-------|
| `caption` | `string` | Figure caption (图片标题) |
| `label` | `string` | Cross-reference label, e.g. `fig:xxx` (交叉引用标签) |
| `width` | `string` | Width specification (宽度), e.g. `0.8\textwidth` |
| `height` | `string` | Height specification (高度), e.g. `60mm` (can combine with width) |
| `placement` | `string` | Float placement (浮动位置), e.g. `htbp` |
| `centering` | `bool` | Center the figure (居中), default behavior |

`placement` only affects LaTeX output and defaults to `htbp` when omitted.

`placement` 仅影响 LaTeX 输出；未指定时默认使用 `htbp`。

### AI-generated figures / AI 生成图片

Add `ai-*` directives to mark a figure for AI generation:

```markdown
![Taxonomy diagram](figures/taxonomy.png)
<!-- caption: Taxonomy of registration methods -->
<!-- label: fig:taxonomy -->
<!-- width: 0.9\textwidth -->
<!-- ai-generated: true -->
<!-- ai-model: dall-e-3 -->
<!-- ai-prompt: |
  Academic diagram showing taxonomy of point cloud registration,
  tree structure, clean minimal style, white background
-->
<!-- ai-negative-prompt: photorealistic, 3D render -->
<!-- ai-params: {size: 1024x1024, quality: hd} -->
```

| AI Directive | Type | Description (描述) |
|-------------|------|-------|
| `ai-generated` | `bool` | Mark for AI generation (标记为 AI 生成) |
| `ai-model` | `string` | Model name override (模型名覆盖) |
| `ai-prompt` | `string` | Generation prompt (生成提示词) |
| `ai-negative-prompt` | `string` | Negative prompt (负向提示词) |
| `ai-params` | `dict` | Extra kwargs passed to `chat.completions.create()`, e.g. `{size: "1024x1024", quality: hd}` (额外参数，透传给生成 API) |

---

## 9. Tables / 表格

Standard GFM (GitHub Flavored Markdown) pipe tables:

```markdown
| Method | RMSE (cm) | Time (ms) | Platform |
|--------|-----------|-----------|----------|
| ICP    | 2.3       | 150       | CPU      |
| 4PCS   | 1.8       | 80        | CPU      |
| Ours   | 1.9       | 8         | FPGA     |
<!-- caption: Performance comparison on ModelNet40 dataset -->
<!-- label: tab:results -->
<!-- placement: h -->
```

### Attach-up directives for tables / 表格附着指令

| Directive | Type | Description (描述) |
|-----------|------|-------|
| `caption` | `string` | Table caption (表格标题) |
| `label` | `string` | Cross-reference label, e.g. `tab:xxx` (交叉引用标签) |
| `placement` | `string` | Float placement (浮动位置), e.g. `htbp`, `h`, `!htbp` |

`placement` only affects LaTeX output and defaults to `htbp` when omitted.

`placement` 仅影响 LaTeX 输出；未指定时默认使用 `htbp`。

Table alignment via GFM syntax:

```markdown
| Left   | Center  | Right  |
|:-------|:-------:|-------:|
| a      | b       | c      |
```

---

## 10. Code Blocks / 代码块

Standard fenced code blocks with language annotation:

````markdown
```python
def icp(source, target, max_iter=50):
    for i in range(max_iter):
        correspondences = find_nearest(source, target)
        R, t = solve_svd(correspondences)
        source = apply_transform(source, R, t)
    return R, t
```
````

---

## 11. Lists / 列表

### Unordered list / 无序列表

```markdown
- Item one
- Item two
  - Nested item
- Item three
```

### Ordered list / 有序列表

```markdown
1. First contribution
2. Second contribution
3. Third contribution
```

---

## 12. Blockquotes / 引用块

```markdown
> Registration is the process of finding a spatial transformation
> that aligns two point clouds.
```

---

## 13. Environments / 自定义环境

Use `<!-- begin: name -->` and `<!-- end: name -->` to wrap content in
a LaTeX environment:

```markdown
<!-- begin: theorem -->
For any two point sets $P$ and $Q$, if the ICP algorithm converges,
the resulting transformation $T^*$ is a local minimum of the
objective function.
<!-- end: theorem -->
```

### Environment directives / 环境指令

Directives between `begin` and `end` are collected into the environment metadata:

```markdown
<!-- begin: algorithm -->
<!-- caption: ICP Algorithm -->
<!-- label: alg:icp -->
**Input:** Source $P$, Target $Q$, max iterations $k$\
**Output:** Rotation $R$, translation $t$

1. Initialize $R = I, t = 0$
2. For $i = 1$ to $k$:
   - Find nearest neighbors
   - Compute optimal $(R, t)$ via SVD
   - Apply transform to $P$
3. Return $R, t$
<!-- end: algorithm -->
```

Common environment names:

| Name | LaTeX | Description |
|------|-------|-------------|
| `theorem` | `\begin{theorem}` | Theorem (定理) |
| `lemma` | `\begin{lemma}` | Lemma (引理) |
| `proof` | `\begin{proof}` | Proof (证明) |
| `definition` | `\begin{definition}` | Definition (定义) |
| `algorithm` | `\begin{algorithm}` | Algorithm (算法) |
| `remark` | `\begin{remark}` | Remark (注) |
| `example` | `\begin{example}` | Example (例) |

---

## 14. Raw LaTeX Blocks / 原始 LaTeX 块

Insert verbatim LaTeX that passes through untouched:

```markdown
<!-- begin: raw -->
\newcommand{\norm}[1]{\left\| #1 \right\|}
\DeclareMathOperator{\argmin}{arg\,min}
<!-- end: raw -->
```

Raw blocks preserve LaTeX content verbatim, including math delimiters such as
inline `$...$`, display `$$...$$`, and table row separators `\\`.

原始 LaTeX 块会按原样保留内容，包括行内 `$...$`、行间 `$$...$$` 数学定界符，
以及表格行分隔符 `\\`。

---

## 15. Include TeX / 引入外部 TeX 文件

Include an external `.tex` file as a raw block:

```markdown
<!-- include-tex: macros/custom-commands.tex -->
```

**Security**: The included path must stay within the source file's directory
(no `../` traversal). Only works for file-based sources (not stdin/API).

---

## 16. Footnotes / 脚注

Standard Markdown footnote syntax:

```markdown
Point cloud registration[^1] is fundamental to 3D vision.

[^1]: The process of aligning two or more 3D point sets into
a common coordinate system.
```

---

## 17. Thematic Breaks / 水平分割线

```markdown
---
```

or `***` or `___`. Produces `\hrule` in LaTeX.

---

## 18. Attach-Up Directive Mechanism / 向上附着机制

Directives in HTML comments attach to the **previous sibling node**:

```
[content node]     ← target (receives metadata)
<!-- key: value --> ← directive (consumed, removed from tree)
```

Multiple directives can stack:

```markdown
![image](fig.png)
<!-- caption: My figure -->
<!-- label: fig:mine -->
<!-- width: 0.8\textwidth -->
```

All three directives attach to the `![image]` node above.

**Special case**: If the previous sibling is a `Paragraph` containing
a single `Image` or `MathBlock`, the directive "penetrates" the paragraph
and attaches to the inner node.

---

## 19. Label Naming Conventions / 标签命名约定

| Prefix | Usage | Example |
|--------|-------|---------|
| `sec:` | Section/heading labels (章节) | `sec:intro`, `sec:method` |
| `fig:` | Figure labels (图片) | `fig:pipeline`, `fig:results` |
| `tab:` | Table labels (表格) | `tab:comparison`, `tab:params` |
| `eq:` | Equation labels (公式) | `eq:icp`, `eq:transform` |
| `alg:` | Algorithm labels (算法) | `alg:icp`, `alg:fpga` |
| `thm:` | Theorem labels (定理) | `thm:convergence` |

---

## 20. Complete Minimal Example / 完整最小示例

```markdown
<!-- documentclass: article -->
<!-- packages: [amsmath, graphicx] -->
<!-- title: My Paper -->
<!-- author: Author Name -->
<!-- date: 2026 -->
<!-- abstract: |
  A short abstract.
-->

# Introduction
<!-- label: sec:intro -->

As shown by [Author](cite:author2024), the problem is important.

The objective function is:

$$
\min_{x} f(x) = \sum_{i} \| x - y_i \|^2
$$
<!-- label: eq:objective -->

See [Equation 1](ref:eq:objective) and [Section 2](ref:sec:method).

## Method
<!-- label: sec:method -->

![System overview](figures/overview.png)
<!-- caption: System overview -->
<!-- label: fig:overview -->
<!-- width: 0.9\textwidth -->

| Metric | Ours | Baseline |
|--------|------|----------|
| Error  | 1.2  | 3.4      |
<!-- caption: Results comparison -->
<!-- label: tab:results -->

## Conclusion

We presented a method that outperforms baselines (see [Table 1](ref:tab:results)).
```
