import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .utils import (
    create_virtual_render_content,
    get_script_range,
    parse_cgx_file,
    run_ruff_check,
)


def lint_file(path, **_):
    """
    Lint a CGX file using ruff (CLI version).

    Args:
        path: Path to the CGX file
        fix: Whether to fix issues (not implemented)
        write: Whether to write changes (not implemented)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    path = Path(path)
    content = path.read_text()

    # Parse CGX file
    parsed = parse_cgx_file(content)
    if not parsed.script_node:
        return 1

    # Get script range
    start, end = get_script_range(parsed.script_node)
    script_range = range(start, end)

    # Read source lines
    lines = content.splitlines(keepends=True)

    # Comment out all non-script lines
    template_commented = [
        line if idx in script_range else "#\n" for idx, line in enumerate(lines)
    ]

    # Create virtual content with render method
    virtual_content = create_virtual_render_content(content, template_commented)

    # Run ruff check with full output (for CLI)
    result, temp_path = run_ruff_check(virtual_content, output_format="full")

    # Replace temp file path with actual path in output
    stdout = result.stdout.replace(str(temp_path), str(path)).strip()
    print(stdout)  # noqa: T201
    return result.returncode


@dataclass
class Diagnostic:
    """Represents a diagnostic message (error, warning, etc.)."""

    line: int
    column: int
    end_line: int
    end_column: int
    message: str
    code: str
    severity: str  # 'error', 'warning', 'info'
    source: str = "ruff"


def lint_cgx_content(content: str) -> List[Diagnostic]:
    """
    Lint CGX file content (for LSP use).

    Args:
        content: The CGX file content as a string
        file_path: Optional file path for better error messages

    Returns:
        List of diagnostics
    """
    # Parse the CGX file using Collagraph's parser
    parsed = parse_cgx_file(content)

    # Check if there's a script section
    if not parsed.script_node:
        # No script section, nothing to lint
        return []

    # Get the line range of the script section
    start_line, end_line = get_script_range(parsed.script_node)

    # Create a modified version where non-script lines are commented out
    source_lines = content.splitlines(keepends=True)

    # Add newline to lines that don't have it (to make sure last line has it?)
    source_lines = [
        line if line.endswith("\n") else f"{line}\n" for line in source_lines
    ]

    script_range = range(start_line, end_line)

    # Comment out all non-script lines to preserve line numbers
    modified_lines = [
        line if idx in script_range else "#\n" for idx, line in enumerate(source_lines)
    ]

    # Try to construct AST and append virtual render method
    # This allows ruff to see template variable usage
    virtual_content = create_virtual_render_content(content, modified_lines)

    # Run ruff on the virtual file
    diagnostics = _run_ruff(virtual_content)

    return diagnostics


def _run_ruff(python_content: str) -> List[Diagnostic]:
    """
    Run ruff on Python content and return diagnostics.

    Args:
        python_content: The Python code (with non-script lines commented)

    Returns:
        List of diagnostics
    """
    # Run ruff check with JSON output
    result, _ = run_ruff_check(python_content, output_format="json")
    if not result.stdout:
        return []

    try:
        ruff_diagnostics = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    # Convert ruff diagnostics to our format
    diagnostics = []
    for diag in ruff_diagnostics:
        # Ruff returns 1-indexed line numbers
        line = diag.get("location", {}).get("row", 1) - 1  # Convert to 0-indexed
        column = diag.get("location", {}).get("column", 1) - 1  # Convert to 0-indexed
        end_line = diag.get("end_location", {}).get("row", line + 1) - 1
        end_column = diag.get("end_location", {}).get("column", column + 1) - 1

        # Determine severity based on ruff's message type
        severity = "warning"
        code = diag.get("code", "unknown")
        if code.startswith("E"):
            severity = "error"
        elif code.startswith("F"):
            severity = "error"

        diagnostics.append(
            Diagnostic(
                line=line,
                column=column,
                end_line=end_line,
                end_column=end_column,
                message=diag.get("message", "Unknown error"),
                code=code,
                severity=severity,
            )
        )

    return diagnostics
