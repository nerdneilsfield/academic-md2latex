# md-mid

[![Python](https://img.shields.io/badge/Python-≥3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-425%2B%20passed-brightgreen)](tests/)
[![mypy](https://img.shields.io/badge/type%20check-mypy%20strict-blue)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230?logo=ruff)](https://docs.astral.sh/ruff/)
[![uv](https://img.shields.io/badge/pkg-uv-DE5FE9?logo=uv)](https://docs.astral.sh/uv/)

**[中文文档](README_ZH.md)** · English

---

**Academic Writing Intermediate Format & Multi-target Conversion Tool**

md-mid defines a Markdown-based intermediate format (`.mid.md`) for academic writing.
Write your paper once in plain Markdown with metadata encoded in HTML comments, then
convert to **LaTeX**, **rich Markdown**, or **self-contained HTML** — all from a single
source file.

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

## Features

- **Multi-target output** — LaTeX (`.tex`), rich Markdown (`.md`), and HTML with MathJax
- **8 citation commands** — `cite`, `citep`, `citet`, `citeauthor`, `citeyear`, `textcite`,
  `parencite`, `autocite` with BibTeX file parsing
- **Math** — inline `$...$` and display `$$...$$` with labels and equation environments
- **Cross-references** — labels and refs that become `\ref{}` / `<a href>` / `{#id}` per target
- **Figures & tables** — caption, label, width, placement via HTML comment directives
- **Environments** — `<!-- begin: algorithm -->` / `<!-- end: algorithm -->` blocks
- **Include TeX** — `<!-- include-tex: fragment.tex -->` for external LaTeX fragments
- **AI figure generation** — optional pipeline with nanobanana-compatible runners
- **5-layer config** — CLI > directives > config file > template > defaults
- **i18n** — `zh` (中文) and `en` locale support for figure/table labels

## Architecture

```mermaid
flowchart TD
    subgraph Input
        SRC["paper.mid.md"]
    end

    subgraph "Parsing Pipeline"
        P["Markdown Parser<br/><i>markdown-it-py + plugins</i>"]
        C["Comment Processor<br/><i>4-phase directive extraction</i>"]
        EAST["Enhanced AST (EAST)<br/><i>32 node types</i>"]
    end

    subgraph Renderers
        LTX["LaTeX Renderer<br/><code>.tex</code>"]
        MD["Markdown Renderer<br/><code>.md</code>"]
        HTML["HTML Renderer<br/><code>.html</code> + MathJax"]
    end

    SRC --> P --> C --> EAST
    EAST --> LTX
    EAST --> MD
    EAST --> HTML
```

Each renderer supports three output modes:

| Mode | LaTeX | Markdown | HTML |
|------|-------|----------|------|
| `full` | Preamble + `\begin{document}` + bibliography | YAML front matter + body + footnotes | `<!DOCTYPE html>` + CSS + MathJax CDN |
| `body` | Content inside `\begin{document}...\end{document}` | Body + footnotes (no front matter) | `<body>` content only |
| `fragment` | Bare content, headings degraded one level | Bare content | Bare content |

<details>
<summary><b>EAST Node Types (32 total)</b></summary>

**Block nodes (16):**
`Document` · `Heading` · `Paragraph` · `Blockquote` · `List` · `ListItem` · `CodeBlock` ·
`MathBlock` · `Figure` · `Table` · `Environment` · `RawBlock` · `ThematicBreak` ·
`FootnoteDef` · `HardBreak` · `SoftBreak`

**Inline nodes (16):**
`Text` · `Strong` · `Emphasis` · `CodeInline` · `MathInline` · `Link` · `Image` ·
`Citation` · `CrossRef` · `FootnoteRef` · `FootnoteDef` · `SoftBreak` · `HardBreak` ·
`RawInline` · `Strikethrough` · `Superscript`

All nodes extend a base `Node` class with `children`, `metadata`, and `position` fields.

</details>

## Getting Started

### Prerequisites

- **Python 3.14+**
- [**uv**](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/<owner>/academic-md2latex.git
cd academic-md2latex
uv sync
```

### Quick Start

```bash
# Markdown → LaTeX (default)
md-mid paper.mid.md -o paper.tex

# Markdown → HTML with MathJax
md-mid paper.mid.md -o paper.html -t html

# Markdown → Rich Markdown
md-mid paper.mid.md -o paper.md -t markdown

# Read from stdin, body-only mode
cat paper.mid.md | md-mid - --mode body -o paper.tex

# Dump the Enhanced AST for debugging
md-mid paper.mid.md --dump-east | jq .
```

<details>
<summary><b>Full CLI Reference</b></summary>

```
Usage: md-mid [OPTIONS] INPUT

Options:
  -o, --output PATH                   Output file (stdout if omitted)
  -t, --target [latex|markdown|html]  Output format (default: latex)
  --mode [full|body|fragment]         Output scope (default: full)
  --config PATH                       Config file (md-mid.yaml)
  --template PATH                     LaTeX template (.yaml)
  --bib PATH                          Bibliography file (.bib)
  --bibliography-mode MODE            auto | standalone | external | none
  --heading-id-style [attr|html]      Heading anchor format
  --locale [zh|en]                    Label language (default: zh)
  --generate-figures                  Enable AI figure generation
  --figures-runner PATH               Figure generation runner script
  --figures-config PATH               Runner config (TOML)
  --force-regenerate                  Re-generate existing images
  --strict                            Strict parsing mode
  --verbose                           Verbose output
  --dump-east                         Dump Enhanced AST as JSON
  --version                           Show version
```

</details>

## Document Format

md-mid documents are standard Markdown files with the `.mid.md` extension. All academic
metadata is encoded in **HTML comments** (`<!-- key: value -->`), so the source is readable
in any Markdown viewer while carrying full LaTeX semantics.

### Document-level Directives

These go at the top of your `.mid.md` file and control the LaTeX preamble:

```markdown
<!-- documentclass: article -->
<!-- classoptions: [12pt, a4paper] -->
<!-- packages: [amsmath, graphicx, hyperref] -->
<!-- bibliography: refs.bib -->
<!-- bibstyle: IEEEtran -->
<!-- title: My Paper Title -->
<!-- author: Author Name -->
<!-- date: 2026 -->
<!-- abstract: |
  This paper presents a novel method ...
-->
```

<details>
<summary><b>Generated LaTeX preamble</b></summary>

```latex
\documentclass[12pt,a4paper]{article}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{hyperref}
\bibliographystyle{IEEEtran}
\title{My Paper Title}
\author{Author Name}
\date{2026}

\begin{document}
\maketitle

\begin{abstract}
This paper presents a novel method ...
\end{abstract}

% ... body content ...

\bibliography{refs}

\end{document}
```

</details>

### Citations

Use Markdown link syntax with a `cite:` prefix in the URL:

```markdown
Prior work [Wang et al.](cite:wang2024) showed that ...
Classical methods [1](citep:fischler1981) have limitations.
As [Smith](citeauthor:smith2023) demonstrated ...
```

| md-mid Syntax | LaTeX Output | HTML Output |
|---------------|-------------|-------------|
| `[text](cite:key)` | `\cite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citep:key)` | `\citep{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citet:key)` | `\citet{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citeauthor:key)` | `\citeauthor{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](citeyear:key)` | `\citeyear{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](textcite:key)` | `\textcite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](parencite:key)` | `\parencite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |
| `[text](autocite:key)` | `\autocite{key}` | `<sup><a href="#cite-key">[1]</a></sup>` |

### Cross-references

```markdown
# Introduction
<!-- label: sec:intro -->

See [Section 1](ref:sec:intro) for details.
```

| Target | Output |
|--------|--------|
| LaTeX | `\label{sec:intro}` + `\ref{sec:intro}` |
| HTML | `<h1 id="sec:intro">` + `<a href="#sec:intro">` |
| Markdown | `{#sec:intro}` + `<a href="#sec:intro">` |

### Figures with Metadata

```markdown
![Pipeline overview](figures/pipeline.png)
<!-- caption: Point cloud registration pipeline -->
<!-- label: fig:pipeline -->
<!-- width: 0.85\textwidth -->
<!-- placement: htbp -->
```

<details>
<summary><b>Generated LaTeX figure</b></summary>

```latex
\begin{figure}[htbp]
\centering
\includegraphics[width=0.85\textwidth]{figures/pipeline.png}
\caption{Point cloud registration pipeline}
\label{fig:pipeline}
\end{figure}
```

</details>

<details>
<summary><b>Generated HTML figure</b></summary>

```html
<figure id="fig:pipeline">
  <img src="figures/pipeline.png"
       alt="Pipeline overview"
       loading="lazy">
  <figcaption>Figure 1: Point cloud registration pipeline</figcaption>
</figure>
```

</details>

<details>
<summary><b>Generated rich Markdown figure</b></summary>

```html
<figure id="fig:pipeline">
  <img src="figures/pipeline.png"
       alt="Pipeline overview"
       style="max-width:100%">
  <figcaption><strong>Figure 1</strong>: Point cloud registration pipeline</figcaption>
</figure>
```

</details>

### AI-generated Figures

Mark a figure as AI-generated to include provenance metadata in the output:

```markdown
![Taxonomy diagram](figures/taxonomy.png)
<!-- caption: Method taxonomy -->
<!-- label: fig:taxonomy -->
<!-- ai-generated: true -->
<!-- ai-model: dall-e-3 -->
<!-- ai-prompt: |
  Academic diagram showing method taxonomy,
  clean minimal style, white background
-->
<!-- ai-negative-prompt: photorealistic, 3D -->
```

In LaTeX output, AI metadata becomes `%` comments. In HTML and rich Markdown, it renders
as a collapsible `<details>` block.

Use `--generate-figures` to automatically generate images from prompts:

```bash
md-mid paper.mid.md -o paper.tex \
  --generate-figures \
  --figures-runner ./runner.py \
  --figures-config api.toml
```

### Tables

```markdown
| Method | RMSE (cm) | Time (ms) | Platform |
|--------|-----------|-----------|----------|
| RANSAC | 2.3       | 150       | CPU      |
| Ours   | 1.9       | 8         | FPGA     |
<!-- caption: Performance comparison on ModelNet40 -->
<!-- label: tab:results -->
```

<details>
<summary><b>Generated LaTeX table</b></summary>

```latex
\begin{table}[htbp]
\centering
\caption{Performance comparison on ModelNet40}
\label{tab:results}
\begin{tabular}{llll}
\hline
Method & RMSE (cm) & Time (ms) & Platform \\
\hline
RANSAC & 2.3 & 150 & CPU \\
Ours & 1.9 & 8 & FPGA \\
\hline
\end{tabular}
\end{table}
```

</details>

### Math

```markdown
Inline: the transform $T \in SE(3)$ is defined by ...

Display with label:

$$
T = \begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix}
$$
<!-- label: eq:transform -->
```

| Target | Inline | Display |
|--------|--------|---------|
| LaTeX | `$T \in SE(3)$` | `\begin{equation} ... \label{eq:transform} \end{equation}` |
| HTML | `$T \in SE(3)$` (MathJax) | `\[ ... \]` with `id="eq:transform"` |
| Markdown | `$T \in SE(3)$` | `$$ ... $$` with `<a id="eq:transform">` |

### Environments

```markdown
<!-- begin: algorithm -->
**Input:** Point clouds $P$ and $Q$

1. Compute coplanar bases
2. Find congruent sets
3. Verify and refine

**Output:** Rigid transform $T$
<!-- end: algorithm -->
```

<details>
<summary><b>Generated LaTeX environment</b></summary>

```latex
\begin{algorithm}
\textbf{Input:} Point clouds $P$ and $Q$

\begin{enumerate}
\item Compute coplanar bases
\item Find congruent sets
\item Verify and refine
\end{enumerate}

\textbf{Output:} Rigid transform $T$
\end{algorithm}
```

</details>

### Include TeX

Insert external LaTeX fragments (e.g., complex TikZ diagrams):

```markdown
<!-- include-tex: figures/architecture.tex -->
```

This reads the file and inserts it as a `RawBlock` node. Works inside environments too.

### Full Example

See [`tests/fixtures/full_example.mid.md`](tests/fixtures/full_example.mid.md) for a
complete demonstration of all features.

## Configuration

```mermaid
flowchart LR
    CLI["CLI flags"] --> R["Resolver"]
    DIR["In-document<br/>directives"] --> R
    CFG["Config file<br/><code>md-mid.yaml</code>"] --> R
    TPL["Template<br/><code>ieee.yaml</code>"] --> R
    DEF["Built-in<br/>defaults"] --> R
    R --> OUT["Final Config"]

    style CLI fill:#ffa
    style DIR fill:#fda
    style CFG fill:#fca
    style TPL fill:#faa
    style DEF fill:#eee
```

Priority: **CLI > directives > config file > template > defaults**. Higher layers override
lower layers. This lets you set venue defaults in a template, override per-paper in the
config file, and fine-tune per-build on the command line.

### Config File (`md-mid.yaml`)

```yaml
documentclass: article
classoptions: [12pt, a4paper]
packages: [amsmath, graphicx]
code_style: lstlisting       # or: minted
locale: zh                    # or: en
target: latex                 # or: markdown, html
bibliography_mode: auto       # or: standalone, external, none
heading_id_style: attr        # or: html
extra-preamble: |
  \DeclareMathOperator{\argmin}{argmin}
```

<details>
<summary><b>All config fields</b></summary>

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `documentclass` | `str` | `"article"` | LaTeX document class |
| `classoptions` | `list[str]` | `[]` | Class options like `12pt`, `a4paper` |
| `packages` | `list[str]` | `[]` | LaTeX packages to load |
| `title` | `str` | `""` | Document title |
| `author` | `str` | `""` | Author name(s) |
| `date` | `str` | `""` | Date string |
| `abstract` | `str` | `""` | Abstract text |
| `bibliography` | `str` | `""` | BibTeX file path |
| `bibstyle` | `str` | `"plain"` | Bibliography style |
| `code_style` | `str` | `"lstlisting"` | Code block rendering style |
| `locale` | `str` | `"zh"` | Label language |
| `target` | `str` | `"latex"` | Default output target |
| `bibliography_mode` | `str` | `"auto"` | Bibliography output strategy |
| `heading_id_style` | `str` | `"attr"` | Heading anchor format |
| `extra-preamble` | `str` | `""` | Raw LaTeX for preamble |
| `thematic_break_style` | `str` | `"newpage"` | `newpage` / `hrule` / `ignore` |
| `tilde_ref` | `bool` | `true` | Use `~\ref` instead of `\ref` |

</details>

### Template File

Templates provide reusable defaults for specific venues. Example — IEEE conference:

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

## Project Structure

```
academic-md2latex/
├── src/md_mid/              # Source code (16 modules)
│   ├── cli.py               #   Click CLI entry point
│   ├── parser.py            #   Markdown → EAST parser
│   ├── nodes.py             #   EAST node definitions (32 types)
│   ├── comment.py           #   4-phase comment directive processor
│   ├── config.py            #   5-layer configuration resolution
│   ├── latex.py             #   LaTeX renderer
│   ├── markdown.py          #   Rich Markdown renderer (2-pass)
│   ├── html.py              #   HTML renderer (MathJax CDN)
│   ├── bibtex.py            #   Minimal BibTeX parser
│   ├── genfig.py            #   AI figure generation pipeline
│   ├── escape.py            #   LaTeX special character escaping
│   ├── sanitize.py          #   HTML input sanitization
│   ├── url_check.py         #   URL safety validation
│   ├── ai_meta.py           #   Shared AI metadata rendering
│   └── diagnostic.py        #   Error/warning diagnostics
├── tests/                   # Test suite (16 files, 425+ tests)
│   ├── fixtures/            #   Test .mid.md documents
│   └── conftest.py          #   Shared pytest fixtures
├── templates/               # LaTeX venue templates (ieee.yaml, ...)
├── docs/                    # Documentation and plans
├── pyproject.toml           # Project metadata & tool config
├── Makefile                 # Build commands
└── CLAUDE.md                # AI agent coding standards
```

<details>
<summary><b>Comment Processor 4-phase Pipeline</b></summary>

```mermaid
flowchart TD
    A["Phase 1: Document Directives<br/><i>documentclass, packages, title, ...</i>"]
    B["Phase 2: Begin/End Environments<br/><i>algorithm, theorem, proof, ...</i>"]
    C["Phase 3: Include-TeX<br/><i>insert external .tex fragments</i>"]
    D["Phase 4: Attach-Up Directives<br/><i>caption, label, width, placement, ai-*</i>"]

    A --> B --> C --> D
```

- **Phase 1** extracts top-level metadata (documentclass, packages, title, author, etc.)
- **Phase 2** pairs `<!-- begin: X -->` / `<!-- end: X -->` into `Environment` nodes
- **Phase 3** replaces `<!-- include-tex: file.tex -->` with `RawBlock` content (recursive)
- **Phase 4** attaches trailing comment metadata to the preceding figure/table/math node

</details>

## Development

### Setup

```bash
uv sync                      # Install all dependencies
```

### Commands

| Command | Description |
|---------|-------------|
| `make check` | Run lint + typecheck + test **(required before committing)** |
| `make test` | Run pytest with verbose output |
| `make lint` | Run ruff linter |
| `make format` | Run ruff formatter |
| `make typecheck` | Run mypy in strict mode |
| `make fix` | Auto-fix lint issues and format |

### Coding Standards

| Rule | Example |
|------|---------|
| Type annotations on all functions | `def parse(text: str) -> Document:` |
| Bilingual comments (EN + CN) | `# Calculate average (计算平均值)` |
| Google-style docstrings (bilingual) | See [CLAUDE.md](CLAUDE.md) |
| 100 char max line length | Enforced by ruff |
| `snake_case` functions, `PascalCase` classes | `render_figure()`, `LaTeXRenderer` |

<details>
<summary><b>Docstring example</b></summary>

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

### Testing

Tests mirror source modules one-to-one (`parser.py` → `test_parser.py`).

```bash
make test                    # Run all 425+ tests
```

| Test file | Covers |
|-----------|--------|
| `test_parser.py` | Markdown parsing, node creation |
| `test_nodes.py` | EAST serialization, type properties |
| `test_latex.py` | LaTeX rendering (headings, math, citations, tables, figures) |
| `test_markdown.py` | Rich Markdown rendering, index pass |
| `test_html.py` | HTML rendering, sanitization, MathJax |
| `test_comment.py` | 4-phase comment directive processing |
| `test_config.py` | Config loading, precedence, validation |
| `test_cli.py` | CLI options, error handling |
| `test_e2e.py` | End-to-end conversion pipelines |
| `test_bibtex.py` | BibTeX file parsing |
| `test_genfig.py` | AI figure generation jobs |
| `test_escape.py` | LaTeX special character escaping |
| `test_sanitize.py` | HTML input sanitization |
| `test_url_check.py` | URL safety validation |
| `test_diagnostic.py` | Diagnostic error/warning collection |

Test fixtures in [`tests/fixtures/`](tests/fixtures/) provide reusable `.mid.md`
documents: `minimal`, `heading_para`, `math`, `cite_ref`, `comments`, `full_example`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests first (TDD encouraged)
4. Ensure `make check` passes (ruff, mypy, pytest)
5. Submit a pull request

All code must include complete type annotations and bilingual (EN + CN) comments.
See [CLAUDE.md](CLAUDE.md) for the full coding standards.
