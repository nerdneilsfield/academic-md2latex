"""HTML renderer — converts EAST to self-contained academic HTML.

HTML 渲染器 — 将 EAST 转换为自包含的学术 HTML。
"""

from __future__ import annotations

import html as _html_lib
import re
from typing import cast

from wenqiao.ai_meta import render_ai_details_html
from wenqiao.diagnostic import DiagCollector
from wenqiao.nodes import (
    Citation,
    CodeBlock,
    CodeInline,
    CrossRef,
    Document,
    Environment,
    Figure,
    FootnoteDef,
    FootnoteRef,
    Heading,
    Image,
    Link,
    List,
    MathBlock,
    MathInline,
    Node,
    Paragraph,
    RawBlock,
    Table,
    Text,
)
from wenqiao.parser import parse
from wenqiao.url_check import is_unsafe_url


def _esc(text: str) -> str:
    """HTML-escape text (HTML 转义文本)."""
    return _html_lib.escape(text, quote=True)


# Safe width pattern: digits + CSS units only (安全宽度正则：仅数字 + CSS 单位)
_SAFE_WIDTH_RE = re.compile(r"^\d+(\.\d+)?(px|em|rem|%|cm|mm|pt|vw)$")
_SLUG_INVALID_RE = re.compile(r"[^\w\u4e00-\u9fff-]+", re.UNICODE)
_LATEX_TABULAR_RE = re.compile(
    r"\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}",
    re.DOTALL,
)


# KaTeX + MathJax CDNs (KaTeX + MathJax CDN 链接)
_KATEX_CSS_CDN = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
_KATEX_JS_CDN = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
_KATEX_AUTORENDER_CDN = (
    "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
)
_MATHJAX_CDN = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
_DEFAULT_IMAGE_MAX_WIDTH = "92%"
_TOC_INTERACTION_JS = """\
(() => {
  const toc = document.querySelector(".toc-panel");
  if (!toc) return;
  const links = toc.querySelectorAll(".toc-nav a");
  links.forEach((a) => {
    a.addEventListener("click", () => {
      if (window.matchMedia("(max-width: 1180px)").matches) toc.removeAttribute("open");
    });
  });
  document.addEventListener("click", (ev) => {
    if (!toc.hasAttribute("open")) return;
    if (window.matchMedia("(max-width: 1180px)").matches && !toc.contains(ev.target)) {
      toc.removeAttribute("open");
    }
  });
})();
"""
_MATH_RENDER_JS = r"""\
(() => {
  const log = (...args) => console.log("[wenqiao-math]", ...args);
  const done = (name) => document.documentElement.setAttribute("data-math-renderer", name);
  const katexDelimiters = [
    { left: "$$", right: "$$", display: true },
    { left: "\\[", right: "\\]", display: true },
    { left: "$", right: "$", display: false },
    { left: "\\(", right: "\\)", display: false },
  ];

  let attempts = 0;
  const maxAttempts = 30;
  const stepMs = 120;
  log("init", { maxAttempts, stepMs });

  const renderWithKaTeX = () => {
    if (typeof window.renderMathInElement !== "function") return false;
    try {
      window.renderMathInElement(document.body, {
        delimiters: katexDelimiters,
        throwOnError: false,
        strict: "ignore",
      });
      log("KaTeX render success");
      done("katex");
      return true;
    } catch (err) {
      log("KaTeX render failed, will fallback", err);
      return false;
    }
  };

  const renderWithMathJax = () => {
    if (!window.MathJax || typeof window.MathJax.typesetPromise !== "function") return false;
    log("fallback to MathJax");
    window.MathJax.typesetPromise()
      .then(() => {
        log("MathJax render success");
        done("mathjax");
      })
      .catch((err) => {
        log("MathJax render failed", err);
        done("mathjax-error");
      });
    return true;
  };

  const tick = () => {
    if (renderWithKaTeX()) return;
    if (renderWithMathJax()) return;
    attempts += 1;
    if (attempts < maxAttempts) {
      window.setTimeout(tick, stepMs);
    } else {
      log("no math renderer became available");
      done("none");
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tick, { once: true });
  } else {
    tick();
  }
})();
"""


def _normalize_css_width(value: object, *, fallback: str = _DEFAULT_IMAGE_MAX_WIDTH) -> str:
    """Normalize CSS width and clamp percentage to <=100 (规范化宽度并限制百分比 <=100)."""
    text = str(value).strip()
    if not text:
        return fallback
    if not _SAFE_WIDTH_RE.match(text):
        return fallback
    if text.endswith("%"):
        try:
            pct = float(text[:-1])
        except ValueError:
            return fallback
        pct = max(0.0, min(100.0, pct))
        if pct.is_integer():
            return f"{int(pct)}%"
        return f"{pct:g}%"
    return text


def _slugify_heading(text: str) -> str:
    """Build stable heading slug for TOC and anchor ids (为目录和锚点生成稳定 slug)."""
    s = re.sub(r"\s+", "-", text.strip().lower())
    s = _SLUG_INVALID_RE.sub("", s)
    return s.strip("-_")


def _build_css(image_max_width: str) -> str:
    """Build HTML stylesheet with configurable image max-width."""
    return f"""\
:root {{
  --content-max-width: 920px;
  --image-max-width: {image_max_width};
  --toc-width: 260px;
  --paper-bg: #f4f6fa;
  --surface-bg: #ffffff;
  --text-main: #1f2733;
  --text-muted: #4d5b70;
  --line-soft: #dbe2ec;
  --line-strong: #c8d2df;
  --accent: #275f9b;
  --accent-soft: #ecf3fb;
}}
html {{
  scroll-behavior: smooth;
  background: var(--paper-bg);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: var(--text-main);
  background: var(--paper-bg);
  font-family:
    "Source Han Serif SC",
    "Noto Serif CJK SC",
    "Noto Serif SC",
    "Songti SC",
    "STSong",
    "PingFang SC",
    "Microsoft YaHei",
    serif;
  line-height: 1.78;
  font-size: 17px;
  letter-spacing: 0.01em;
  font-kerning: normal;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  line-break: auto;
  word-break: normal;
  padding: 2em 1.2em;
  overflow-x: hidden;
}}
.content-wrap {{
  width: min(var(--content-max-width), calc(100vw - 2.4rem));
  margin-left: auto;
  margin-right: auto;
  background: var(--surface-bg);
  border: 1px solid var(--line-soft);
  border-radius: 14px;
  box-shadow: 0 10px 24px rgba(34, 55, 84, 0.06);
  padding: 1.55rem 1.45rem 1.7rem;
}}
p {{
  margin: 0.72em 0 0.9em;
  color: var(--text-main);
}}
a {{
  color: var(--accent);
  text-decoration: none;
  text-underline-offset: 0.16em;
}}
a:hover {{ text-decoration: underline; }}
.doc-header {{
  margin-bottom: 1.25em;
  text-align: center;
  padding-bottom: 0.85em;
  border-bottom: 1px solid var(--line-soft);
}}
.doc-title {{
  margin: 0;
  font-size: clamp(1.72rem, 2.3vw, 2.24rem);
  line-height: 1.3;
  letter-spacing: 0.025em;
  font-family:
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
}}
.doc-author {{
  margin: 0.35em 0 0;
  color: var(--text-muted);
  font-size: 1rem;
}}
.doc-date {{
  margin: 0.2em 0 0;
  color: #64748a;
  font-size: 0.94rem;
}}
.doc-abstract {{
  margin: 0.82em auto 0;
  max-width: 74ch;
  text-align: left;
  color: #2d3a4a;
}}
h1, h2, h3, h4 {{
  color: #1f2f45;
  font-family:
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
  font-weight: 650;
  line-height: 1.35;
  margin-top: 1.45em;
  margin-bottom: 0.5em;
}}
h1 {{ font-size: 1.95rem; }}
h2 {{ font-size: 1.58rem; }}
h3 {{ font-size: 1.3rem; }}
h4 {{ font-size: 1.13rem; }}
img {{ max-width: 100%; height: auto; }}
figure {{
  text-align: center;
  margin: 1.5em auto;
  padding: 0.55rem 0.45rem 0.7rem;
  border-radius: 10px;
  background: #fbfcff;
  border: 1px solid var(--line-soft);
}}
figure img {{
  max-width: min(100%, var(--image-max-width));
  border-radius: 8px;
  border: 1px solid var(--line-soft);
}}
figcaption {{
  font-style: normal;
  margin-top: 0.55em;
  color: #35465c;
  font-size: 0.95em;
  line-height: 1.62;
}}
table {{
  border-collapse: collapse;
  margin: 0.75em auto 0;
  background: #fff;
}}
th, td {{
  border: 1px solid var(--line-strong);
  padding: 0.45em 0.78em;
  vertical-align: top;
}}
th {{
  background: var(--accent-soft);
  color: #1f3858;
  font-weight: 650;
}}
tbody tr:nth-child(even) {{ background: #fafcff; }}
.table-wrap {{
  text-align: center;
  margin: 1.5em 0;
  overflow-x: auto;
  max-width: 100%;
  border-radius: 10px;
}}
.table-wrap table {{
  width: max-content;
  min-width: 100%;
}}
.table-caption {{
  font-style: normal;
  margin-bottom: 0.45em;
  color: #334a67;
}}
pre {{
  background: #f7f9fd;
  border: 1px solid var(--line-soft);
  padding: 0.92em 1em;
  overflow-x: auto;
  border-radius: 8px;
}}
code {{
  font-family:
    "JetBrains Mono",
    "SFMono-Regular",
    "Fira Code",
    "Cascadia Mono",
    "Menlo",
    "Consolas",
    monospace;
  font-size: 0.9em;
}}
pre code {{ line-height: 1.55; }}
p, li, figcaption, td, th {{ overflow-wrap: anywhere; }}
blockquote {{
  border-left: 4px solid #9fb4d1;
  margin-left: 0;
  padding: 0.2em 0 0.2em 0.95em;
  color: #41516a;
  background: #f7fbff;
  border-radius: 0 6px 6px 0;
}}
.footnotes {{
  border-top: 1px solid var(--line-strong);
  margin-top: 3em;
  padding-top: 0.5em;
  font-size: 0.92em;
}}
.bibliography {{ margin-top: 2em; }}
details {{
  background: #fafcff;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  padding: 0.5em 0.9em;
  margin: 1em 0;
}}
summary {{ cursor: pointer; font-weight: 650; color: #2b425f; }}
.toc-panel {{
  position: fixed;
  left: 1rem;
  top: 1rem;
  width: auto;
  max-height: none;
  overflow: visible;
  z-index: 20;
  background: transparent;
  border: 0;
  box-shadow: none;
}}
.toc-panel > summary {{
  list-style: none;
  margin: 0;
  padding: 0.52em 0.8em;
  background: #fff;
  border: 1px solid var(--line-soft);
  box-shadow: 0 6px 14px rgba(22, 45, 73, 0.11);
  cursor: pointer;
  user-select: none;
  font-weight: 600;
  border-radius: 999px;
}}
.toc-panel > summary::after {{
  content: "▸";
  margin-left: 0.45em;
  color: #777;
}}
.toc-panel[open] {{
  width: min(var(--toc-width), calc(100vw - 2rem));
  max-height: calc(100vh - 5rem);
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  box-shadow: 0 14px 30px rgba(17, 39, 64, 0.14);
}}
.toc-panel[open] > summary {{
  border: 0;
  border-bottom: 1px solid var(--line-soft);
  border-radius: 10px 10px 0 0;
  box-shadow: none;
  padding: 0.65em 0.8em;
}}
.toc-panel[open] > summary::after {{ content: "▾"; }}
.toc-panel > summary::-webkit-details-marker {{ display: none; }}
.toc-nav {{
  display: none;
  max-height: calc(100vh - 11rem);
  overflow: auto;
  padding: 0.35em 0.35em 0.7em;
}}
.toc-panel[open] .toc-nav {{ display: block; }}
.toc-nav ul {{
  margin: 0;
  padding-left: 0.45em;
  list-style: none;
}}
.toc-nav li {{ margin: 0.22em 0; line-height: 1.35; }}
.toc-nav a {{ color: #23466f; text-decoration: none; }}
.toc-nav a:hover {{ text-decoration: underline; }}
.toc-nav .toc-level-2 {{ margin-left: 0.7em; }}
.toc-nav .toc-level-3 {{ margin-left: 1.4em; font-size: 0.95em; }}
.back-to-top {{
  position: fixed;
  left: 1rem;
  bottom: 1rem;
  z-index: 21;
  text-decoration: none;
  padding: 0.42em 0.62em;
  border-radius: 8px;
  border: 1px solid var(--line-strong);
  background: #fff;
  color: #27496e;
  box-shadow: 0 7px 16px rgba(25, 44, 70, 0.12);
}}
.back-to-top:hover {{
  background: #f7fbff;
  text-decoration: none;
}}
@media (max-width: 1180px) {{
  body {{
    padding: 0.95rem 0.78rem 1.08rem;
    font-size: 16.4px;
  }}
  .content-wrap {{
    width: min(var(--content-max-width), calc(100vw - 1.7rem));
    border-radius: 10px;
    padding: 1.1rem 0.88rem 1.2rem;
    box-shadow: 0 6px 14px rgba(34, 55, 84, 0.07);
  }}
  .toc-panel {{ left: 0.7rem; top: 0.7rem; }}
  .toc-panel[open] {{
    width: min(72vw, 240px);
    max-height: calc(100vh - 4.5rem);
  }}
  .toc-nav {{
    max-height: calc(100vh - 9rem);
  }}
  .back-to-top {{
    left: 0.7rem;
    bottom: 0.7rem;
  }}
}}
"""


class HTMLRenderer:
    """Render EAST to self-contained academic HTML.

    将 EAST 渲染为自包含的学术 HTML。

    Args:
        mode: Output mode — full | body | fragment  (输出模式)
        bib: Bibliography dict key→display string  (参考文献字典)
        locale: Label language zh | en  (标签语言)
        diag: Diagnostic collector  (诊断收集器)
    """

    def __init__(
        self,
        mode: str = "full",
        bib: dict[str, str] | None = None,
        locale: str = "zh",
        diag: DiagCollector | None = None,
    ) -> None:
        self._mode = mode
        self._bib: dict[str, str] = bib or {}
        self._locale = locale
        self._diag = diag

        # Figure / table counters (图表计数器)
        self._fig_count: int = 0
        self._tab_count: int = 0

        # Citation tracking: key → sequential number  (引用编号追踪)
        self._cite_order: dict[str, int] = {}
        self._cite_seq: int = 0

        # Native footnote defs (原生脚注定义)
        self._fn_defs: dict[str, str] = {}

        # Footnote ref sequential numbering (脚注引用序号)
        self._fn_ref_order: dict[str, int] = {}
        self._fn_ref_seq: int = 0

        # Heading index for TOC (标题索引，用于目录)
        self._toc_entries: list[tuple[int, str, str]] = []
        self._heading_slug_counts: dict[str, int] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self, node: Node) -> str:
        """Render a node to HTML string (渲染节点为 HTML 字符串)."""
        if isinstance(node, Document):
            return self._render_document(node)
        return self._dispatch(node)

    # ── Document ──────────────────────────────────────────────────────────────

    def _render_document(self, doc: Document) -> str:
        """Render the full document (渲染完整文档)."""
        # Reset state for each render call (每次渲染重置状态)
        self._fig_count = 0
        self._tab_count = 0
        self._cite_order = {}
        self._cite_seq = 0
        self._fn_defs = {}
        self._fn_ref_order = {}
        self._fn_ref_seq = 0
        self._toc_entries = []
        self._heading_slug_counts = {}

        body = "".join(self._dispatch(child) for child in doc.children)
        doc_header = self._render_doc_header(doc)
        footnotes = self._render_footnotes()

        if self._mode == "fragment":
            return body

        if self._mode == "body":
            return doc_header + body + footnotes

        # Full document mode (全文模式)
        title = str(doc.metadata.get("title", ""))
        title_tag = f"<title>{_esc(title)}</title>" if title else "<title>Document</title>"
        image_max_width = _normalize_css_width(
            doc.metadata.get("html_image_max_width", _DEFAULT_IMAGE_MAX_WIDTH),
            fallback=_DEFAULT_IMAGE_MAX_WIDTH,
        )
        css = _build_css(image_max_width)
        toc_html = self._render_toc()

        # Map locale to HTML lang attribute (本地化映射为 HTML lang 属性)
        lang = "en" if self._locale == "en" else "zh-CN"

        return (
            "<!DOCTYPE html>\n"
            f'<html lang="{lang}">\n'
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"{title_tag}\n"
            f"<style>\n{css}</style>\n"
            f'<link rel="stylesheet" href="{_KATEX_CSS_CDN}">\n'
            "<script>\n"
            "MathJax = { tex: { inlineMath: [['$','$'], ['\\\\(','\\\\)']], "
            "displayMath: [['$$','$$'], ['\\\\[','\\\\]']] }, "
            "options: { skipHtmlTags: ['script','style'] } };\n"
            "</script>\n"
            f'<script src="{_KATEX_JS_CDN}" defer></script>\n'
            f'<script src="{_KATEX_AUTORENDER_CDN}" defer></script>\n'
            f'<script src="{_MATHJAX_CDN}" id="MathJax-script" defer></script>\n'
            "</head>\n"
            "<body>\n"
            '<div id="top"></div>\n'
            f"{toc_html}"
            '<a href="#top" class="back-to-top" aria-label="Back to top">↑ Top</a>\n'
            '<main class="content-wrap">\n'
            f"{doc_header}{body}{footnotes}"
            "</main>\n"
            f"<script>\n{_TOC_INTERACTION_JS}\n</script>\n"
            f"<script>\n{_MATH_RENDER_JS}\n</script>\n"
            "</body>\n"
            "</html>\n"
        )

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, node: Node) -> str:
        """Dispatch node to the appropriate render method (分发节点到对应渲染方法)."""
        handlers = {
            "heading": self._render_heading,
            "paragraph": self._render_paragraph,
            "blockquote": self._render_blockquote,
            "list": self._render_list,
            "list_item": self._render_list_item,
            "code_block": self._render_code_block,
            "figure": self._render_figure,
            "image": self._render_image,
            "table": self._render_table,
            "math_block": self._render_math_block,
            "environment": self._render_environment,
            "raw_block": self._render_raw_block,
            "thematic_break": self._render_thematic_break,
            "text": self._render_text,
            "strong": self._render_strong,
            "emphasis": self._render_emphasis,
            "code_inline": self._render_code_inline,
            "math_inline": self._render_math_inline,
            "link": self._render_link,
            "cross_ref": self._render_cross_ref,
            "citation": self._render_citation,
            "footnote_ref": self._render_footnote_ref,
            "footnote_def": self._render_footnote_def,
            "hardbreak": self._render_hard_break,
            "softbreak": self._render_soft_break,
        }
        handler = handlers.get(node.type)
        if handler:
            return handler(node)
        # Unknown node: warn and render children (未知节点：警告并渲染子节点)
        if self._diag is not None:
            self._diag.warning(f"Unhandled HTML node type '{node.type}' (未处理的 HTML 节点类型)")
        return self._render_children(node)

    def _render_children(self, node: Node) -> str:
        """Render all children and concatenate (渲染所有子节点并拼接)."""
        return "".join(self._dispatch(child) for child in node.children)

    # ── Block nodes ───────────────────────────────────────────────────────────

    def _render_heading(self, node: Node) -> str:
        """Heading → h1-h6 with optional id anchor (标题渲染)."""
        h = cast(Heading, node)
        level = max(1, min(6, h.level))
        heading_text = self._plain_text(node).strip()
        hid = self._resolve_heading_id(node, heading_text)
        id_attr = f' id="{_esc(hid)}"' if hid else ""
        if hid and heading_text and level <= 3:
            self._toc_entries.append((level, heading_text, hid))
        content = self._render_children(node)
        return f"<h{level}{id_attr}>{content}</h{level}>\n"

    def _render_paragraph(self, node: Node) -> str:
        """Paragraph → p tag (段落渲染)."""
        content = self._render_children(node)
        if not content.strip():
            return ""
        return f"<p>{content}</p>\n"

    def _render_blockquote(self, node: Node) -> str:
        """Blockquote → blockquote tag (引用渲染)."""
        content = self._render_children(node)
        return f"<blockquote>\n{content}</blockquote>\n"

    def _render_list(self, node: Node) -> str:
        """List → ul or ol (列表渲染)."""
        lst = cast(List, node)
        tag = "ol" if lst.ordered else "ul"
        content = self._render_children(node)
        return f"<{tag}>\n{content}</{tag}>\n"

    def _render_list_item(self, node: Node) -> str:
        """List item → li (列表项渲染)."""
        content = self._render_children(node)
        return f"<li>{content}</li>\n"

    def _render_code_block(self, node: Node) -> str:
        """Code block → pre/code with language class (代码块渲染)."""
        cb = cast(CodeBlock, node)
        lang_attr = f' class="language-{_esc(cb.language)}"' if cb.language else ""
        escaped = _esc(cb.content)
        return f"<pre><code{lang_attr}>{escaped}</code></pre>\n"

    def _render_figure(self, node: Node) -> str:
        """Figure → figure tag with auto-numbering (图渲染，自动编号)."""
        self._fig_count += 1
        fig = cast(Figure, node)
        meta = node.metadata
        label = str(meta.get("label", ""))
        caption = str(meta.get("caption", ""))
        width = str(meta.get("width", ""))
        ai = meta.get("ai")

        # Determine label prefix for caption (确定标签前缀)
        prefix = "Figure" if self._locale == "en" else "图"
        id_attr = f' id="{_esc(label)}"' if label else ""

        # Build img tag (构建 img 标签)
        safe_width = _normalize_css_width(width, fallback="") if width else ""
        style = f' style="max-width:{_esc(safe_width)}"' if safe_width else ""
        img_tag = f'<img src="{_esc(fig.src)}" alt="{_esc(fig.alt)}"{style} loading="lazy">'

        lines = [f"<figure{id_attr}>", f"  {img_tag}"]

        if caption:
            cap_text = f"{prefix} {self._fig_count}: {self._render_caption_inline(caption)}"
            lines.append(f"  <figcaption>{cap_text}</figcaption>")

        # AI generation info as details fold (AI 生成信息折叠块)
        if isinstance(ai, dict):
            lines.extend(self._render_ai_details(ai))

        lines.append("</figure>")
        return "\n".join(lines) + "\n"

    def _render_image(self, node: Node) -> str:
        """Image → plain img or promoted to figure if it has caption/label.

        有 caption/label 时升级为 figure 环境渲染。
        """
        img = cast(Image, node)
        meta = node.metadata
        if meta.get("caption") or meta.get("label"):
            # Promote: reuse figure rendering logic (升级为 figure 渲染)
            fig_node = Figure(
                src=img.src,
                alt=img.alt,
                children=list(img.children),
                metadata=dict(meta),
            )
            return self._render_figure(fig_node)
        return f'<img src="{_esc(img.src)}" alt="{_esc(img.alt)}" loading="lazy">'

    def _render_table(self, node: Node) -> str:
        """Table → table tag with auto-numbering and caption (表渲染，自动编号)."""
        self._tab_count += 1
        tbl = cast(Table, node)
        meta = node.metadata
        label = str(meta.get("label", ""))
        caption = str(meta.get("caption", ""))
        prefix = "Table" if self._locale == "en" else "表"
        id_attr = f' id="{_esc(label)}"' if label else ""

        lines: list[str] = [f'<div class="table-wrap"{id_attr}>']

        if caption:
            cap_text = f"{prefix} {self._tab_count}: {self._render_caption_inline(caption)}"
            lines.append(f'  <p class="table-caption">{cap_text}</p>')

        lines.append("  <table>")

        # Build alignment style map (构建对齐样式映射)
        def _align_style(col_idx: int) -> str:
            if col_idx < len(tbl.alignments):
                a = tbl.alignments[col_idx]
                if a in ("left", "center", "right"):
                    return f' style="text-align:{a}"'
            return ""

        # Header row (表头行)
        if tbl.headers:
            lines.append("    <tr>")
            for ci, cell_nodes in enumerate(tbl.headers):
                cell_html = "".join(self._dispatch(n) for n in cell_nodes)
                lines.append(f"      <th{_align_style(ci)}>{cell_html}</th>")
            lines.append("    </tr>")

        # Data rows (数据行)
        for row in tbl.rows:
            lines.append("    <tr>")
            for ci, cell_nodes in enumerate(row):
                cell_html = "".join(self._dispatch(n) for n in cell_nodes)
                lines.append(f"      <td{_align_style(ci)}>{cell_html}</td>")
            lines.append("    </tr>")

        lines.append("  </table>")
        lines.append("</div>")
        return "\n".join(lines) + "\n"

    def _render_math_block(self, node: Node) -> str:
        r"""Math block → \[...\] for MathJax, HTML-escaped (块级数学公式，HTML 转义)."""
        mb = cast(MathBlock, node)
        label = str(node.metadata.get("label", ""))
        id_attr = f' id="{_esc(label)}"' if label else ""
        # Escape math content for HTML safety; MathJax reads decoded text (HTML 转义数学内容)
        return f'<div class="math-block"{id_attr}>\n\\[{_esc(mb.content)}\\]\n</div>\n'

    def _render_environment(self, node: Node) -> str:
        """Environment → generic div with class (环境渲染)."""
        env = cast(Environment, node)
        content = self._render_children(node)
        return f'<div class="env-{_esc(env.name)}">\n{content}</div>\n'

    def _render_raw_block(self, node: Node) -> str:
        """Raw block: HTML kind → sanitized; LaTeX → details fold (原始块渲染)."""
        rb = cast(RawBlock, node)
        if rb.kind == "html":
            # Sanitize HTML through allowlist (通过白名单清洗 HTML)
            from wenqiao.sanitize import sanitize_html

            return sanitize_html(rb.content) + "\n"
        if rb.kind == "latex":
            if table_html := self._render_latex_table_raw(rb.content):
                return table_html
        # LaTeX raw block → collapsible fold (LaTeX 块折叠显示)
        escaped = _esc(rb.content)
        return (
            "<details>\n"
            "<summary>Raw LaTeX</summary>\n"
            f'<pre><code class="language-latex">{escaped}</code></pre>\n'
            "</details>\n"
        )

    def _render_thematic_break(self, node: Node) -> str:
        """Thematic break → hr (分割线渲染)."""
        return "<hr>\n"

    # ── Inline nodes ──────────────────────────────────────────────────────────

    def _render_text(self, node: Node) -> str:
        """Text node → HTML-escaped string (文本节点 HTML 转义)."""
        t = cast(Text, node)
        return _esc(t.content)

    def _render_strong(self, node: Node) -> str:
        """Strong → strong tag (加粗渲染)."""
        return f"<strong>{self._render_children(node)}</strong>"

    def _render_emphasis(self, node: Node) -> str:
        """Emphasis → em tag (斜体渲染)."""
        return f"<em>{self._render_children(node)}</em>"

    def _render_code_inline(self, node: Node) -> str:
        """Inline code → code tag (行内代码渲染)."""
        ci = cast(CodeInline, node)
        return f"<code>{_esc(ci.content)}</code>"

    def _render_math_inline(self, node: Node) -> str:
        """Inline math → $...$ for MathJax (行内数学公式渲染)."""
        mi = cast(MathInline, node)
        return f"${_esc(mi.content)}$"

    def _render_link(self, node: Node) -> str:
        """Link → a tag with scheme validation (链接渲染，含 scheme 校验)."""
        lnk = cast(Link, node)
        text = self._render_children(node)
        url = lnk.url
        # Block dangerous schemes (阻止危险 scheme)
        if is_unsafe_url(url):
            return text  # render text only, drop the link (仅渲染文本，丢弃链接)
        return f'<a href="{_esc(url)}">{text}</a>'

    def _render_cross_ref(self, node: Node) -> str:
        """Cross-ref → a tag using display_text (交叉引用渲染)."""
        cr = cast(CrossRef, node)
        # Parser fills display_text, not children (解析器填充 display_text 而非 children)
        text = _esc(cr.display_text) if cr.display_text else _esc(cr.label)
        return f'<a href="#{_esc(cr.label)}">{text}</a>'

    def _render_citation(self, node: Node) -> str:
        """Citation → superscript numbered reference (文献引用渲染)."""
        cit = cast(Citation, node)
        parts: list[str] = []
        for key in cit.keys:
            if key not in self._cite_order:
                self._cite_seq += 1
                self._cite_order[key] = self._cite_seq
            n = self._cite_order[key]
            parts.append(f'<sup><a href="#cite-{_esc(key)}" class="cite">[{n}]</a></sup>')
        return "".join(parts)

    def _render_footnote_ref(self, node: Node) -> str:
        """Footnote ref → superscript sequential number (脚注引用渲染为上标序号)."""
        fr = cast(FootnoteRef, node)
        if fr.ref_id not in self._fn_ref_order:
            self._fn_ref_seq += 1
            self._fn_ref_order[fr.ref_id] = self._fn_ref_seq
        n = self._fn_ref_order[fr.ref_id]
        return f'<sup><a href="#fn-{_esc(fr.ref_id)}">[{n}]</a></sup>'

    def _render_footnote_def(self, node: Node) -> str:
        """Footnote def → collect for end of document (脚注定义收集)."""
        fd = cast(FootnoteDef, node)
        content = self._render_children(node).strip()
        self._fn_defs[fd.def_id] = content
        return ""

    def _render_hard_break(self, node: Node) -> str:
        """Hard break → br tag (硬换行渲染)."""
        return "<br>\n"

    def _render_soft_break(self, node: Node) -> str:
        """Soft break → newline (preserves Markdown line break semantics) (软换行渲染)."""
        return "\n"

    # ── Layout helpers ───────────────────────────────────────────────────────

    def _render_doc_header(self, doc: Document) -> str:
        """Render visible doc metadata header (渲染可见文档元数据头)."""
        title = str(doc.metadata.get("title", "")).strip()
        author = str(doc.metadata.get("author", "")).strip()
        date = str(doc.metadata.get("date", "")).strip()
        abstract = str(doc.metadata.get("abstract", "")).strip()
        if not any((title, author, date, abstract)):
            return ""
        lines = ['<header class="doc-header">']
        if title:
            lines.append(f'  <h1 class="doc-title">{_esc(title)}</h1>')
        if author:
            lines.append(f'  <p class="doc-author">{_esc(author)}</p>')
        if date:
            lines.append(f'  <p class="doc-date">{_esc(date)}</p>')
        if abstract:
            abs_html = _esc(abstract).replace("\n", "<br>")
            lines.append(f'  <p class="doc-abstract"><strong>Abstract.</strong> {abs_html}</p>')
        lines.append("</header>")
        return "\n".join(lines) + "\n"

    def _render_toc(self) -> str:
        """Render left collapsible TOC (渲染左侧可折叠目录)."""
        if not self._toc_entries:
            return ""
        lines = [
            '<details class="toc-panel">',
            "  <summary>目录 / Contents</summary>",
            '  <nav class="toc-nav" aria-label="Table of contents">',
            "    <ul>",
        ]
        for level, text, hid in self._toc_entries:
            lines.append(
                f'      <li class="toc-level-{level}">'
                f'<a href="#{_esc(hid)}">{_esc(text)}</a></li>'
            )
        lines.extend(["    </ul>", "  </nav>", "</details>"])
        return "\n".join(lines) + "\n"

    def _resolve_heading_id(self, node: Node, heading_text: str) -> str:
        """Resolve heading id from metadata or generated slug (从元数据或 slug 生成标题 id)."""
        label = str(node.metadata.get("label", "")).strip()
        if label:
            return label
        base = _slugify_heading(heading_text)
        if not base:
            base = "section"
        count = self._heading_slug_counts.get(base, 0) + 1
        self._heading_slug_counts[base] = count
        if count == 1:
            return base
        return f"{base}-{count}"

    def _plain_text(self, node: Node) -> str:
        """Extract plain text recursively (递归提取纯文本)."""
        if isinstance(node, Text):
            return node.content
        if isinstance(node, CrossRef):
            return node.display_text or node.label
        if isinstance(node, Citation):
            return node.display_text or ",".join(node.keys)
        return "".join(self._plain_text(child) for child in node.children)

    def _render_caption_inline(self, caption: str) -> str:
        """Render caption as inline markdown (图注按行内 Markdown 渲染)."""
        cap = caption.strip()
        if not cap:
            return ""
        try:
            cap_doc = parse(cap)
        except Exception:
            return _esc(caption)
        if not cap_doc.children or any(
            not isinstance(block, Paragraph) for block in cap_doc.children
        ):
            return _esc(caption)
        parts: list[str] = []
        for block in cap_doc.children:
            para = cast(Paragraph, block)
            piece = "".join(self._dispatch(child) for child in para.children).strip()
            if piece:
                parts.append(piece)
        if not parts:
            return _esc(caption)
        return " ".join(parts)

    def _render_latex_table_raw(self, content: str) -> str | None:
        """Convert simple LaTeX table/tabular raw block to HTML table when possible."""
        if r"\begin{table" not in content or r"\begin{tabular" not in content:
            return None

        match = _LATEX_TABULAR_RE.search(content)
        if match is None:
            return None
        tabular_spec = match.group(1)
        tabular_body = match.group(2)

        rows = self._parse_latex_tabular_rows(tabular_body, tabular_spec)
        if not rows:
            return None

        caption = self._extract_latex_braced_value(content, "caption")
        label = self._extract_latex_braced_value(content, "label")
        id_attr = f' id="{_esc(label)}"' if label else ""

        lines: list[str] = [f'<div class="table-wrap"{id_attr}>']
        if caption:
            lines.append(f'  <p class="table-caption">{self._latex_inline_to_html(caption)}</p>')
        lines.append("  <table>")

        headers = rows[0]
        body_rows = rows[1:]

        lines.append("    <thead>")
        lines.append("      <tr>")
        for cell in headers:
            lines.append(f"        <th>{self._latex_inline_to_html(cell)}</th>")
        lines.append("      </tr>")
        lines.append("    </thead>")

        if body_rows:
            lines.append("    <tbody>")
            for row in body_rows:
                lines.append("      <tr>")
                for cell in row:
                    lines.append(f"        <td>{self._latex_inline_to_html(cell)}</td>")
                lines.append("      </tr>")
            lines.append("    </tbody>")

        lines.append("  </table>")
        lines.append("</div>")
        return "\n".join(lines) + "\n"

    def _count_tabular_columns(self, spec: str) -> int:
        """Count expected tabular columns from column spec (统计 tabular 列格式中的列数)."""
        expanded = spec
        # Expand common repeat syntax *{N}{...} (展开常见重复语法)
        for _ in range(6):
            m = re.search(r"\*\{(\d+)\}\{([^{}]+)\}", expanded)
            if m is None:
                break
            n = int(m.group(1))
            repeated = m.group(2) * n
            expanded = expanded[: m.start()] + repeated + expanded[m.end() :]
        # Drop @{} inter-column directives (去掉 @{} 间距指令)
        expanded = re.sub(r"@\{[^}]*\}", "", expanded)
        return len(re.findall(r"[lcrpmbxLCRPMBX]", expanded))

    def _parse_latex_tabular_rows(self, body: str, column_spec: str = "") -> list[list[str]]:
        """Parse basic tabular rows split by \\\\ and & (解析基础 tabular 行列)."""
        expected_cols = self._count_tabular_columns(column_spec)
        cleaned = body.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"(?m)^\s*%.*$", "", cleaned)
        cleaned = cleaned.replace(r"\\hline", r"\\")
        cleaned = cleaned.replace(r"\hline", "\n")
        cleaned = re.sub(r"(?<!\\)\\\\(?:\[[^\]]*\])?", "\n", cleaned)
        # Raw blocks from <!-- begin: raw --> may flatten lines and collapse "\\"
        # between rows to "\"; recover rows on likely first-cell boundaries.
        cleaned = re.sub(r"\\(?=[A-Z0-9\u4e00-\u9fff])", "\n", cleaned)

        rows: list[list[str]] = []
        for chunk in cleaned.splitlines():
            line = re.sub(r"\\+$", "", chunk).strip()
            if not line:
                continue
            cells = [c.strip() for c in line.split("&")]
            if not any(cells):
                continue
            if expected_cols > 0 and len(cells) > expected_cols and len(cells) % expected_cols == 0:
                for i in range(0, len(cells), expected_cols):
                    group = [c.strip() for c in cells[i : i + expected_cols]]
                    if any(group):
                        rows.append(group)
                continue
            rows.append(cells)
        return rows

    def _extract_latex_braced_value(self, content: str, command: str) -> str:
        r"""Extract \command{...} value with brace balancing (提取带平衡括号的命令值)."""
        prefix = f"\\{command}{{"
        start = content.find(prefix)
        if start < 0:
            return ""
        i = start + len(prefix)
        depth = 1
        while i < len(content):
            ch = content[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return content[start + len(prefix) : i].strip()
            i += 1
        return ""

    def _latex_inline_to_html(self, text: str) -> str:
        """Render a minimal subset of LaTeX inline markup to HTML (最小子集 LaTeX 行内转换)."""
        src = text.strip()
        if not src:
            return ""
        # Row flattening may leave a stray "\" before first cell text.
        src = re.sub(r"^\\(?=[A-Z0-9\u4e00-\u9fff])", "", src)

        # Promote \textbf{...} to <strong> while escaping plain text.
        out: list[str] = []
        pos = 0
        for m in re.finditer(r"\\textbf\{([^{}]*)\}", src):
            if m.start() > pos:
                out.append(_esc(src[pos : m.start()]))
            out.append(f"<strong>{_esc(m.group(1))}</strong>")
            pos = m.end()
        if pos < len(src):
            out.append(_esc(src[pos:]))

        rendered = "".join(out)
        rendered = rendered.replace(r"\%", "%").replace(r"\_", "_")
        rendered = rendered.replace(r"\&", "&")
        return rendered

    # ── Footnotes and bibliography ────────────────────────────────────────────

    def _render_footnotes(self) -> str:
        """Render bibliography + footnote definitions at end (渲染文末参考文献和脚注)."""
        if self._mode == "fragment":
            return ""

        parts: list[str] = []

        # Bibliography (参考文献部分)
        if self._cite_order:
            parts.append('<div class="bibliography">\n<h2>References</h2>\n<ol>\n')
            for key, _num in sorted(self._cite_order.items(), key=lambda kv: kv[1]):
                text = _esc(self._bib.get(key, key))
                parts.append(f'  <li id="cite-{_esc(key)}">{text}</li>\n')
            parts.append("</ol>\n</div>\n")

        # Footnotes — sorted by ref encounter order (脚注部分 — 按引用出现顺序排序)
        if self._fn_defs:
            parts.append('<div class="footnotes">\n<hr>\n<ol>\n')
            ordered = sorted(
                self._fn_defs.items(),
                key=lambda kv: self._fn_ref_order.get(kv[0], 999),
            )
            for def_id, content in ordered:
                parts.append(f'  <li id="fn-{_esc(def_id)}">{content}</li>\n')
            parts.append("</ol>\n</div>\n")

        return "".join(parts)

    # ── AI details helper ─────────────────────────────────────────────────────

    def _render_ai_details(self, ai: dict[str, object]) -> list[str]:
        """Render AI generation info as HTML details fold (AI 信息折叠块渲染)."""
        return render_ai_details_html(ai, _esc)
