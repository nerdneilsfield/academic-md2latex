from md_mid.diagnostic import DiagLevel, Diagnostic, Position


def test_create_warning():
    pos = Position(line=42, column=1)
    d = Diagnostic(DiagLevel.WARNING, "Unknown directive 'color'", "paper.mid.md", pos)
    assert d.level == DiagLevel.WARNING
    assert d.message == "Unknown directive 'color'"
    assert d.file == "paper.mid.md"
    assert d.position.line == 42


def test_format_warning():
    pos = Position(line=42, column=1)
    d = Diagnostic(DiagLevel.WARNING, "Unknown directive 'color'", "paper.mid.md", pos)
    assert str(d) == "[WARNING] paper.mid.md:42 - Unknown directive 'color'"


def test_format_error_no_position():
    d = Diagnostic(DiagLevel.ERROR, "File not found", "missing.md")
    assert str(d) == "[ERROR] missing.md - File not found"


def test_collector():
    from md_mid.diagnostic import DiagCollector

    dc = DiagCollector("test.md")
    dc.warning("bad thing", Position(line=1, column=1))
    dc.error("worse thing", Position(line=2, column=1))
    dc.info("fyi", Position(line=3, column=1))
    assert len(dc.diagnostics) == 3
    assert dc.has_errors is True
    assert len(dc.errors) == 1
    assert len(dc.warnings) == 1


def test_diag_phase_timing():
    """phase() context manager records wall-clock timing (phase 上下文管理器记录计时)."""
    from md_mid.diagnostic import DiagCollector

    dc = DiagCollector("test.md")
    with dc.phase("parse"):
        pass  # Near-zero work (几乎无工作量)
    assert "parse" in dc.timings
    assert dc.timings["parse"] >= 0.0
