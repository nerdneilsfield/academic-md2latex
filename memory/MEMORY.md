# Project Memory — academic-md2latex

## Project Overview
- **Repo**: academic-md2latex / CLI tool: `md-mid`
- **Format**: md-mid (Markdown-based academic writing intermediate format)
- **Stack**: Python 3.14, markdown-it-py, ruamel.yaml, click, pytest, uv, ruff, mypy

## Phase Status
- **Phase 1**: ✅ Complete (core pipeline, LaTeX renderer, citations, cross-refs)
- **Phase 2**: ✅ Complete (Rich Markdown renderer, figures, tables, citations→footnotes)
- **Phase 3**: ✅ Complete (2026-03-03) — see below
- **Phase 4**: ⏳ Planned (template system, i18n/locale for LaTeX, minted/lstlisting config)

## Phase 3 Completed (2026-03-03)

7 commits merged to master:
- `8e3b390` refactor(nodes,parser): Table to Node-based cells
- `5264956` feat(latex): rich inline content in table cells
- `91473a3` feat(markdown): rich table cells as HTML
- `b87d483` feat(markdown): nested list indentation
- `4d4e690` feat(markdown,cli): --locale option (zh/en)
- `c920be2` feat(cli): stdin (-) / stdout (-o -) support
- `2dd2a78` feat(markdown,cli): body/fragment modes

Final test count: **241 tests**, make check clean (ruff 0, mypy 0).

## Architecture Notes

### EAST Node Types (src/md_mid/nodes.py)
- `Table.headers: list[CellContent]` where `CellContent = list[Node]`
- `Table.rows: list[TableRow]` where `TableRow = list[CellContent]`
- `Table.to_dict()` overridden to serialize nested node lists

### Key Rendering Patterns
- **LaTeX table cells**: `self._render_nodes(cell)` — renders list of Node
- **Markdown table cells**: `self._render_cell_html(cell)` + `self._render_node_html(node)` — ALL text through `_esc()`
- **MathInline in HTML**: raw `$content$` (no escape — by design, MathJax needs unescaped)
- **Nested lists**: `self._list_depth` tracks depth, `"  " * depth` indentation

### MarkdownRenderer.__init__ signature (after Phase 3)
```python
def __init__(
    self,
    bib: dict[str, str] | None = None,
    heading_id_style: str = "attr",
    locale: str = "zh",    # Phase 3: "zh" | "en"
    mode: str = "full",    # Phase 3: "full" | "body" | "fragment"
    diag: DiagCollector | None = None,
) -> None:
```

### CLI Options (after Phase 3)
- `--locale [zh|en]` — figure/table label language (default: zh)
- `--mode [full|body|fragment]` — output mode for Markdown target
- `-` as input — reads from stdin
- `-o -` as output — writes to stdout, suppresses "Written to" message

## Test Patterns
- `doc(*nodes)` helper in test files creates Document
- `render(doc)` helper calls MarkdownRenderer/LaTeXRenderer
- `_cells(*texts)` — wraps strings as `[[Text(content=t)]]` list
- `_rows(*row_texts)` — wraps string rows as `[[[Text(content=t)]]]`
- Test class naming: `TestTableRichCells`, `TestNestedList`, `TestLocale`, `TestMarkdownModes`

## Build Commands
```bash
make test       # uv run pytest -v --tb=short
make check      # ruff + mypy + pytest
make lint       # ruff check
make typecheck  # mypy src/md_mid/
```

## Claude Flow V3 Swarm Pattern (used for Phase 3)
- Init: `npx @claude-flow/cli@latest swarm init --topology hierarchical --max-agents 8 --strategy specialized`
- TeamCreate → TaskCreate (all tasks) → Spawn 4 agents in ONE message (run_in_background: true)
- Coordination: coder notifies tester after each commit; tester runs make check; reviewer does final review
- Tasks 1→2→3 must be sequential (type change cascades); Tasks 4-7 also sequential (shared files)
- After Plan Task 1: latex/markdown table tests EXPECTED to fail (fixed in Tasks 2-3)

## Coding Standards
- All functions: complete type annotations
- All comments: bilingual English (中文)
- Files: stay under 500 lines (markdown.py at 524 — acceptable given Phase 3 scope)
- Escape: ALL HTML text output through `_esc()` in markdown renderer
