from click.testing import CliRunner
from md_mid.cli import main


def test_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "md-mid" in result.output or "input" in result.output.lower()


def test_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_convert_minimal(tmp_path):
    src = tmp_path / "test.mid.md"
    src.write_text("# Hello\n\nWorld.\n")
    out = tmp_path / "test.tex"
    result = CliRunner().invoke(main, [str(src), "-o", str(out)])
    assert result.exit_code == 0
    content = out.read_text()
    assert "\\section{Hello}" in content
    assert "World." in content
