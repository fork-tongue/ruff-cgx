import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .utils import (
    create_virtual_render_content,
    extract_script_content,
    parse_cgx_file,
    run_ruff_check,
)


def _prepare_content_for_linting(content: str) -> str | None:
    """
    Prepare CGX content for linting by extracting Python and creating virtual content.

    Args:
        content: The CGX file content as a string

    Returns:
        The prepared Python code ready for ruff, or None if no script section
    """
    # Parse the CGX file
    parsed = parse_cgx_file(content)
    if not parsed.script_node:
        return None

    # Extract pure Python content
    script_content = extract_script_content(parsed.script_node)
    if not script_content:
        return None

    # Prepend with comment lines to preserve line numbers for diagnostics
    prefix_content = "#\n" * script_content.start_line

    modified_content = prefix_content + script_content.python_code

    # Create virtual content with render method
    # This allows ruff to see template variable usage
    virtual_content = create_virtual_render_content(content, modified_content)

    return virtual_content


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
    content = path.read_text(encoding="utf-8")

    # Prepare content for linting
    virtual_content = _prepare_content_for_linting(content)
    if virtual_content is None:
        return 1

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
    # Prepare content for linting
    virtual_content = _prepare_content_for_linting(content)
    if virtual_content is None:
        return []

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
