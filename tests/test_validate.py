"""validate 子命令和 EAST walker 的测试。

Tests for the validate subcommand and EAST walker (collect_east_info).
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from wenqiao.cli import cli as main
from wenqiao.diagnostic import DiagCollector
from wenqiao.nodes import (
    Citation,
    CrossRef,
    Document,
    Figure,
    Image,
    Paragraph,
    Table,
    Text,
)
from wenqiao.validate import (
    ValidationInfo,
    collect_east_info,
    validate_bib,
    validate_crossrefs,
    validate_images,
)

# ── Walker unit tests (Walker 单元测试) ──────────────────────────────────────


def test_collect_citations() -> None:
    """Citation nodes → cite_keys set (Citation 节点 → cite_keys 集合)."""
    doc = Document(
        children=[
            Paragraph(
                children=[
                    Citation(keys=["wang2024", "li2023"]),
                    Citation(keys=["wang2024"]),  # duplicate (重复)
                ]
            ),
        ]
    )
    info = collect_east_info(doc)
    assert info.cite_keys == {"wang2024", "li2023"}


def test_collect_labels() -> None:
    """metadata["label"] → labels set (元数据标签 → labels 集合)."""
    fig = Figure(src="img.png", metadata={"label": "fig:arch"})
    doc = Document(children=[fig])
    info = collect_east_info(doc)
    assert "fig:arch" in info.labels


def test_collect_crossrefs() -> None:
    """CrossRef nodes → crossref_labels set (CrossRef 节点 → crossref_labels 集合)."""
    doc = Document(
        children=[
            Paragraph(
                children=[
                    CrossRef(label="fig:arch"),
                    CrossRef(label="tab:results"),
                ]
            ),
        ]
    )
    info = collect_east_info(doc)
    assert info.crossref_labels == {"fig:arch", "tab:results"}


def test_collect_images() -> None:
    """Figure/Image → image_srcs list (Figure/Image → image_srcs 列表)."""
    doc = Document(
        children=[
            Figure(src="fig1.png"),
            Paragraph(children=[Image(src="inline.jpg")]),
        ]
    )
    info = collect_east_info(doc)
    assert "fig1.png" in info.image_srcs
    assert "inline.jpg" in info.image_srcs


def test_collect_table_cells() -> None:
    """Citations/refs inside Table cells are found (表格单元格内的引用/交叉引用可被找到)."""
    table = Table(
        headers=[[Text(content="Col1")], [Citation(keys=["key1"])]],
        rows=[
            [[CrossRef(label="fig:x")], [Text(content="data")]],
        ],
    )
    doc = Document(children=[table])
    info = collect_east_info(doc)
    assert "key1" in info.cite_keys
    assert "fig:x" in info.crossref_labels


# ── Validator unit tests (验证器单元测试) ─────────────────────────────────────


def test_validate_bib_missing_key() -> None:
    """Missing cite key produces warning (缺失引用键产生警告)."""
    info = ValidationInfo(cite_keys={"wang2024", "missing_key"})
    bib = {"wang2024": "Wang. Some paper. 2024."}
    diag = DiagCollector("test")
    validate_bib(info, bib, diag)
    assert len(diag.warnings) == 1
    assert "missing_key" in diag.warnings[0].message


def test_validate_crossrefs_dangling() -> None:
    """CrossRef with no label produces warning (无标签的交叉引用产生警告)."""
    info = ValidationInfo(
        crossref_labels={"fig:arch", "tab:missing"},
        labels={"fig:arch"},
    )
    diag = DiagCollector("test")
    validate_crossrefs(info, diag)
    assert len(diag.warnings) == 1
    assert "tab:missing" in diag.warnings[0].message


def test_validate_images_missing_file(tmp_path: Path) -> None:
    """Missing image file produces warning (缺失图片文件产生警告)."""
    # Create one file, leave another missing (创建一个文件，另一个缺失)
    (tmp_path / "exists.png").write_bytes(b"fake png")
    info = ValidationInfo(image_srcs=["exists.png", "missing.png"])
    diag = DiagCollector("test")
    validate_images(info, tmp_path, diag)
    assert len(diag.warnings) == 1
    assert "missing.png" in diag.warnings[0].message


def test_validate_images_skips_urls() -> None:
    """URL images are skipped (URL 图片被跳过)."""
    info = ValidationInfo(image_srcs=["https://example.com/img.png"])
    diag = DiagCollector("test")
    validate_images(info, Path("."), diag)
    assert len(diag.warnings) == 0


# ── CLI integration tests (CLI 集成测试) ─────────────────────────────────────


def test_validate_clean_file(tmp_path: Path) -> None:
    """Clean file exits 0 (干净文件退出码 0)."""
    src = tmp_path / "clean.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    result = CliRunner().invoke(main, ["validate", str(src)])
    assert result.exit_code == 0


def test_validate_unmatched_begin(tmp_path: Path) -> None:
    """Unmatched begin exits 1 (未匹配的 begin 退出码 1)."""
    src = tmp_path / "bad.mid.md"
    src.write_text("<!-- begin: figure -->\nContent\n")
    result = CliRunner().invoke(main, ["validate", str(src)])
    assert result.exit_code == 1


def test_validate_missing_cite_in_bib(tmp_path: Path) -> None:
    """Missing cite key in bib produces warning (bib 中缺失引用键产生警告)."""
    src = tmp_path / "cite.mid.md"
    src.write_text("[Author](cite:missing_key) says hello.\n")
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{other, author={X}, title={Y}, year={2024}}\n")
    result = CliRunner().invoke(main, ["validate", str(src), "--bib", str(bib)])
    # Should warn about missing_key (应警告 missing_key)
    assert "missing_key" in (result.output + (result.stderr_bytes or b"").decode())


def test_validate_crossref_no_label(tmp_path: Path) -> None:
    """Dangling cross-ref produces warning (悬空交叉引用产生警告)."""
    src = tmp_path / "ref.mid.md"
    src.write_text("See [Figure 1](ref:fig:nonexistent).\n")
    result = CliRunner().invoke(main, ["validate", str(src), "--verbose"])
    combined = result.output + (result.stderr_bytes or b"").decode()
    assert "fig:nonexistent" in combined


def test_validate_missing_image(tmp_path: Path) -> None:
    """Missing image file produces warning (缺失图片文件产生警告)."""
    src = tmp_path / "img.mid.md"
    src.write_text("![alt](nonexistent.png)\n")
    result = CliRunner().invoke(main, ["validate", str(src), "--verbose"])
    combined = result.output + (result.stderr_bytes or b"").decode()
    assert "nonexistent.png" in combined


def test_validate_strict_mode(tmp_path: Path) -> None:
    """--strict exits 1 on warnings (--strict 有警告时退出码 1)."""
    src = tmp_path / "ref.mid.md"
    src.write_text("See [Figure 1](ref:fig:nonexistent).\n")
    result = CliRunner().invoke(main, ["validate", str(src), "--strict"])
    assert result.exit_code == 1


def test_validate_bib_from_directive(tmp_path: Path) -> None:
    """Picks up bibliography from <!-- bibliography: ... --> directive.

    从 <!-- bibliography: ... --> 指令获取参考文献文件。
    """
    bib = tmp_path / "auto.bib"
    bib.write_text("@article{found, author={A}, title={B}, year={2024}}\n")
    src = tmp_path / "doc.mid.md"
    src.write_text("<!-- bibliography: auto.bib -->\n\n[A](cite:found) and [B](cite:not_in_bib).\n")
    result = CliRunner().invoke(main, ["validate", str(src), "--verbose"])
    combined = result.output + (result.stderr_bytes or b"").decode()
    # Should warn about not_in_bib, not about found (应警告 not_in_bib，不警告 found)
    assert "not_in_bib" in combined
