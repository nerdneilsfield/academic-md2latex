from wenqiao.escape import escape_latex, escape_latex_with_protection


class TestEscapeLaTeX:
    def test_no_special_chars(self):
        assert escape_latex("hello world") == "hello world"

    def test_hash(self):
        assert escape_latex("Section #1") == r"Section \#1"

    def test_percent(self):
        assert escape_latex("100%") == r"100\%"

    def test_ampersand(self):
        assert escape_latex("A & B") == r"A \& B"

    def test_underscore(self):
        assert escape_latex("my_var") == r"my\_var"

    def test_braces(self):
        assert escape_latex("{x}") == r"\{x\}"

    def test_tilde(self):
        assert escape_latex("~") == r"\textasciitilde{}"

    def test_caret(self):
        assert escape_latex("^") == r"\textasciicircum{}"

    def test_backslash(self):
        assert escape_latex("\\") == r"\textbackslash{}"

    def test_dollar(self):
        assert escape_latex("$10") == r"\$10"

    def test_multiple_specials(self):
        assert escape_latex("a & b # c") == r"a \& b \# c"

    def test_chinese_text_untouched(self):
        assert escape_latex("这是中文") == "这是中文"


class TestEscapeWithProtection:
    def test_protect_cite(self):
        result = escape_latex_with_protection(r"\cite{wang2024}")
        assert result == r"\cite{wang2024}"

    def test_protect_ref(self):
        result = escape_latex_with_protection(r"\ref{fig:x}")
        assert result == r"\ref{fig:x}"

    def test_protect_href(self):
        result = escape_latex_with_protection(r"\href{http://x.com}{link}")
        assert result == r"\href{http://x.com}{link}"

    def test_mixed_text_and_command(self):
        result = escape_latex_with_protection(r"see \cite{w2024} for 100% details")
        assert result == r"see \cite{w2024} for 100\% details"

    def test_command_with_options(self):
        result = escape_latex_with_protection(r"\usepackage[utf8]{inputenc}")
        assert result == r"\usepackage[utf8]{inputenc}"

    def test_textbf(self):
        result = escape_latex_with_protection(r"\textbf{bold}")
        assert result == r"\textbf{bold}"
