"""Benchmarks for ruff-cgx performance."""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from ruff_cgx import format_cgx_content, lint_cgx_content
from ruff_cgx.linter import lint_file

# Sample CGX content for benchmarking
SIMPLE_CGX = dedent(
    """
    <template>
        <div>
            <label :text="message"></label>
        </div>
    </template>

    <script>
    from collagraph import Component

    class MyComponent(Component):
        def __init__(self):
            self.message = "Hello World"
    </script>
    """
).strip()

# CGX with unsorted imports (tests both linting and import sorting)
UNSORTED_IMPORTS_CGX = dedent(
    """
    <template>
        <div :class="active_class">
            <button @click="handle_click">Click me</button>
        </div>
    </template>

    <script>
    from typing import Dict
    from collagraph import Component
    import sys
    import os


    class ButtonComponent(Component):
        def __init__(self):
            self.active = False

        def handle_click(self):
            self.active = not self.active

        @property
        def active_class(self) -> str:
            return "active" if self.active else "inactive"
    </script>
    """
).strip()

# Complex CGX with multiple template elements
COMPLEX_CGX = dedent(
    """
    <template>
        <div>
            <header>
                <h1 :text="title"></h1>
            </header>
            <main>
                <div v-for="item in items">
                    <span :text="item.name"></span>
                    <span :text="item.value"></span>
                </div>
            </main>
            <footer>
                <button @click="add_item">Add</button>
                <button @click="clear_items">Clear</button>
            </footer>
        </div>
    </template>

    <script>
    from typing import List, Dict
    from collagraph import Component


    class ListComponent(Component):
        def __init__(self):
            self.title = "My List"
            self.items: List[Dict[str, str]] = []

        def add_item(self):
            self.items.append({"name": "Item", "value": str(len(self.items))})

        def clear_items(self):
            self.items.clear()
    </script>
    """
).strip()


class TestFormatBenchmarks:
    """Benchmarks for format operations."""

    def test_format_simple_cgx(self, benchmark):
        """Benchmark formatting a simple CGX file."""
        result = benchmark(format_cgx_content, SIMPLE_CGX)
        assert result is not None

    def test_format_unsorted_imports(self, benchmark):
        """Benchmark formatting CGX with unsorted imports."""
        result = benchmark(format_cgx_content, UNSORTED_IMPORTS_CGX)
        assert result is not None

    def test_format_complex_cgx(self, benchmark):
        """Benchmark formatting a complex CGX file."""
        result = benchmark(format_cgx_content, COMPLEX_CGX)
        assert result is not None


class TestLintBenchmarks:
    """Benchmarks for lint operations."""

    def test_lint_simple_cgx(self, benchmark):
        """Benchmark linting a simple CGX file."""
        result = benchmark(lint_cgx_content, SIMPLE_CGX)
        assert isinstance(result, list)

    def test_lint_unsorted_imports(self, benchmark):
        """Benchmark linting CGX with unsorted imports."""
        result = benchmark(lint_cgx_content, UNSORTED_IMPORTS_CGX)
        assert isinstance(result, list)

    def test_lint_complex_cgx(self, benchmark):
        """Benchmark linting a complex CGX file."""
        result = benchmark(lint_cgx_content, COMPLEX_CGX)
        assert isinstance(result, list)


class TestLintFileBenchmarks:
    """Benchmarks for lint file operations with fix."""

    def test_lint_file_with_fix_cli(self, benchmark):
        """Benchmark linting and fixing a file (CLI usage with full output)."""

        def setup():
            # Create temp file
            f = tempfile.NamedTemporaryFile(
                mode="w", suffix=".cgx", delete=False, encoding="utf-8"
            )
            f.write(UNSORTED_IMPORTS_CGX)
            f.close()
            return (Path(f.name),), {"fix": True}

        def teardown(path, fix):
            # Clean up temp file
            try:
                path.unlink()
            except Exception:
                pass

        result = benchmark.pedantic(
            lint_file, setup=setup, teardown=teardown, rounds=20, iterations=1
        )
        # lint_file returns exit code
        assert result in (0, 1)
