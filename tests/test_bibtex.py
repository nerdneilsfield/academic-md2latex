from md_mid.bibtex import parse_bib

BIB_CONTENT = r"""
@article{wang2024,
  author = {Wang, Alice and Li, Bob},
  title  = {Point Cloud Registration via 4PCS},
  journal = {CVPR},
  year   = {2024},
}

@inproceedings{fischler1981,
  author = {Fischler, M. A. and Bolles, R. C.},
  title  = {Random Sample Consensus},
  booktitle = {CACM},
  year   = {1981},
}

@book{goossens1993,
  author = {Goossens, Michel},
  title  = {The LaTeX Companion},
  year   = {1993},
}
"""


def test_parse_returns_dict():
    result = parse_bib(BIB_CONTENT)
    assert isinstance(result, dict)
    assert "wang2024" in result
    assert "fischler1981" in result


def test_parse_article_formatted():
    result = parse_bib(BIB_CONTENT)
    entry = result["wang2024"]
    assert "Wang" in entry
    assert "2024" in entry
    assert "Point Cloud Registration" in entry


def test_parse_inproceedings():
    result = parse_bib(BIB_CONTENT)
    entry = result["fischler1981"]
    assert "Fischler" in entry
    assert "1981" in entry


def test_missing_key_not_in_result():
    result = parse_bib(BIB_CONTENT)
    assert "nonexistent" not in result


def test_empty_bib_returns_empty_dict():
    assert parse_bib("") == {}
    assert parse_bib("  ") == {}


# --- H2 + M1 bug-fix tests (H2 + M1 缺陷修复测试) ---


def test_hyphenated_key_parsed() -> None:
    """连字符键能被解析 (Hyphenated key like wang-2024 is parsed)."""
    bib = "@article{wang-2024, author={Wang}, title={T}, year={2024}}"
    assert "wang-2024" in parse_bib(bib)


def test_colon_key_parsed() -> None:
    """冒号键能被解析 (Colon key like doi:10.1234 is parsed)."""
    bib = "@article{doi:10.1234/test, author={S}, title={T}, year={2024}}"
    assert "doi:10.1234/test" in parse_bib(bib)


def test_at_in_field_value() -> None:
    """字段含 @ 不截断 (Field with @ like email is fully parsed)."""
    bib = "@article{t, author={S}, note={x@y.com}, year={2024}}\n"
    result = parse_bib(bib)
    assert "t" in result and "2024" in result["t"]


def test_multiple_entries_with_at() -> None:
    """多条目含 @ 全部解析 (Multiple entries with @ in fields all parsed)."""
    bib = (
        "@article{a, author={A}, note={x@y}, year={2024}}\n"
        "@article{b, author={B}, title={T}, year={2024}}\n"
    )
    result = parse_bib(bib)
    assert "a" in result and "b" in result


def test_no_double_period_et_al() -> None:
    """多作者无双句号 (Multi-author has no 'et al..' double period)."""
    bib = "@article{t, author={S and J}, title={T}, year={2024}}"
    assert ".." not in parse_bib(bib)["t"]
