"""Tests for the RuffLinter API."""

from textwrap import dedent

import pytest

from ruff_cgx import RuffLinter


@pytest.fixture
def linter():
    """Create a linter instance."""
    return RuffLinter()


def test_linter_initialization(linter):
    """Test that the linter initializes correctly."""
    assert linter is not None
    # Note: ruff_available may be False if ruff isn't installed
    if not linter.ruff_available:
        pytest.xfail("Ruff should be available to run the test suite")


def test_lint_valid_code(linter):
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
    )
    diagnostics = linter.lint_cgx_file(content)

    assert len(diagnostics) == 0
    # May have style warnings, but no syntax errors
    assert all(
        d.severity != "error" or "unavailable" in d.code.lower() for d in diagnostics
    ), diagnostics


def test_lint_invalid_code(linter):
    """Test linting invalid Python code in a CGX file."""
    content = dedent(
        """
        <template>
            <node :text="message"></node>
        </template>

        <script>
        from collagraph import Component


        class Node(Component):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.message = undefined_variable
        </script>
        """.lstrip("\n")
    )
    diagnostics = linter.lint_cgx_file(content)

    # Should have 2 syntax error diagnostics:
    # 2. Expected an expression (incomplete statement)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "F821", diagnostic.code
    assert "Undefined name `undefined_variable`" in diagnostic.message, (
        diagnostic.message
    )
    assert diagnostic.line == 11
    assert diagnostic.column == 23


def test_lint_empty_file(linter):
    """Test linting an empty CGX file."""
    diagnostics = linter.lint_cgx_file("")

    # Should return empty list or just ruff availability warning
    assert isinstance(diagnostics, list)


def test_lint_unused_import(linter):
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
            def __init__(self, props):
                super().__init__(props)
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

    diagnostics = linter.lint_cgx_file(content)

    # Should find 1 unused imports: QAction
    # Should not find error about QBoxLayout since it is used in the template
    assert len(diagnostics) == 1, diagnostics
    diagnostic = diagnostics[0]
    assert diagnostic.code == "F401"
    assert "QAction" in diagnostic.message
