# ruamel.yaml Usage Research for Comment Processor

Version: ruamel.yaml 0.19.1

## Summary

`ruamel.yaml` with `typ='safe'` is the recommended YAML parser for the Comment Processor. It blocks dangerous YAML tags, returns plain Python types (`dict`/`list`/`str`), and correctly handles block scalars. One caveat: date-like strings are auto-coerced to `datetime.date` objects and must be normalized back to strings.

## Target Inputs (HTML comment content after stripping delimiters)

| Input | Parsed Result |
|-------|---------------|
| `label: sec:intro` | `{'label': 'sec:intro'}` |
| `packages: [amsmath, graphicx]` | `{'packages': ['amsmath', 'graphicx']}` |
| `package-options:\n  geometry: "margin=1in"` | `{'package-options': {'geometry': 'margin=1in'}}` |
| `abstract: \|\n  Line one\n  Line two` | `{'abstract': 'Line one\nLine two'}` |
| `ai-params: {seed: 42, steps: 50}` | `{'ai-params': {'seed': 42, 'steps': 50}}` |

All five target inputs parse correctly.

## YAML Loading Modes

| Mode | Constructor | Returns | Blocks dangerous tags | Notes |
|------|-------------|---------|----------------------|-------|
| `YAML(typ='safe')` | SafeConstructor | `dict`, `list`, `str`, `int`, `float`, `bool`, `None`, `datetime.date` | Yes | **Recommended** |
| `YAML()` (round-trip) | RoundTripConstructor | `CommentedMap`, `CommentedSeq`, `LiteralScalarString` | **No** | Preserves formatting but unsafe |
| `YAML(typ='base')` | BaseConstructor | `dict`, `list`, `str` (no int/float coercion) | **No** | Everything is a string |

**Use `YAML(typ='safe')`**. Round-trip mode (`YAML()`) does NOT block dangerous YAML tags like `!!python/object/apply:os.system` -- this is a critical security issue since HTML comments come from user input.

## Block Scalar Preservation

Both modes preserve newlines correctly in block scalars (`|`):

```
abstract: |
  Line one
  Line two
```

Parses to: `'Line one\nLine two'` (str)

The `|` (literal) style preserves newlines. The `>` (folded) style joins lines with spaces:

| Style | Input | Result |
|-------|-------|--------|
| `\|` (literal) | `Line one\nLine two` | `'Line one\nLine two'` |
| `>` (folded) | `Line one\nLine two` | `'Line one Line two'` |
| `\|` with trailing `\n` | `Line one\nLine two\n` | `'Line one\nLine two\n'` |

## Value Type Coercion (safe mode)

| YAML Value | Python Type | Example |
|------------|-------------|---------|
| `simple string` | `str` | `'simple string'` |
| `42` | `int` | `42` |
| `3.14` | `float` | `3.14` |
| `true` / `false` | `bool` | `True` / `False` |
| `null` / `~` | `NoneType` | `None` |
| `[a, b, c]` | `list` | `['a', 'b', 'c']` |
| `{x: 1, y: 2}` | `dict` | `{'x': 1, 'y': 2}` |
| `sec:intro` | `str` | `'sec:intro'` (colons in values are fine) |
| `2024-01-15` | `datetime.date` | `datetime.date(2024, 1, 15)` -- **needs normalization** |
| `"2024-01-15"` | `str` | `'2024-01-15'` |

**Important**: Date-like strings (`YYYY-MM-DD`) are coerced to `datetime.date`. The normalization function below converts them back to strings.

## Error Handling

| Input | Behavior |
|-------|----------|
| `""` (empty) | Returns `None` |
| `"  "` (whitespace) | Returns `None` |
| `"foo"` (bare string) | Returns `str`, not `dict` |
| `"42"` (bare number) | Returns `int`, not `dict` |
| `"not: valid: yaml: here"` | Raises `ScannerError` |
| `"key: [unclosed"` | Raises `ParserError` |
| `": no-key"` | Returns `{None: 'no-key'}` (dict with None key) |
| `"key: value\nextra: value"` | Returns multi-key dict (valid) |
| `"just a regular comment"` | Returns `str`, not `dict` |

**Key insight**: Non-directive comments (like `"just a regular comment"`) parse as bare strings, not dicts. The `isinstance(result, dict)` check cleanly distinguishes directives from regular comments.

## Recommended Code Pattern

```python
from __future__ import annotations

import datetime
from typing import Any

from ruamel.yaml import YAML


def parse_comment_yaml(html_comment: str) -> dict[str, Any] | None:
    """Parse YAML directives from an HTML comment.

    Extracts the text between <!-- and -->, attempts YAML parsing,
    and returns a plain Python dict on success. Returns None if:
    - The comment is empty
    - The content is not valid YAML
    - The YAML does not produce a dict (e.g., bare strings, numbers)

    Uses safe mode to block dangerous YAML tags.
    """
    yaml = YAML(typ="safe")

    # Strip <!-- and --> delimiters
    text = html_comment.strip()
    if text.startswith("<!--"):
        text = text[4:]
    if text.endswith("-->"):
        text = text[:-3]
    text = text.strip()

    if not text:
        return None

    try:
        result = yaml.load(text)
    except Exception:
        return None

    if not isinstance(result, dict):
        return None

    return _normalize(result)


def _normalize(obj: Any) -> Any:
    """Convert ruamel.yaml types to plain Python types.

    - datetime.date/datetime -> str (YAML auto-coerces date-like strings)
    - Ensures all dict keys are str
    - Preserves int, float, bool, None as-is
    """
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(i) for i in obj]
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return str(obj)
    if isinstance(obj, str):
        return str(obj)  # ensure plain str, not LiteralScalarString subclass
    return obj
```

## Test Results for Recommended Pattern

```
'<!-- label: sec:intro -->'                    -> {'label': 'sec:intro'}
'<!-- packages: [amsmath, graphicx] -->'       -> {'packages': ['amsmath', 'graphicx']}
'<!-- package-options:\n  geometry: ... -->'    -> {'package-options': {'geometry': 'margin=1in'}}
'<!-- abstract: |\n  Line one\n  Line two -->' -> {'abstract': 'Line one\nLine two'}
'<!-- ai-params: {seed: 42, steps: 50} -->'    -> {'ai-params': {'seed': 42, 'steps': 50}}
'<!-- date: 2024-01-15 -->'                    -> {'date': '2024-01-15'}
'<!-- just a regular comment -->'              -> None
'<!-- -->'                                     -> None
'<!-- not: valid: yaml -->'                    -> None
```

## Performance Note

Creating `YAML(typ='safe')` is lightweight. It is fine to create a new instance per call, but if the comment processor processes many comments, a module-level instance can be reused since `YAML.load()` is stateless for parsing.

## Key Decisions for Comment Processor

1. **Use `YAML(typ='safe')`** -- blocks code execution via YAML tags.
2. **Check `isinstance(result, dict)`** -- cleanly filters out non-directive comments.
3. **Normalize dates** -- `datetime.date` objects must be converted back to `str`.
4. **Catch broad `Exception`** -- both `ScannerError` and `ParserError` can be raised; catching `Exception` is simplest and safest.
5. **Strip delimiters first** -- remove `<!--` and `-->` before passing to YAML parser.
6. **Multi-key comments are valid** -- a single comment can contain multiple directives (e.g., `<!-- title: Foo\nauthor: Bar -->`).
