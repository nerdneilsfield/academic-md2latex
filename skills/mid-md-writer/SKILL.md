---
name: mid-md-writer
description: "Write well-formed .mid.md academic papers for md-mid converter. Use when asked to write, generate, or create .mid.md documents, test fixtures, or academic content in mid format."
version: 1.0.0
category: authoring
tags:
  - mid-md
  - academic
  - latex
  - markdown
  - authoring
  - test-fixture
author: md-mid
---

# `.mid.md` Academic Paper Writer

You are a specialist for writing `.mid.md` files — the academic Markdown intermediate format used by the md-mid converter. Every `.mid.md` file you produce MUST be valid CommonMark that simultaneously carries full LaTeX-grade semantics via HTML comment directives.

## Quick Reference Card

```
HEADER (before first content)        ATTACH-UP (after content node)
<!-- documentclass: article -->       <!-- label: sec:intro -->
<!-- classoptions: [12pt, a4] -->     <!-- caption: My figure -->
<!-- packages: [amsmath, ctex] -->    <!-- width: 0.8\textwidth -->
<!-- package-options: {hyper: []} --> <!-- placement: htbp -->
<!-- bibliography: refs.bib -->       <!-- centering: true -->
<!-- bibstyle: IEEEtran -->           <!-- options: ... -->
<!-- title: ... -->                   <!-- args: ... -->
<!-- author: ... -->
<!-- date: 2026 -->                   AI FIGURE DIRECTIVES
<!-- abstract: | ... -->              <!-- ai-generated: true -->
<!-- preamble: ... -->                <!-- ai-model: dall-e-3 -->
<!-- latex-mode: xelatex -->          <!-- ai-prompt: | ... -->
<!-- bibliography-mode: biber -->     <!-- ai-negative-prompt: ... -->
                                      <!-- ai-params: {size: 1024x1024} -->
ENVIRONMENTS
<!-- begin: theorem -->               SPECIAL
<!-- end: theorem -->                 <!-- begin: raw --> ... <!-- end: raw -->
                                      <!-- include-tex: path.tex -->

CITATIONS                            CROSS-REFERENCES
[Text](cite:key)                     [Text](ref:label)
[Text](cite:a,b,c)                   [Figure 1](ref:fig:xxx)
[Text](cite:key?cmd=citet)           [Section 2](ref:sec:xxx)

MATH                                 FOOTNOTES
Inline: $E = mc^2$                   Text[^1] ...
Block:  $$ ... $$                    [^1]: Footnote content.
<!-- label: eq:xxx -->
```

## Mandatory Rules

### 1. Header Region — ALL document directives go FIRST

```markdown
<!-- documentclass: article -->
<!-- packages: [amsmath, graphicx, algorithm2e] -->
<!-- title: Paper Title -->
<!-- author: Author Names -->
<!-- date: 2026 -->
<!-- abstract: |
  Abstract text here. Use YAML literal block scalar for multiline.
  Each continuation line must be indented by 2 spaces.
-->

# First Heading Starts Body
```

- Document directives MUST appear before any content (headings, paragraphs, etc.)
- Once a heading or paragraph appears, the header region is closed
- Duplicate directives are ignored with a warning — use each key only once
- The `abstract` value uses YAML `|` (literal block scalar) for multiline text

### 2. Labels — Attach BELOW the target node

```markdown
# Introduction
<!-- label: sec:intro -->

$$
E = mc^2
$$
<!-- label: eq:einstein -->

![Pipeline](fig.png)
<!-- caption: The pipeline -->
<!-- label: fig:pipeline -->
<!-- width: 0.85\textwidth -->
```

- Directives attach to the **previous sibling** (the node directly above)
- Multiple directives stack — order among them does not matter
- Use conventional prefixes: `sec:`, `fig:`, `tab:`, `eq:`, `alg:`, `thm:`

### 3. Citations — Link syntax with `cite:` scheme

```markdown
[Wang et al.](cite:wang2024)
[1-3](cite:wang2024,li2023,zhang2025)
[Wang](cite:wang2024?cmd=citet)
```

Valid `?cmd=` values: `cite`, `citep`, `citet`, `citeauthor`, `citeyear`, `textcite`, `parencite`, `autocite`.

**Do NOT** use `\cite{...}` raw LaTeX in body text. Always use the link syntax.

### 4. Cross-References — Link syntax with `ref:` scheme

```markdown
As shown in [Figure 1](ref:fig:pipeline), ...
See [Section 2](ref:sec:related) for details.
From [Equation 3](ref:eq:objective), we derive...
```

**Do NOT** use `\ref{...}` raw LaTeX. Always use the link syntax.

### 5. Math — Dollar delimiters only

```markdown
Inline: $T \in SE(3)$

Block:
$$
\min_{R,t} \sum_{i=1}^{n} \| R p_i + t - q_i \|^2
$$
<!-- label: eq:objective -->
```

- Inline math: single `$...$`
- Block math: `$$` on its own line, content, `$$` on its own line
- Add `<!-- label: eq:... -->` after block math for numbered equations
- No label = unnumbered equation

### 6. Tables — GFM pipe syntax + attach-up

```markdown
| Method | RMSE | Time (ms) |
|--------|------|-----------|
| ICP    | 2.3  | 150       |
| Ours   | 1.9  | 8         |
<!-- caption: Performance comparison -->
<!-- label: tab:results -->
```

- Use GFM alignment: `|:---|`, `|:---:|`, `|---:|`
- `caption` and `label` attach to the table above

### 7. Figures — Image + attach-up directives

```markdown
![Alt text for accessibility](figures/filename.png)
<!-- caption: Descriptive caption for the figure -->
<!-- label: fig:descriptive-label -->
<!-- width: 0.9\textwidth -->
```

For AI-generated figures, add `ai-*` directives:

```markdown
![Taxonomy](figures/taxonomy.png)
<!-- caption: Taxonomy of registration methods -->
<!-- label: fig:taxonomy -->
<!-- width: 0.9\textwidth -->
<!-- ai-generated: true -->
<!-- ai-prompt: |
  Academic diagram showing taxonomy of point cloud registration methods,
  tree structure with three main branches, clean vector style,
  white background, blue accent color
-->
```

### 8. Environments — `begin`/`end` pairs

```markdown
<!-- begin: theorem -->
For any compact set $K$, the ICP algorithm converges
to a local minimum in finite iterations.
<!-- end: theorem -->
<!-- label: thm:convergence -->
```

Common: `theorem`, `lemma`, `proof`, `definition`, `corollary`, `remark`, `example`, `algorithm`.

Environment-internal directives (`label`, `caption`, `options`, `args`) can go inside or after.

### 9. Raw LaTeX — Only for macros/commands

```markdown
<!-- begin: raw -->
\newcommand{\norm}[1]{\left\| #1 \right\|}
\DeclareMathOperator{\argmin}{arg\,min}
<!-- end: raw -->
```

Use sparingly. Prefer Markdown constructs over raw LaTeX for portability.

### 10. Code Blocks — Fenced with language

````markdown
```python
def icp(source, target):
    # Implementation
    pass
```
````

### 11. Footnotes

```markdown
Registration[^reg] is a core problem in 3D vision.

[^reg]: The process of aligning two or more 3D point sets.
```

## Feature Coverage Checklist

When writing a **test fixture** or **comprehensive example**, ensure you exercise:

- [ ] Document header with at least: `documentclass`, `packages`, `title`, `author`, `date`, `abstract`
- [ ] Multiple heading levels (`#`, `##`, `###`)
- [ ] Section labels (`<!-- label: sec:... -->`)
- [ ] Inline formatting: `**bold**`, `*italic*`, `` `code` ``
- [ ] Inline math: `$...$`
- [ ] Block math: `$$...$$` with and without labels
- [ ] Single-key citation: `[X](cite:key)`
- [ ] Multi-key citation: `[X](cite:a,b,c)`
- [ ] Citation with `?cmd=`: at least `citet` and `citep`
- [ ] Cross-references to sections, figures, tables, equations
- [ ] Figure with `caption`, `label`, `width`
- [ ] AI-generated figure with `ai-*` directives
- [ ] Table with `caption` and `label`
- [ ] Table with alignment (left/center/right columns)
- [ ] Ordered and unordered lists
- [ ] Nested lists
- [ ] Blockquote
- [ ] Code block with language
- [ ] Environment (`<!-- begin: theorem -->...<!-- end: theorem -->`)
- [ ] Raw LaTeX block (`<!-- begin: raw -->...<!-- end: raw -->`)
- [ ] Footnotes (`[^id]` and `[^id]: ...`)
- [ ] Thematic break (`---`)
- [ ] Link: `[text](url)`
- [ ] Multiple paragraphs with varied inline elements

## Common Mistakes to Avoid

| Wrong | Right | Why |
|-------|-------|-----|
| `\cite{key}` in body | `[Text](cite:key)` | Raw LaTeX citations are not parsed |
| `\ref{label}` in body | `[Text](ref:label)` | Raw LaTeX refs are not parsed |
| `\begin{equation}...\end{equation}` | `$$...$$` + `<!-- label: eq:... -->` | Use dollar math, not LaTeX environments |
| Label before target | Label after target | Directives attach **upward** |
| `<!-- title: ... -->` after `# Heading` | `<!-- title: ... -->` before any content | Document directives must be in header |
| `<!-- label: fig1 -->` | `<!-- label: fig:fig1 -->` | Use conventional prefix |
| `abstract: multi line` | `abstract: \| ↵  multi line` | Use YAML `\|` for multiline values |
| Directives on same line as content | Directives on separate lines | Each directive gets its own `<!-- -->` line |

## Output Targets

The `.mid.md` format converts to three targets:

1. **LaTeX** (`--target latex`): Full academic paper with `\documentclass`, `\begin{document}`, etc.
2. **Markdown** (`--target markdown`): Clean round-trip Markdown preserving all semantics
3. **HTML** (`--target html`): Self-contained HTML with MathJax and styling

Write `.mid.md` content that works well across all three.
