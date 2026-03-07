# 文桥 · Wenqiao

[![CI](https://github.com/nerdneilsfield/wenqiao/actions/workflows/ci.yml/badge.svg)](https://github.com/nerdneilsfield/wenqiao/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/wenqiao)](https://pypi.org/project/wenqiao/)
[![Python](https://img.shields.io/pypi/pyversions/wenqiao?logo=python&logoColor=white)](https://pypi.org/project/wenqiao/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![mypy](https://img.shields.io/badge/type%20check-mypy%20strict-blue)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230?logo=ruff)](https://docs.astral.sh/ruff/)
[![uv](https://img.shields.io/badge/pkg-uv-DE5FE9?logo=uv)](https://docs.astral.sh/uv/)

**[中文文档](README_ZH.md)** · English

---

> **Write once, render anywhere.**  
> *One manuscript, many outputs.*

**Academic Writing Intermediate Format & Multi-target Conversion Tool**

Academic writing suffers not from deep thought, but from format entanglement.  
Lost in the forest of `.tex` brackets, wandering in the maze of `\begin{} \end{}`,  
you yearn for Markdown's simplicity, yet citations, cross-references, and figure labels  
exile you to the wilderness.

**Wenqiao** is a bridge:  
> One end connects your thoughts (Markdown's purity),  
> the other end connects the world's rules (LaTeX's rigor, HTML's openness, rich text's friendliness).  
> You simply stand at the center, writing a manuscript called `.mid.md`.

Wenqiao defines a Markdown-based intermediate format (`.mid.md`) for academic writing.
Write your paper once in plain Markdown with metadata encoded in HTML comments, then
convert to **LaTeX**, **rich Markdown**, or **self-contained HTML** — all from a single
source file.

```mermaid
graph LR
    A["paper.mid.md"] --> B["wenqiao"]
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
  `parencite`, `autocite` with BibTeX file parsing; also supports bare `[cite:key]` shortcuts
- **Math** — inline `$...$` and display `$$...$$` with labels and equation environments
- **Cross-references** — labels and refs that become `\ref{}` / `<a href>` / `{#id}` per target;
  also supports bare `[ref:label]` shortcuts
- **Figures & tables** — caption, label, width, placement via HTML comment directives;
  table captions support inline `[text](ref:label)` / `[text](cite:key)` markup
- **Smart table layout** — auto-scales wide tables with `\scalebox`, wraps long cells with
  `\makecell[lt]`, uses per-column dynamic wrap threshold to prevent page overflow
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

- **Python 3.12+**
- [**uv**](https://docs.astral.sh/uv/) package manager (recommended)

### Installation

**From PyPI:**

```bash
pip install wenqiao

# Or with uv
uv pip install wenqiao

# With AI figure generation support
pip install wenqiao[figures]
```

**From source (for development):**

```bash
git clone https://github.com/nerdneilsfield/wenqiao.git
cd wenqiao
uv sync
```

### Quick Start

```bash
# Markdown → LaTeX (default)
wenqiao paper.mid.md -o paper.tex

# Explicit convert subcommand (same as above)
wenqiao convert paper.mid.md -o paper.tex

# Markdown → HTML with MathJax
wenqiao paper.mid.md -o paper.html -t html

# Markdown → Rich Markdown
wenqiao paper.mid.md -o paper.md -t markdown

# Validate citations, cross-references, and images
wenqiao validate paper.mid.md --bib refs.bib --strict

# Check formatting (exit 1 if unformatted)
wenqiao format paper.mid.md --check --diff

# Format with change statistics
wenqiao format paper.mid.md --stats

# Read from stdin, body-only mode
cat paper.mid.md | wenqiao - --mode body -o paper.tex

# Dump the Enhanced AST for debugging
wenqiao paper.mid.md --dump-east | jq .
```

<details>
<summary><b>Full CLI Reference</b></summary>

Wenqiao uses subcommands: `convert` (default), `validate`, and `format`.
The `convert` subcommand is implicit — `wenqiao file.mid.md` is equivalent to
`wenqiao convert file.mid.md`.

```
Usage: wenqiao [OPTIONS] COMMAND [ARGS]...

Commands:
  convert   Convert academic Markdown to LaTeX/Markdown/HTML (default)
  validate  Validate citations, cross-references, and images
  format    Normalize academic Markdown formatting
```

**convert** (default):
```
Usage: wenqiao convert [OPTIONS] INPUT

Options:
  -o, --output PATH                   Output file (stdout if omitted)
  -t, --target [latex|markdown|html]  Output format (default: latex)
  --mode [full|body|fragment]         Output scope (default: full)
  --config PATH                       Config file (wenqiao.yaml)
  --template PATH                     LaTeX template (.yaml)
  --bib PATH                          Bibliography file (.bib)
  --bibliography-mode MODE            auto | standalone | external | none
  --heading-id-style [attr|html]      Heading anchor format
  --locale [zh|en]                    Label language (default: zh)
  --generate-figures                  Enable AI figure generation
  --figures-config PATH               Runner config (TOML)
  --force-regenerate                  Re-generate existing images
  --concurrency INTEGER               Max concurrent figure generations (default: 4)
  --strict                            Strict parsing mode
  --verbose                           Verbose output
  --dump-east                         Dump Enhanced AST as JSON
```

**validate**:
```
Usage: wenqiao validate [OPTIONS] INPUT

Options:
  --bib PATH       BibTeX file for citation validation
  --config PATH    External config file (wenqiao.yaml)
  --template PATH  LaTeX template file (.yaml)
  --strict         Exit 1 on any diagnostic warnings
  --verbose        Show all diagnostics
```

**generate**:
```
Usage: wenqiao generate [OPTIONS] INPUT

  Generate AI figures in a .mid.md file concurrently.

Options:
  --figures-config PATH      TOML config for AI backend (API key, model, URL)
  --model TEXT               Override model name from config
  --base-url TEXT            Override API base URL
  --api-key TEXT             API key (also reads WENQIAO_API_KEY env var)
  --type [openai]            Backend type (default: openai)
  --concurrency INTEGER      Max concurrent generations, must be >= 1 (default: 4)
  --start-id INTEGER         Start figure index, 1-based inclusive (default: 1)
  --end-id INTEGER           End figure index, 1-based inclusive (default: last)
  --force                    Re-generate even if output file exists
  --no-writeback             Skip writing <!-- ai-done: true --> to source file
```

**format**:
```
Usage: wenqiao format [OPTIONS] INPUT

Options:
  -o, --output PATH  Output path (default: overwrite input)
  --check            Check only, exit 1 if unformatted
  --diff             Show unified diff of changes
  --no-rumdl         Skip rumdl formatting step
  --stats            Show formatting statistics
```

</details>

## Python API

Wenqiao exposes a clean Python API for programmatic use in build systems, Jupyter
notebooks, web services, and custom tooling. All public symbols are available
directly from the `wenqiao` package.

```python
from wenqiao import convert, validate_text, format_text, parse_document
from wenqiao import ConvertResult, ConversionError, WenqiaoConfig, Diagnostic, Document
```

### `convert()` — Convert Academic Markdown

The primary entry point. Converts Markdown source to LaTeX, HTML, or rich Markdown.

```python
from wenqiao import convert

# Basic: string → LaTeX
result = convert("# Introduction\n\nHello world.\n")
print(result.text)       # \documentclass[12pt,a4paper]{article} ...
print(result.config)     # WenqiaoConfig(target='latex', mode='full', ...)
print(result.document)   # Document(children=[Heading(...), Paragraph(...)])
print(result.diagnostics)  # [] (empty if no warnings/errors)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | `str \| Path` | *required* | Markdown text string or file path |
| `target` | `str` | `"latex"` | Output format: `"latex"` / `"markdown"` / `"html"` |
| `mode` | `str \| None` | `None` | Output scope: `"full"` / `"body"` / `"fragment"` |
| `locale` | `str \| None` | `None` | Label language: `"zh"` / `"en"` |
| `config` | `WenqiaoConfig \| dict \| None` | `None` | Pre-built config object or overrides dict |
| `template` | `Path \| None` | `None` | Template YAML file path |
| `bib` | `Path \| str \| dict \| None` | `None` | `.bib` file path, raw text, or pre-parsed dict |
| `strict` | `bool` | `False` | Raise `ConversionError` on diagnostic errors |

**Returns:** `ConvertResult` — a frozen dataclass with `.text`, `.diagnostics`, `.config`, `.document`.

#### Output targets

```python
# LaTeX (default)
latex_result = convert(source)

# Rich Markdown with BibTeX footnotes
md_result = convert(source, target="markdown", bib=Path("refs.bib"))

# Self-contained HTML with MathJax
html_result = convert(source, target="html")
```

#### Output modes

```python
# Full document with preamble (default)
full = convert(source, mode="full")

# Body only — no \documentclass or \begin{document}
body = convert(source, mode="body")

# Fragment — bare content, headings degraded
fragment = convert(source, mode="fragment")
```

#### File path input

```python
from pathlib import Path

# Read directly from a .mid.md file
result = convert(Path("paper.mid.md"), target="html")
```

#### Configuration

Three ways to pass configuration:

```python
from wenqiao import convert, WenqiaoConfig
from pathlib import Path

# 1. Dict overrides — merged with defaults
result = convert(source, config={
    "documentclass": "report",
    "classoptions": ["11pt", "letterpaper"],
    "locale": "en",
})

# 2. Pre-built WenqiaoConfig — used as-is, no merging
cfg = WenqiaoConfig(mode="body", locale="en", documentclass="IEEEtran")
result = convert(source, config=cfg)

# 3. Template YAML file — merged at the template layer
result = convert(source, template=Path("templates/ieee.yaml"))
```

#### Bibliography

Three ways to provide bibliography data:

```python
from pathlib import Path

# .bib file path
result = convert(md, target="markdown", bib=Path("refs.bib"))

# Raw .bib text content
bib_text = '@article{wang2024, author={Wang}, title={Test}, year={2024}}'
result = convert(md, target="markdown", bib=bib_text)

# Pre-parsed dict (cite_key → display string)
result = convert(md, target="markdown", bib={"wang2024": "Wang. Test. 2024."})
```

#### Strict mode

```python
from wenqiao import convert, ConversionError

try:
    result = convert(source, strict=True)
except ConversionError as e:
    print(f"Conversion failed: {e}")
    for diag in e.diagnostics:
        print(f"  {diag}")
```

### `validate_text()` — Validate Document

Runs the EAST walker and validators to check citations, cross-references, and more.
Returns a list of `Diagnostic` objects.

```python
from wenqiao import validate_text

# Basic validation
diagnostics = validate_text("See [ref](cite:missing_key).\n", bib={})
for d in diagnostics:
    print(d)  # [WARNING] <string> - Citation key 'missing_key' not found ...

# With .bib file
diagnostics = validate_text(Path("paper.mid.md"), bib=Path("refs.bib"))

# Strict mode — raises ConversionError on any errors
from wenqiao import ConversionError
try:
    validate_text(source, strict=True)
except ConversionError as e:
    print(f"Validation failed with {len(e.diagnostics)} issues")
```

### `format_text()` — Normalize Formatting

Round-trip normalization: parse → render back as Markdown. Idempotent — formatting
an already-formatted document returns the same text.

Built-in normalization includes common math cleanup used by `wenqiao format`,
including:
- Unicode math operators to LaTeX (`≤`→`$\\leq$`, in math spans to `\\leq`)
- Bare Greek letters to LaTeX (`σ`→`$\\sigma$`, in math spans to `\\sigma`)
- Unicode super/subscripts (`m²`→`$m^2$`, `x₀`→`$x_0$`)
- Blank-line separation around display-math blocks delimited by standalone `$$`

```python
from wenqiao import format_text

formatted = format_text("# Hello\n\nWorld.\n")
print(formatted)

# Works with file paths too
formatted = format_text(Path("paper.mid.md"))

# Idempotent check
assert format_text(formatted) == formatted
```

### `parse_document()` — Low-level EAST Access

Returns the raw EAST `Document` tree for custom processing. Runs parse +
comment directive processing but no rendering.

```python
from wenqiao import parse_document, Document
from wenqiao.nodes import Heading, Paragraph

doc = parse_document("# Hello\n\nWorld.\n")
assert isinstance(doc, Document)

# Inspect the tree
for child in doc.children:
    print(f"{child.type}: {child}")

# Access document-level metadata from directives
doc = parse_document("""
<!-- title: My Paper -->
<!-- author: Author -->

# Introduction
""")
print(doc.metadata)  # {'title': 'My Paper', 'author': 'Author'}
```

### `ConvertResult` — Result Object

```python
@dataclass(frozen=True)
class ConvertResult:
    text: str                    # Rendered output string
    diagnostics: list[Diagnostic]  # Warnings and errors
    config: WenqiaoConfig          # Resolved configuration
    document: Document           # EAST tree (for inspection)
```

### `ConversionError` — Error Type

Raised when `strict=True` and diagnostics contain errors.

```python
class ConversionError(Exception):
    diagnostics: list[Diagnostic]  # All diagnostic messages
```

### Integration Examples

<details>
<summary><b>Jupyter Notebook</b></summary>

```python
from wenqiao import convert
from IPython.display import HTML

source = Path("paper.mid.md").read_text()
result = convert(source, target="html", mode="body")
HTML(result.text)
```

</details>

<details>
<summary><b>Build system (Makefile / script)</b></summary>

```python
#!/usr/bin/env python3
"""Batch convert all .mid.md files to LaTeX."""
from pathlib import Path
from wenqiao import convert

for md_file in Path("chapters/").glob("*.mid.md"):
    result = convert(md_file, template=Path("templates/ieee.yaml"))
    out = md_file.with_suffix(".tex")
    out.write_text(result.text, encoding="utf-8")
    print(f"{md_file} → {out} ({len(result.diagnostics)} diagnostics)")
```

</details>

<details>
<summary><b>Web service (FastAPI)</b></summary>

```python
from fastapi import FastAPI, HTTPException
from wenqiao import convert, ConversionError

app = FastAPI()

@app.post("/convert")
def convert_markdown(source: str, target: str = "latex"):
    try:
        result = convert(source, target=target, strict=True)
        return {"text": result.text, "diagnostics": [str(d) for d in result.diagnostics]}
    except ConversionError as e:
        raise HTTPException(400, detail=[str(d) for d in e.diagnostics])
```

</details>

<details>
<summary><b>Custom EAST processing</b></summary>

```python
from wenqiao import parse_document
from wenqiao.nodes import Heading, Citation

doc = parse_document(Path("paper.mid.md"))

# Extract all headings
headings = [
    (child.level, child)
    for child in doc.children
    if isinstance(child, Heading)
]

# Collect all citation keys
def collect_cites(node, keys=None):
    if keys is None:
        keys = set()
    if isinstance(node, Citation):
        keys.update(node.keys)
    for child in node.children:
        collect_cites(child, keys)
    return keys

all_keys = collect_cites(doc)
print(f"Found {len(all_keys)} unique citation keys")
```

</details>

## Document Format

Wenqiao documents are standard Markdown files with the `.mid.md` extension. All academic
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

**`package-options`** passes options to individual packages:

```markdown
<!-- packages: [amsmath, graphicx, geometry] -->
<!-- package-options: {geometry: "margin=1in,top=2cm"} -->
```

This generates `\usepackage[margin=1in,top=2cm]{geometry}`. The value is passed verbatim into `\usepackage[...]{pkg}`.

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

Bare citation shortcuts are also supported:

```markdown
[cite:wang2024]
[cite:wang2024?cmd=citet]
[cite:a,b,c]
```

They behave like empty-display citations and map to the same citation commands.

| wenqiao Syntax | LaTeX Output | HTML Output |
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
[ref:sec:intro]
```

Bare ref shortcuts use the label itself as display text in Markdown/HTML output.

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
wenqiao paper.mid.md -o paper.tex \
  --generate-figures \
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

**Complex tables** (merged cells, `booktabs`, `multicolumn`) use a raw LaTeX passthrough block:

```markdown
<!-- begin: raw -->
\begin{table}[htbp]
\centering
\caption{Multi-column results}
\label{tab:complex}
\begin{tabular}{lcc}
\hline
\multicolumn{2}{c}{Performance} & Score \\
\hline
ICP   & 85.3 & RMSE \\
Ours  & 93.1 & RMSE \\
\hline
\end{tabular}
\end{table}
<!-- end: raw -->
```

Raw passthrough also preserves math delimiters verbatim, including inline `$...$`
and display `$$...$$` spans inside the raw block.

Add `booktabs` to your packages list to use `\toprule`, `\midrule`, `\bottomrule`.

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
    CFG["Config file<br/><code>wenqiao.yaml</code>"] --> R
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

### Config File (`wenqiao.yaml`)

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
| `thematic_break` | `str` | `"newpage"` | `newpage` / `hrule` / `ignore` |
| `ref_tilde` | `bool` | `true` | Use `~\ref` instead of `\ref` |

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
wenqiao paper.mid.md --template templates/ieee.yaml -o paper.tex
```

## Project Structure

```
wenqiao/
├── src/wenqiao/              # Source code (17 modules)
│   ├── __init__.py          #   Public API re-exports
│   ├── api.py               #   Public Python API (convert, validate, format)
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
├── tests/                   # Test suite (17 files, 479 tests)
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
make test                    # Run all 625 tests
```

| Test file | Covers |
|-----------|--------|
| `test_api.py` | Public Python API (convert, validate, format, parse) |
| `test_parser.py` | Markdown parsing, node creation |
| `test_nodes.py` | EAST serialization, type properties |
| `test_latex.py` | LaTeX rendering (headings, math, citations, tables, figures, scaling) |
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

## Claude Code Skill

This project ships a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill
(`wenqiao-writer`) that teaches Claude how to write well-formed `.mid.md` documents.

### Setup

Symlink the skill into your Claude Code configuration:

```bash
# From the project root
ln -s "$(pwd)/skills/wenqiao-writer" ~/.claude/skills/wenqiao-writer
```

Or, if you have the repo cloned elsewhere, the project already includes a symlink at
`.claude/skills/wenqiao-writer` pointing to `skills/wenqiao-writer`.

### Usage

Once installed, invoke the skill in Claude Code by name:

```
/wenqiao-writer
```

Or simply ask Claude to "write a `.mid.md` paper" — it will automatically pick up the
skill. The skill teaches Claude:

- All `.mid.md` directives (document headers, labels, captions, environments, etc.)
- Correct citation syntax (`[text](cite:key)`) and cross-references (`[text](ref:label)`)
- AI figure metadata directives
- Common mistakes to avoid
- A full feature coverage checklist for test fixtures

### Example prompt

> Write a `.mid.md` draft for a paper about point cloud registration using FPGA
> acceleration. Include an abstract, 3 sections, a comparison table, and 2 figures
> with AI generation prompts.

## Built-in Presets

Presets provide a one-line starting configuration for common document types:

```markdown
<!-- preset: zh -->
<!-- title: 我的论文 -->
```

| Preset | `documentclass` | `locale` | Use case |
|--------|-----------------|----------|----------|
| `zh`   | `ctexart`       | `zh`     | Chinese academic paper — compile with XeLaTeX |
| `en`   | `article`       | `en`     | Standard English paper |

Both presets include a comprehensive package set covering all wenqiao features:
`amsmath`, `amssymb`, `graphicx`, `geometry` (2 cm margins), `hyperref`, `xcolor`, `listings`,
`amsthm`, `algorithm2e`, `booktabs`, `makecell` (multi-line table cells).
Add `<!-- package-options: {...} -->` to configure individual packages, or add more via `<!-- packages: [...] -->`.

All document directives override the preset:

```markdown
<!-- preset: zh -->
<!-- documentclass: IEEEtran -->   <!-- overrides ctexart -->
```

**Via CLI:**

```bash
wenqiao paper.mid.md --preset zh -o paper.tex
```

**Priority chain:** `CLI > directives > config file > template > preset > defaults`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests first (TDD encouraged)
4. Ensure `make check` passes (ruff, mypy, pytest)
5. Submit a pull request

All code must include complete type annotations and bilingual (EN + CN) comments.
See [CLAUDE.md](CLAUDE.md) for the full coding standards.
