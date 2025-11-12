import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .utils import (
    ParsedCGX,
    ScriptContent,
    create_virtual_render_content,
    extract_script_content,
    parse_cgx_file,
    run_ruff_check,
)


def _prepare_content_for_linting(
    content: str,
) -> tuple[str, ParsedCGX, ScriptContent] | None:
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

    return virtual_content, parsed, script_content


def lint_file(path, fix=False, **_):
    """
    Lint a CGX file using ruff (CLI version).

    Args:
        path: Path to the CGX file
        fix: Whether to fix issues (default: False)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")

    # Prepare content for linting
    virtual_content = _prepare_content_for_linting(content)
    if virtual_content is None:
        return 1

    virtual_content, parsed, script_content = virtual_content

    # Run ruff check with full output (for CLI)
    result, temp_path, fixed_content = run_ruff_check(
        virtual_content, output_format="full", fix=fix
    )

    # Replace temp file path with actual path in output
    stdout = result.stdout.replace(str(temp_path), str(path)).strip()
    print(stdout)  # noqa: T201

    # If fix was requested and we got fixed content, apply it back to the file
    if fix and fixed_content:
        _apply_fixes_to_file(path, content, parsed, script_content, fixed_content)

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

    virtual_content, _, _ = virtual_content

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
    result, _, _ = run_ruff_check(python_content, output_format="json")
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


def _extract_fixed_python(fixed_content: str, script_content: ScriptContent) -> str:
    """
    Extract the actual fixed Python code from the fixed virtual content.

    The fixed_content has:
    1. Comment lines prepended (# lines to preserve line numbers)
    2. The actual fixed Python code
    3. Virtual render method appended (starting with "class CGXVirtual...")

    Args:
        fixed_content: The fixed content from ruff (includes comments + virtual)
        script_content: Original script content metadata

    Returns:
        Just the fixed Python code
    """
    lines = fixed_content.splitlines(keepends=True)

    # Skip the comment prefix lines
    start_idx = script_content.start_line

    # The virtual class is always named CGXVirtual{OriginalClassName}
    # Try to find it by looking for "class CGXVirtual"
    end_idx = len(lines)
    for i in range(start_idx, len(lines)):
        if lines[i].startswith("class CGXVirtual"):
            end_idx = i
            break

    # Extract just the Python code
    python_lines = lines[start_idx:end_idx]
    python_code = "".join(python_lines)

    # Strip trailing whitespace but preserve the final newline
    python_code = python_code.rstrip()
    if python_code and not python_code.endswith("\n"):
        python_code += "\n"

    return python_code


def _apply_fixes_to_file(
    path: Path,
    original_content: str,
    parsed: ParsedCGX,
    script_content: ScriptContent,
    fixed_content: str,
) -> None:
    """
    Apply the fixed Python code back to the original CGX file.

    Args:
        path: Path to the CGX file
        original_content: The original file content
        parsed: Parsed CGX structure
        script_content: Script content metadata
        fixed_content: The fixed content from ruff (includes virtual content)
    """
    # Extract just the fixed Python code
    fixed_python = _extract_fixed_python(fixed_content, script_content)

    # Split original content into lines
    original_lines = original_content.splitlines(keepends=True)

    # Build the new content by replacing the script section
    new_lines = []

    # Add everything before the script section
    script_start_tag_line = parsed.script_node.location[0] - 1  # 0-indexed
    new_lines.extend(original_lines[:script_start_tag_line])

    # Add the script tag and fixed Python
    new_lines.append("<script>\n")
    new_lines.append(fixed_python)
    new_lines.append("</script>\n")

    # Add everything after the script section
    # This is already the line after </script> (1-indexed)
    script_end_tag_line = parsed.script_node.end[0]
    if script_end_tag_line < len(original_lines):
        new_lines.extend(original_lines[script_end_tag_line:])

    # Write back to file
    new_content = "".join(new_lines)

    # Ensure file ends with newline
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"

    path.write_text(new_content, encoding="utf-8")
