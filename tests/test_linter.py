"""Tests for linting and diagnostics."""

import tempfile
from pathlib import Path
from textwrap import dedent

from ruff_cgx import lint_cgx_content, lint_file


def test_lint_valid_code():
    """Test linting valid Python code in a CGX file."""
    content = dedent(
        """
        <template>
            <label :text="message"></label>
        </template>

        <script>
        from collagraph import Component


        class Label(Component):
            pass
        </script>
        """
    ).strip()
    diagnostics = lint_cgx_content(content)

    assert len(diagnostics) == 0, diagnostics


def test_lint_invalid_code():
    """Test linting invalid Python code in a CGX file."""
    content = dedent(
        """
        <template>
            <node :text="message"></node>
        </template>

        <script>
        from collagraph import Component


        class Node(Component):
            def init(self):
                self.message = undefined_variable</script>
        """
    ).strip()
    diagnostics = lint_cgx_content(content)

    # Should have 1 syntax error diagnostics:
    # Undefined variable
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "F821", diagnostic.code
    assert "Undefined name `undefined_variable`" in diagnostic.message, (
        diagnostic.message
    )
    assert diagnostic.line == 10
    assert diagnostic.column == 23


def test_lint_empty_file():
    """Test linting an empty CGX file."""
    diagnostics = lint_cgx_content("")

    # Should return empty list
    assert len(diagnostics) == 0, diagnostics


def test_lint_unused_import():
    content = dedent(
        """
        <template>
          <widget>
            <!-- v-bind props -->
            <label
              v-bind:text="props['text']"
            />
            <!-- v-bind state + shortcut -->
            <label
              :text="state['other_text']"
            />
            <!-- v-bind state + component method -->
            <label
              :text="counter_format()"
            />
            <!-- v-bind state + component attribute -->
            <label
              :text="title"
            />
            <!-- v-bind context -->
            <label
              v-bind:text="cg.__version__"
            />
            <!-- v-if -->
            <label
              v-if="state['counter'] == 0"
              text="if"
            />
            <!-- v-else-if -->
            <label
              v-else-if="state['counter'] == 1"
              text="else-if"
            />
            <!-- v-else-if -->
            <label
              v-else-if="state['counter'] == 2"
              text="second else-if"
            />
            <!-- v-else -->
            <label
              v-else
              text="else"
            />
            <!-- v-for enumeration-->
            <label
              v-for="animal in state['animals']"
              v-bind:text="animal"
            />
            <!-- v-for enumeration-->
            <label
              v-for="idx, animal in enumerate(state['animals'])"
              v-bind:key="idx"
              v-bind:text="animal"
            />
            <widget :layout="{
                'type': 'box',
                'direction': QBoxLayout.Direction.LeftToRight}
            ">
              <!-- v-on -->
              <button
                v-on:clicked="bump"
                text="Bump"
              />
              <!-- v-on shortcut -->
              <button
                @clicked="add"
                text="Add"
              />
            </widget>
          </widget>
        </template>


        <script lang="python">
        import collagraph as cg
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QBoxLayout


        class Directives(cg.Component):
            def init(self):
                self.state["other_text"] = "Other"
                self.state["counter"] = 0
                self.state["animals"] = []
                self.title = "Title"

            def bump(self):
                self.state["counter"] += 1

            def add(self):
                for x in ["Aardvark", "Addax", "Adelie Penguin", "African Buffalo"]:
                    if x not in self.state["animals"]:
                        self.state["animals"].append(x)
                        break

            def counter_format(self):
                return f"Counter: {self.state['counter']}"
        </script>
        """
    )

    diagnostics = lint_cgx_content(content)

    # Should find 1 unused imports: QAction
    # Should not find error about QBoxLayout since it is used in the template
    assert len(diagnostics) == 1, diagnostics
    diagnostic = diagnostics[0]
    assert diagnostic.code == "F401"
    assert "QAction" in diagnostic.message


def test_lint_file_with_fix():
    """Test that lint_file with fix=True applies auto-fixable issues."""
    content = dedent(
        """
        <template>
            <label :text="message"></label>
        </template>

        <script>
        from collagraph import Component
        import sys


        class Label(Component):
            pass
        </script>
        """
    ).strip()

    # Create a temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".cgx", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        # First check that we have fixable issues (unsorted imports)
        diagnostics = lint_cgx_content(content)
        assert len(diagnostics) == 2, diagnostics
        assert [diag.code for diag in diagnostics] == ["I001", "F401"]
        # Check that we have the I001 import sorting diagnostic
        i001_diags = [d for d in diagnostics if d.code == "I001"]
        assert len(i001_diags) == 1, f"Expected I001 diagnostic, got: {diagnostics}"

        # Run lint_file with fix=True
        lint_file(temp_path, fix=True)

        # Read the file back
        fixed_content = temp_path.read_text(encoding="utf-8")

        # The imports should now be sorted (import before from)
        script_section = fixed_content.split("<script>")[1].split("</script>")[0]
        import_sys_pos = script_section.find("import sys")
        from_collagraph_pos = script_section.find("from collagraph")

        assert import_sys_pos < from_collagraph_pos, (
            "Expected imports to be sorted (import before from), "
            f"but got:\n{script_section}"
        )

        # Both imports should still be there
        assert "import sys" in fixed_content
        assert "from collagraph import Component" in fixed_content
        assert '<label :text="message"></label>' in fixed_content

        # Verify the I001 diagnostic is gone
        diagnostics_after = lint_cgx_content(fixed_content)
        i001_after = [d for d in diagnostics_after if d.code == "I001"]
        assert len(i001_after) == 0, (
            f"Expected I001 to be fixed, but still present: {i001_after}"
        )
    finally:
        # Clean up
        temp_path.unlink()
