# Examples Usage Guide

This directory contains an end-to-end ICP survey example:

- Source manuscript: `examples/icp-survey.mid.md`
- Bibliography: `examples/icp.bib`
- Figure assets: `examples/images/`
- LaTeX build config: `examples/latexmkrc`, `examples/.latexignore`

All commands below assume you run them from the repository root (`academic-md2latex/`).

## 1) Generate Figures

### 1.1 Prepare figure runner config

Create a local config file first:

```bash
cp generator_config.example.toml generator_config.toml
```

Then edit `generator_config.toml` and fill your API settings (`api_key`, `api_base_url`, `model`).

### 1.2 Generate all AI-marked figures

```bash
uv run wenqiao generate examples/icp-survey.mid.md \
  --figures-config generator_config.toml \
  --model openai \
  --concurrency 4
```

Useful options:

- Force regenerate existing files:

```bash
uv run wenqiao generate examples/icp-survey.mid.md \
  --figures-config generator_config.toml \
  --model openai \
  --force
```

- Generate only a figure range (1-based index):

```bash
uv run wenqiao generate examples/icp-survey.mid.md \
  --figures-config generator_config.toml \
  --model openai \
  --start-id 1 \
  --end-id 10
```

## 2) Convert to Different Formats

### 2.1 Optional: safe formatting pass

If you want a non-destructive formatting output first:

```bash
uv run wenqiao format examples/icp-survey.mid.md -o examples/icp-survey.mid.test.md
```

Check without writing (exit 1 if not clean):

```bash
uv run wenqiao format examples/icp-survey.mid.md --check --diff
```

Format in-place with statistics:

```bash
uv run wenqiao format examples/icp-survey.mid.md --stats
```

### 2.2 Convert to LaTeX

```bash
uv run wenqiao convert examples/icp-survey.mid.md \
  -t latex \
  --bib examples/icp.bib \
  -o examples/icp-survey.tex
```

### 2.3 Convert to rich Markdown

```bash
uv run wenqiao convert examples/icp-survey.mid.md \
  -t markdown \
  -o examples/icp-survey.rendered.md
```

### 2.4 Convert to HTML

```bash
uv run wenqiao convert examples/icp-survey.mid.md \
  -t html \
  -o examples/icp-survey.html
```

## 3) Compile LaTeX to PDF

After generating `examples/icp-survey.tex`, compile with `latexmk`:

```bash
cd examples
latexmk -r latexmkrc -xelatex -pdf icp-survey.tex
```

Output PDF path:

`examples/build/icp-survey.pdf`

Clean auxiliary files:

```bash
cd examples
latexmk -r latexmkrc -c icp-survey.tex
```

Full clean (including PDF):

```bash
cd examples
latexmk -r latexmkrc -C icp-survey.tex
```
