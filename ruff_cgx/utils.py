"""Shared utilities for ruff-cgx linting and formatting."""

import ast
import os
import subprocess
import tempfile
import textwrap
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from collagraph.sfc.compiler import construct_ast
from collagraph.sfc.parser import CGXParser, Element

# Module-level configuration for ruff command
_ruff_command: Optional[str] = None


def set_ruff_command(command: str) -> None:
    """
    Set the ruff command to use programmatically.

    This is the recommended way for LSP servers and other Python code
    to configure the ruff executable.

    Args:
        command: Path or command name for ruff executable (e.g., "/usr/local/bin/ruff")

    Example:
        >>> import ruff_cgx
        >>> ruff_cgx.set_ruff_command("/path/to/custom/ruff")
        >>> ruff_cgx.format_file("file.cgx")
    """
    global _ruff_command
    _ruff_command = command


def get_ruff_command() -> str:
    """
    Get the ruff command to use.

    Priority order:
    1. Command set via set_ruff_command() (programmatic)
    2. RUFF_COMMAND environment variable (for CLI use)
    3. Default: "ruff"

    Returns:
        Path or command name for ruff executable
    """
    if _ruff_command is not None:
        return _ruff_command
    return os.environ.get("RUFF_COMMAND", "ruff")


def reset_ruff_command() -> None:
    """
    Reset the ruff command to default (uses priority: env var, then "ruff").

    Clears any command set via set_ruff_command().
    """
    global _ruff_command
    _ruff_command = None


@dataclass
class ParsedCGX:
    """Result of parsing a CGX file."""

    parser: CGXParser
    script_node: Optional[Element]
    template_nodes: List[Element]


def parse_cgx_file(content: str) -> ParsedCGX:
    """
    Parse a CGX file and extract script and template nodes.

    Args:
        content: The CGX file content as a string

    Returns:
        ParsedCGX with parser, script_node, and template_nodes
    """
    parser = CGXParser()
    parser.feed(content)

    script_node = parser.root.child_with_tag("script")
    template_nodes = [
        node
        for node in parser.root.children
        if not hasattr(node, "tag") or node.tag != "script"
    ]

    return ParsedCGX(
        parser=parser,
        script_node=script_node,
        template_nodes=template_nodes,
    )


def get_script_range(script_node: Element) -> tuple[int, int]:
    """
    Get the line range of a script node.

    Args:
        script_node: The script node from CGXParser

    Returns:
        Tuple of (start_line, end_line) where end_line is exclusive
    """
    start = script_node.location[0]
    end = script_node.end[0] - 1  # -1 because end points to closing tag
    return start, end


def create_virtual_render_content(
    original_content: str, modified_lines: List[str]
) -> str:
    """
    Create virtual content with render method appended for template-aware linting.

    This creates a virtual subclass with the render method compiled from the template,
    allowing ruff to see which imports and variables are used in the template.

    Args:
        original_content: The original CGX file content
        modified_lines: Lines with non-script sections commented out

    Returns:
        Modified content with virtual render method appended
    """
    try:
        # construct_ast compiles the template into a render() method
        tree, _ = construct_ast("in-memory", original_content)

        # Find the component class definition (last ClassDef in the AST)
        component_class_def = None
        for node in reversed(tree.body):
            if isinstance(node, ast.ClassDef):
                component_class_def = node
                break

        if not component_class_def:
            # No class found, just return the commented content
            return "".join(modified_lines)

        component_class_name = component_class_def.name

        # Find the render method
        render_method = None
        for node in component_class_def.body:
            if isinstance(node, ast.FunctionDef) and node.name == "render":
                render_method = node
                break

        if not render_method:
            # No render method, just return the commented content
            return "".join(modified_lines)

        # Unparse the render method to get the source code
        render_source = ast.unparse(render_method)
        render_source = textwrap.indent(render_source, "    ")

        # Append a virtual subclass with the render method
        # This helps ruff see that template variables are used
        modified_lines.append(
            f"class Virtual{component_class_name}({component_class_name}):\n"
        )
        # Add the render method with noqa to ignore issues in generated code
        for line in render_source.split("\n"):
            modified_lines.append(f"{line}  # noqa\n")

        return "".join(modified_lines)

    except Exception:
        # If anything fails, just return the basic commented content
        # This ensures linting still works even if AST construction fails
        return "".join(modified_lines)


def run_ruff_format(
    source: str, *, use_single_quotes: bool = False, check: bool = False
) -> str:
    """
    Format Python source code using ruff.

    Args:
        source: The Python source code to format
        use_single_quotes: If True, configure ruff to use single quotes
        check: If True, only check without modifying

    Returns:
        Formatted Python source code
    """
    ruff_command = [get_ruff_command(), "format"]
    if check:
        ruff_command.append("--check")

    with tempfile.TemporaryDirectory() as directory:
        target_file = Path(directory) / "source.py"
        target_file.write_text(source)

        # Create config if single quotes requested
        if use_single_quotes:
            config_file = Path(directory) / "ruff.toml"
            config_file.write_text('[format]\nquote-style = "single"\n')
            ruff_command.extend(["--config", str(config_file)])

        ruff_command.append(str(target_file))

        # Enable color output
        env = os.environ.copy()
        env["CLICOLOR_FORCE"] = "1"

        # Run ruff
        result = subprocess.run(ruff_command, capture_output=True, text=True, env=env)

        if result.returncode == 0 or not check:
            return target_file.read_text(encoding="utf-8")
        else:
            # If check mode and would change, return original
            return source


def run_ruff_check(
    source: str, output_format: str = "json"
) -> tuple[subprocess.CompletedProcess, Path]:
    """
    Run ruff check on Python source code.

    Args:
        source: The Python source code to check
        output_format: Output format for ruff (default: "json")

    Returns:
        CompletedProcess with the ruff result
    """
    with temp_py_file(source) as temp_path:
        ruff_command = [
            get_ruff_command(),
            "check",
            f"--output-format={output_format}",
            "--no-cache",
            "--ignore=RUF100",  # Ignore unused noqa (we add these for virtual render)
            str(temp_path),
        ]

        env = os.environ.copy()
        env["CLICOLOR_FORCE"] = "1"

        return subprocess.run(
            ruff_command, capture_output=True, text=True, env=env, timeout=30
        ), temp_path


@contextmanager
def temp_py_file(content: str):
    """
    Create a temporary Python file with the given content.

    Args:
        content: The Python code to write to the file

    Yields:
        Path to the temporary file

    Example:
        with temp_py_file("print('hello')") as path:
            result = subprocess.run(['python', str(path)])
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        yield temp_path
    finally:
        try:
            temp_path.unlink()
        except Exception:
            pass
