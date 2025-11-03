"""Tests for handling Python code on the same line as <script> tag."""

from ruff_cgx import format_cgx_content, lint_cgx_content


def test_lint_inline_script():
    """Test linting when Python code is on the same line as <script> tag."""
    content = """<script>from pprint import pprint
import collagraph
unused_variable = 123
</script>
"""
    diagnostics = lint_cgx_content(content)

    # Should detect both unused imports on correct lines
    assert len(diagnostics) >= 2
    codes = [d.code for d in diagnostics]
    assert "F401" in codes  # Unused import

    # Check line numbers are correct (0-indexed)
    pprint_diag = next(d for d in diagnostics if "pprint" in d.message)
    assert pprint_diag.line == 0  # First line (0-indexed)

    collagraph_diag = next(d for d in diagnostics if "collagraph" in d.message)
    assert collagraph_diag.line == 1  # Second line (0-indexed)


def test_format_inline_script():
    """Test formatting when Python code is on the same line as <script> tag."""
    content = """<script>from pprint import pprint
import collagraph
unused_variable = 123
</script>
"""
    formatted = format_cgx_content(content)

    # Should move Python to its own line after <script>
    assert formatted.startswith("<script>\nfrom pprint")

    # Should still format the Python code correctly
    assert "from pprint import pprint" in formatted
    assert "import collagraph" in formatted
    assert "unused_variable = 123" in formatted


def test_format_inline_script_normalizes_to_newline():
    """Test that formatting normalizes inline Python to start on a new line."""
    content = """<script>from pprint import pprint
import collagraph
</script>
"""
    formatted = format_cgx_content(content)

    lines = formatted.split("\n")
    # First line should be just the script tag
    assert lines[0] == "<script>"
    # Second line should be the first import
    assert "from pprint import pprint" in lines[1]


def test_lint_with_newline_after_script():
    """Test linting when Python is already on a new line after <script>."""
    content = """<script>
from pprint import pprint
import collagraph
unused_variable = 123
</script>
"""
    diagnostics = lint_cgx_content(content)

    # Should detect unused imports
    assert len(diagnostics) >= 2
    codes = [d.code for d in diagnostics]
    assert "F401" in codes

    # Check line numbers are correct (0-indexed, line 1 is first Python line)
    pprint_diag = next(d for d in diagnostics if "pprint" in d.message)
    assert pprint_diag.line == 1  # Second line (0-indexed)

    collagraph_diag = next(d for d in diagnostics if "collagraph" in d.message)
    assert collagraph_diag.line == 2  # Third line (0-indexed)


def test_format_with_newline_after_script():
    """Test formatting when Python is already on a new line after <script>."""
    content = """<script>
from pprint import pprint
import collagraph
unused_variable = 123
</script>
"""
    formatted = format_cgx_content(content)

    # Should keep Python on new line
    assert formatted.startswith("<script>\nfrom pprint")

    # Should format the Python code correctly
    assert "from pprint import pprint" in formatted
    assert "import collagraph" in formatted
    assert "unused_variable = 123" in formatted
