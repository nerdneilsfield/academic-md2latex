# markdown-it-py Token Structure Research

Version: markdown-it-py 4.0.0, mdit-py-plugins (latest)

## Setup

```python
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin

md = (
    MarkdownIt("commonmark", {"html": True})
    .use(dollarmath_plugin)
    .use(footnote_plugin)
    .enable("table")
)
tokens = md.parse(source)
tree = SyntaxTreeNode(tokens)
```

## Token Object

`markdown_it.token.Token` fields (via `as_dict()`):

| Field      | Type              | Description                                                |
|------------|-------------------|------------------------------------------------------------|
| `type`     | `str`             | Token type name, e.g. `"heading_open"`, `"text"`           |
| `tag`      | `str`             | HTML tag, e.g. `"h1"`, `"p"`, `"strong"`, `"math"`        |
| `nesting`  | `int`             | `1` = open, `0` = self-closing/inline, `-1` = close       |
| `attrs`    | `dict` or `None`  | HTML attributes, e.g. `{"style": "text-align:left"}`      |
| `map`      | `list[int]` or `None` | Source line range `[begin, end)` (block tokens only)    |
| `level`    | `int`             | Nesting depth in token stream                              |
| `children` | `list[Token]` or `None` | Inline children (only on `inline` tokens)            |
| `content`  | `str`             | Text content (for leaf tokens and `inline` tokens)         |
| `markup`   | `str`             | Markup character(s): `"#"`, `"**"`, `` "`" ``, `"$$"`, etc. |
| `info`     | `str`             | Extra info, e.g. language string on fenced code blocks     |
| `meta`     | `dict`            | Plugin metadata, e.g. footnote `{"id": 0, "label": "note"}` |
| `block`    | `bool`            | `True` for block-level tokens                              |
| `hidden`   | `bool`            | If `True`, token should not be rendered                    |

## SyntaxTreeNode

`SyntaxTreeNode(tokens)` converts the flat token list into a tree. Key properties:

| Property         | Type                              | Description                                      |
|------------------|-----------------------------------|--------------------------------------------------|
| `type`           | `str`                             | Node type (strips `_open`/`_close` suffixes)     |
| `tag`            | `str`                             | HTML tag (from opening token)                    |
| `content`        | `str`                             | Text content                                     |
| `markup`         | `str`                             | Markup characters                                |
| `map`            | `tuple[int,int]` or `None`        | Source line range (tuple, not list)               |
| `meta`           | `dict`                            | Plugin metadata                                  |
| `attrs`          | `dict`                            | HTML attributes                                  |
| `children`       | `list[SyntaxTreeNode]`            | Child nodes                                      |
| `parent`         | `SyntaxTreeNode` or `None`        | Parent node                                      |
| `is_root`        | `bool`                            | True for root node                               |
| `is_nested`      | `bool`                            | True for nodes from open/close token pairs        |
| `token`          | `Token` or `None`                 | Underlying token (leaf nodes only)               |
| `nester_tokens`  | `_NesterTokens` or `None`         | `(opening, closing)` tokens (nested nodes only)  |
| `walk()`         | `Iterator[SyntaxTreeNode]`        | Depth-first traversal                            |
| `pretty()`       | `str`                             | Pretty-printed tree representation               |

**Important**: For nested nodes (e.g., `heading`, `paragraph`, `strong`), `.token` is `None`. Access the opening/closing tokens via `.nester_tokens.opening` / `.nester_tokens.closing`.

## Token Types by Category

### 1. Headings

Input: `# Hello **world**`

```
heading_open   tag='h1', nesting=1, markup='#', map=[0,1]
  inline       content='Hello **world**', children=[...]
    text       content='Hello '
    strong_open  tag='strong', markup='**'
    text       content='world'
    strong_close tag='strong', markup='**'
heading_close  tag='h1', nesting=-1, markup='#'
```

SyntaxTreeNode:
```
root
  heading  tag='h1', markup='#', map=(0,1)  [nester_tokens]
    inline  content='Hello **world**'  [token]
      text  content='Hello '  [token]
      strong  tag='strong', markup='**'  [nester_tokens]
        text  content='world'  [token]
```

### 2. Paragraphs

Input: `A paragraph.`

```
paragraph_open  tag='p', nesting=1, map=[0,1]
  inline        content='A paragraph.'
    text        content='A paragraph.'
paragraph_close tag='p', nesting=-1
```

### 3. Math (dollarmath plugin)

**Inline math** (`$...$`): Token type `math_inline`, tag `math`, markup `$`

Input: `Here is $x^2$ inline.`
```
paragraph_open
  inline  content='Here is $x^2$ inline.'
    text         content='Here is '
    math_inline  tag='math', content='x^2', markup='$', block=False
    text         content=' inline.'
paragraph_close
```

**Block math** (`$$...$$`): Token type `math_block`, tag `math`, markup `$$`

Input: `$$\na + b = c\n$$`
```
math_block  tag='math', content='\na + b = c\n', markup='$$', map=[0,3], block=True
```

**Key**: `math_inline` is a child of an `inline` token. `math_block` is a standalone block token (no open/close pair). Content includes the math expression without delimiters. Content of `math_block` has leading/trailing newlines.

### 4. Footnotes (footnote plugin)

Input: `Text[^note].\n\n[^note]: Footnote content.`

**Inline reference** (child of `inline` token):
```
footnote_ref  meta={'id': 0, 'subId': 0, 'label': 'note'}
```

**Footnote definitions** (block-level, at end of token stream):
```
footnote_block_open   nesting=1
  footnote_open       nesting=1, meta={'id': 0, 'label': 'note'}
    paragraph_open
      inline          content='Footnote content.'
        text          content='Footnote content.'
    footnote_anchor   meta={'id': 0, 'subId': 0, 'label': 'note'}
    paragraph_close
  footnote_close      nesting=-1
footnote_block_close  nesting=-1
```

**Key**: `footnote_ref.meta.id` links to `footnote_open.meta.id`. The label is the original `[^label]` text.

### 5. Tables

Input: `| A | B |\n|---|---|\n| 1 | 2 |`

```
table_open   tag='table', map=[0,3]
  thead_open   tag='thead', map=[0,1]
    tr_open      tag='tr', map=[0,1]
      th_open      tag='th', nesting=1
        inline       content='A'
          text       content='A'
      th_close     tag='th'
      th_open      tag='th'
        inline       content='B'
          text       content='B'
      th_close     tag='th'
    tr_close     tag='tr'
  thead_close  tag='thead'
  tbody_open   tag='tbody', map=[2,3]
    tr_open      tag='tr', map=[2,3]
      td_open      tag='td'
        inline       content='1'
          text       content='1'
      td_close     tag='td'
      td_open      tag='td'
        inline       content='2'
          text       content='2'
      td_close     tag='td'
    tr_close     tag='tr'
  tbody_close  tag='tbody'
table_close  tag='table'
```

**Alignment**: `th_open` and `td_open` carry `attrs={'style': 'text-align:left|center|right'}` when alignment is specified via `:---|:---:|---:`.

### 6. HTML Block Comments

Input: `<!-- label: sec:intro -->`

```
html_block  content='<!-- label: sec:intro -->\n', map=[0,1]
```

**Key**: Standalone HTML comments on their own line produce a single `html_block` token. Content includes trailing newline. No nesting, no children.

### 7. HTML Inline Comments

Input: `text <!-- comment --> more`

```
paragraph_open
  inline  content='text <!-- comment --> more'
    text         content='text '
    html_inline  content='<!-- comment -->'
    text         content=' more'
paragraph_close
```

**Key**: `html_inline` is a child of an `inline` token, similar to `math_inline`. Content is the raw HTML including comment delimiters.

### 8. Lists

**Ordered list**:
```
ordered_list_open  tag='ol', markup='.'
  list_item_open     tag='li', markup='.'
    paragraph_open
      inline  content='First'
    paragraph_close
  list_item_close
ordered_list_close
```

**Bullet list**:
```
bullet_list_open  tag='ul', markup='-'
  list_item_open    tag='li', markup='-'
    ...
  list_item_close
bullet_list_close
```

### 9. Blockquotes

```
blockquote_open   tag='blockquote', markup='>'
  paragraph_open
    inline  content='A quote\ncontinued'
      text      content='A quote'
      softbreak
      text      content='continued'
  paragraph_close
blockquote_close
```

### 10. Images

Input: `![Alt text](image.png)`

```
paragraph_open
  inline
    image  tag='img', content='Alt text', attrs={'src': 'image.png', 'alt': ''}
      text  content='Alt text'   (children contain alt text tokens)
paragraph_close
```

**Key**: `image` is a self-closing inline token (nesting=0). `attrs.src` has the URL. Children contain the alt text as parsed tokens.

### 11. Links

Input: `[Click here](https://example.com)`

```
paragraph_open
  inline
    link_open   tag='a', attrs={'href': 'https://example.com'}
    text        content='Click here'
    link_close  tag='a'
paragraph_close
```

### 12. Code

**Fenced code block**:
```
fence  tag='code', info='python', content='print("hello")\n', markup='```', map=[0,3]
```

**Inline code**:
```
code_inline  tag='code', content='code', markup='`'
```

### 13. Emphasis

**Bold** (`**text**`):
```
strong_open   tag='strong', markup='**'
text          content='text'
strong_close  tag='strong', markup='**'
```

**Italic** (`*text*`):
```
em_open   tag='em', markup='*'
text      content='text'
em_close  tag='em', markup='*'
```

### 14. Other Tokens

| Type        | Tag    | Description                     |
|-------------|--------|---------------------------------|
| `hr`        | `hr`   | Horizontal rule (`---`)         |
| `softbreak` | `br`   | Newline within paragraph        |
| `hardbreak` | `br`   | Forced line break (two spaces)  |

## Token Stream Pattern

Block tokens follow an open/close pattern:
```
xxx_open (nesting=1)
  inline (nesting=0, children=[...])
    text / strong_open / math_inline / etc.
xxx_close (nesting=-1)
```

Some tokens are self-contained (no open/close):
- `math_block` (nesting=0)
- `html_block` (nesting=0)
- `fence` (nesting=0)
- `hr` (nesting=0)

Inline tokens are always children of an `inline` token:
- `text`, `code_inline`, `softbreak`, `hardbreak`
- `math_inline`, `html_inline`, `footnote_ref`
- `image` (self-closing, has children for alt text)
- `strong_open`/`strong_close`, `em_open`/`em_close`
- `link_open`/`link_close`

## Comprehensive SyntaxTreeNode Walk Example

Input combining all features:
```
root
  heading       tag='h1', markup='#', map=(0, 1)
    inline        content='Introduction', map=(0, 1)
      text          content='Introduction'
  paragraph     tag='p', map=(2, 3)
    inline        content='Some text with $E=mc^2$ inline math.'
      text          content='Some text with '
      math_inline   tag='math', content='E=mc^2', markup='$'
      text          content=' inline math.'
  math_block    tag='math', content='\n\\int_0^1 f(x)\\,dx\n', markup='$$', map=(4, 7)
  table         tag='table', map=(10, 13)
    thead / tbody / tr / th / td hierarchy...
  paragraph     tag='p', map=(14, 15)
    inline        content='Text[^note].'
      text          content='Text'
      footnote_ref  (meta.id=0, meta.label='note')
      text          content='.'
  html_block    content='<!-- label: sec:intro -->\n', map=(18, 19)
  footnote_block
    footnote      (meta.id=0, meta.label='note')
      paragraph
        inline      content='A footnote.'
          text        content='A footnote.'
        footnote_anchor  (meta.id=0)
```

## Key Findings for md-mid Parser Design

1. **SyntaxTreeNode vs raw tokens**: Use `SyntaxTreeNode` for tree-based traversal. It auto-merges `_open`/`_close` pairs into single nested nodes. Use `.walk()` for depth-first iteration.

2. **Nested vs leaf nodes**: Check `node.is_nested` to determine if a node wraps children. For nested nodes, access opening token via `node.nester_tokens.opening`. For leaf nodes, access `node.token` directly.

3. **Math tokens**: `math_inline` (inline, child of `inline`) and `math_block` (standalone block). Content is the raw math without delimiters. Block math content has leading/trailing newlines.

4. **HTML comments for directives**: Both `html_block` and `html_inline` tokens carry the full `<!-- ... -->` content. Parse with regex to extract directive key/value pairs.

5. **Footnotes**: `footnote_ref` inline tokens link to `footnote_open` block tokens via `meta.id`. The footnote block section appears at the end of the token stream wrapped in `footnote_block_open`/`close`.

6. **Table alignment**: Column alignment is encoded as `style` attributes on `th_open`/`td_open` tokens: `text-align:left|center|right`.

7. **Source maps**: Block tokens have `map` as `[begin, end)` line numbers. SyntaxTreeNode converts to tuple `(begin, end)`. Inline tokens and closing tokens have `map=None`.

8. **image token**: Has `attrs.src` for URL and children for alt text tokens. It is self-closing (nesting=0) despite having children.

9. **fence token**: Single self-contained token with `info` field for language, `content` for code body (includes trailing newline), `markup` for delimiter style.
