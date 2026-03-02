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
