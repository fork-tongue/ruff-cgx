"""Benchmarks for ruff-cgx performance."""

import tempfile
from pathlib import Path
from textwrap import dedent

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
        def init(self):
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
        def init(self):
            self.state["active"] = False

        def handle_click(self):
            self.state["active"] = not self.state["active"]

        @property
        def active_class(self) -> str:
            return "active" if self.state["active"] else "inactive"
    </script>
    """
).strip()

# Complex CGX with multiple template elements
COMPLEX_CGX = dedent(
    """
    <template>
        <div>
            <header>
                <h1 :text="title" foo="bar"></h1>
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
        def init(self):
            self.title = "My List"
            self.items: List[Dict[str, str]] = []

        def add_item(self):
            self.items.append({"name": "Item", "value": str(len(self.items))})

        def clear_items(self):
            self.items.clear()
    </script>
    """
).strip()

# Very complex CGX with multiline dicts, many directives, and many elements
VERY_COMPLEX_CGX = dedent(
    """
    <template>
        <div :class="container_class" :style="container_style">
            <nav v-if="show_navigation" :config="{'theme': 'dark', 'sticky': True, 'offset': 10}">
                <div>
                    <a v-for="link in nav_links" :href="link.url" :class="link.active_class" @click="handle_nav_click">
                        <span :text="link.label"></span>
                        <span v-if="link.badge" :text="link.badge" class="badge"></span>
                    </a>
                </div>
            </nav>
            <header :style="{'background': header_bg, 'padding': header_padding}">
                <div>
                    <h1 :text="page_title" :id="title_id"></h1>
                    <p v-if="subtitle" :text="subtitle"></p>
                    <div v-if="show_actions">
                        <button @click="handle_refresh" :disabled="is_loading" :class="refresh_btn_class">
                            <span v-if="is_loading">Loading...</span>
                            <span v-else>Refresh</span>
                        </button>
                        <button @click="handle_export" :class="export_btn_class">Export</button>
                    </div>
                </div>
            </header>
            <aside v-if="show_sidebar" :config="{'width': sidebar_width, 'collapsible': True, 'position': 'left'}">
                <div>
                    <h3 :text="sidebar_title"></h3>
                    <ul>
                        <li v-for="item in sidebar_items" :key="item.id" :class="item.class_name">
                            <span :text="item.label"></span>
                            <span v-if="item.count" :text="item.count" class="count"></span>
                        </li>
                    </ul>
                </div>
            </aside>
            <main :style="{'min-height': min_content_height, 'padding': content_padding}">
                <section v-if="error_message">
                    <div class="error" :text="error_message"></div>
                </section>
                <section v-else-if="is_loading">
                    <div class="spinner"></div>
                    <p>Loading data...</p>
                </section>
                <section v-else>
                    <div v-for="section in content_sections" :id="section.id" :class="section.class_name">
                        <h2 :text="section.title"></h2>
                        <p v-if="section.description" :text="section.description"></p>
                        <div v-if="section.items" class="items-grid">
                            <article v-for="item in section.items" :key="item.id" :data-id="item.id" :class="{'featured': item.featured, 'new': item.is_new}" @click="handle_item_click">
                                <div class="item-header">
                                    <h4 :text="item.title"></h4>
                                    <span v-if="item.badge" :text="item.badge" :class="item.badge_class"></span>
                                </div>
                                <div class="item-body">
                                    <p :text="item.description"></p>
                                    <div v-if="item.metadata" class="metadata">
                                        <span v-if="item.metadata.author" :text="item.metadata.author"></span>
                                        <span v-if="item.metadata.date" :text="item.metadata.date"></span>
                                        <span v-if="item.metadata.category" :text="item.metadata.category"></span>
                                    </div>
                                </div>
                                <div class="item-footer">
                                    <button @click="handle_view" :data-id="item.id">View</button>
                                    <button v-if="item.can_edit" @click="handle_edit" :data-id="item.id">Edit</button>
                                    <button v-if="item.can_delete" @click="handle_delete" :data-id="item.id" class="danger">Delete</button>
                                </div>
                            </article>
                        </div>
                    </div>
                </section>
            </main>
            <footer :style="{'background': footer_bg, 'padding': footer_padding, 'margin-top': footer_margin}">
                <div>
                    <div class="footer-links">
                        <a v-for="link in footer_links" :href="link.url" :text="link.label" @click="handle_footer_click"></a>
                    </div>
                    <div class="footer-info">
                        <p :text="copyright_text"></p>
                        <p v-if="version_info" :text="version_info"></p>
                    </div>
                </div>
            </footer>
        </div>
    </template>

    <script>
    from typing import List, Dict, Any, Optional
    from collagraph import Component

    class DashboardComponent(Component):
        def init(self):
            self.show_navigation = True
            self.show_sidebar = True
            self.show_actions = True
            self.is_loading = False
            self.error_message: Optional[str] = None
            self.page_title = "Dashboard"
            self.subtitle = "Welcome to your dashboard"
            self.nav_links: List[Dict[str, Any]] = []
            self.sidebar_items: List[Dict[str, Any]] = []
            self.content_sections: List[Dict[str, Any]] = []
            self.footer_links: List[Dict[str, str]] = []

        @property
        def container_class(self) -> str:
            return "container" if not self.is_loading else "container loading"

        @property
        def container_style(self) -> Dict[str, str]:
            return {"max-width": "1200px", "margin": "0 auto"}

        @property
        def header_bg(self) -> str:
            return "#f5f5f5"

        @property
        def header_padding(self) -> str:
            return "20px"

        @property
        def sidebar_width(self) -> str:
            return "250px"

        @property
        def sidebar_title(self) -> str:
            return "Filters"

        @property
        def min_content_height(self) -> str:
            return "600px"

        @property
        def content_padding(self) -> str:
            return "20px"

        @property
        def footer_bg(self) -> str:
            return "#333"

        @property
        def footer_padding(self) -> str:
            return "20px"

        @property
        def footer_margin(self) -> str:
            return "40px"

        @property
        def copyright_text(self) -> str:
            return "© 2025 My Company"

        @property
        def version_info(self) -> str:
            return "Version 1.0.0"

        @property
        def title_id(self) -> str:
            return "page-title"

        @property
        def refresh_btn_class(self) -> str:
            return "btn btn-primary" if not self.is_loading else "btn btn-primary disabled"

        @property
        def export_btn_class(self) -> str:
            return "btn btn-secondary"

        def handle_nav_click(self):
            pass

        def handle_refresh(self):
            self.is_loading = True

        def handle_export(self):
            pass

        def handle_item_click(self):
            pass

        def handle_view(self):
            pass

        def handle_edit(self):
            pass

        def handle_delete(self):
            pass

        def handle_footer_click(self):
            pass
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

    def test_format_very_complex_cgx(self, benchmark):
        """Benchmark formatting a very complex CGX file with many elements and directives."""
        result = benchmark(format_cgx_content, VERY_COMPLEX_CGX)
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

    def test_lint_very_complex_cgx(self, benchmark):
        """Benchmark linting a very complex CGX file with many elements and directives."""
        result = benchmark(lint_cgx_content, VERY_COMPLEX_CGX)
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

        def teardown(path, fix):  # noqa: ARG001
            # Clean up temp file
            try:
                path.unlink()
            except Exception:
                pass

        result = benchmark.pedantic(
            lint_file, setup=setup, teardown=teardown, rounds=20, iterations=1
        )
        # lint_file returns a dict with diagnostics and metadata
        assert isinstance(result, dict)
        assert "diagnostics" in result
