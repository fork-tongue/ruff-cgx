"""Shared utilities for ruff-cgx linting and formatting."""

import ast
import os
import re
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import List

from collagraph.sfc.compiler import construct_ast
from collagraph.sfc.parser import CGXParser, Element

# Module-level configuration for ruff command
_ruff_command: str | None = None


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
    script_node: Element | None
    template_nodes: List[Element]


@dataclass
class ScriptContent:
    """Result of extracting Python content from a script node."""

    python_code: str  # Pure Python content (without leading newline)
    start_line: int  # 0-indexed line where Python actually starts
    end_line: int  # 0-indexed line where </script> tag is
    starts_on_new_line: bool  # Whether Python was on a new line after <script>
    closing_tag_inline: bool  # Whether </script> is on same line as last Python code


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


def extract_script_content(script_node: Element) -> ScriptContent | None:
    """
    Extract pure Python content from a script node.

    This handles cases where Python code is on the same line as the <script> tag
    by extracting the content from the TextElement child and determining the actual
    line boundaries.

    Args:
        script_node: The script node from CGXParser

    Returns:
        ScriptContent with pure Python code and location info, or None if no content
    """
    if not script_node.children:
        return None

    script_child = script_node.children[0]
    python_content = script_child.content
    assert "<script" not in python_content

    # Get the line where the <script> tag starts and where it ends
    script_tag_line = script_node.location[0] - 1  # Convert to 0-indexed
    end_line = script_node.end[0] - 1  # End tag line (0-indexed)

    # Determine if Python starts on a new line after <script>
    starts_on_new_line = python_content.startswith("\n")

    # Determine if closing tag is on the same line as Python code
    # If column > 0, there's content before the closing tag
    closing_tag_inline = script_node.end[1] > 0

    # Strip leading newline if present
    if starts_on_new_line:
        python_content = python_content[1:]
        start_line = script_tag_line + 1
    else:
        start_line = script_tag_line

    # Strip leading/trailing whitespace from the Python content
    # (parser may include spaces when tags are inline)
    python_content = python_content.strip()

    # Ensure content ends with a newline for proper formatting
    if python_content and not python_content.endswith("\n"):
        python_content += "\n"

    return ScriptContent(
        python_code=python_content,
        start_line=start_line,
        end_line=end_line,
        starts_on_new_line=starts_on_new_line,
        closing_tag_inline=closing_tag_inline,
    )


def create_virtual_render_content(original_content: str, modified_content: str) -> str:
    """
    Create virtual content with render method appended for template-aware linting.

    This creates a virtual subclass with the render method compiled from the template,
    allowing ruff to see which imports and variables are used in the template.

    Args:
        original_content: The original CGX file content
        modified_content: content with non-script sections commented out

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
            return modified_content

        component_class_name = component_class_def.name

        # Find the render method
        render_method = None
        for node in component_class_def.body:
            if isinstance(node, ast.FunctionDef) and node.name == "render":
                render_method = node
                break

        if not render_method:
            # No render method, just return the commented content
            return modified_content

        # Unparse the render method to get the source code
        render_source = ast.unparse(render_method)
        render_source = textwrap.indent(render_source, "    ")

        # Append a virtual subclass with the render method
        # This helps ruff see that template variables are used
        virtual_class_def = (
            f"class CGXVirtual{component_class_name}({component_class_name}):\n"
        )
        # Add the render method with noqa to ignore issues in generated code
        virtual_class_content = "".join(
            [f"{line}  # noqa\n" for line in render_source.splitlines()]
        )

        return modified_content + virtual_class_def + virtual_class_content

    except Exception:
        # If anything fails, just return the basic commented content
        # This ensures linting still works even if AST construction fails
        return modified_content


def is_isort_configured() -> bool:
    """Check if 'unsorted-imports' is both enabled and marked as should_fix."""
    result = False
    try:
        # Print ruff settings
        ruff_output = subprocess.run(
            ["ruff", "check", "--show-settings"], capture_output=True, text=True
        ).stdout

        # Get both the enabled + should_fix sections
        enabled_match = re.search(
            r"linter\.rules\.enabled = \[(.*?)\]", ruff_output, re.DOTALL
        )

        should_fix_match = re.search(
            r"linter\.rules\.should_fix = \[(.*?)\]", ruff_output, re.DOTALL
        )

        if not enabled_match or not should_fix_match:
            return False

        # Check that 'unsorted-imports' rule appears in both sections
        in_enabled = "unsorted-imports" in enabled_match.group(1)
        in_should_fix = "unsorted-imports" in should_fix_match.group(1)

        return in_enabled and in_should_fix

    except Exception:
        pass
    return result


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
    should_sort_imports = is_isort_configured()

    # Enable color output for format operations
    env = os.environ.copy()
    env["CLICOLOR_FORCE"] = "1"

    current_source = source

    # If isort is configured, sort imports first using --diff approach
    if should_sort_imports:
        # Run ruff check with --diff to get import sorting changes
        # Disable color for diff output
        env_no_color = os.environ.copy()

        isort_command = [
            get_ruff_command(),
            "check",
            "--select",
            "I",
            "--diff",
            "--no-cache",
            "--stdin-filename",
            "source.py",
            "-",
        ]

        isort_result = subprocess.run(
            isort_command,
            input=current_source,
            capture_output=True,
            text=True,
            env=env_no_color,
            timeout=30,
        )

        # Apply the diff if there are any import sorting changes
        if isort_result.stdout.strip():
            try:
                current_source = apply_unified_diff(current_source, isort_result.stdout)
            except Exception:
                # If diff application fails, continue with original
                pass

    # Use stdin approach for formatting
    ruff_command = [get_ruff_command(), "format", "--stdin-filename", "source.py"]
    if check:
        ruff_command.append("--check")
    if use_single_quotes:
        # Use inline config instead of temp file
        ruff_command.extend(["--config", "indent-width=2"])
        ruff_command.extend(["--config", 'format.quote-style="single"'])
    ruff_command.append("-")

    result = subprocess.run(
        ruff_command,
        input=current_source,
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode == 0:
        return result.stdout
    else:
        # If check mode and would change, return original
        return source


def apply_unified_diff(original: str, diff: str) -> str:
    """
    Apply a unified diff to source code.

    Args:
        original: The original source code
        diff: The unified diff output from ruff

    Returns:
        The patched source code

    Raises:
        ValueError: If the diff cannot be applied
    """
    if not diff.strip():
        return original

    original_lines = original.splitlines(keepends=True)
    result_lines = []

    diff_lines = diff.splitlines()
    i = 0

    # Skip the header lines (---, +++, and any "Would fix" messages)
    while i < len(diff_lines):
        line = diff_lines[i]
        if line.startswith("@@"):
            break
        i += 1

    # Track current position in original
    original_idx = 0

    while i < len(diff_lines):
        line = diff_lines[i]

        if line.startswith("@@"):
            # Parse hunk header: @@ -start,count +start,count @@
            parts = line.split()
            if len(parts) >= 3:
                # Extract old start position (1-indexed)
                old_start = int(parts[1].split(",")[0][1:])
                # Add unchanged lines up to this hunk
                while original_idx < old_start - 1:
                    result_lines.append(original_lines[original_idx])
                    original_idx += 1
            i += 1

        elif line.startswith("-"):
            # Line removed - skip it in original
            original_idx += 1
            i += 1

        elif line.startswith("+"):
            # Line added - add to result
            result_lines.append(line[1:] + "\n")
            i += 1

        elif line.startswith(" "):
            # Context line - copy from original
            result_lines.append(original_lines[original_idx])
            original_idx += 1
            i += 1

        else:
            # End of hunk or unknown line
            i += 1

    # Add remaining original lines
    while original_idx < len(original_lines):
        result_lines.append(original_lines[original_idx])
        original_idx += 1

    return "".join(result_lines)


def run_ruff_check(
    source: str, output_format: str = "json", fix: bool = False
) -> tuple[subprocess.CompletedProcess, Path | None, str | None]:
    """
    Run ruff check on Python source code.

    Args:
        source: The Python source code to check
        output_format: Output format for ruff (default: "json")
        fix: Whether to apply fixes (default: False)

    Returns:
        Tuple of (CompletedProcess with the ruff result, temp file path or None,
        fixed content if fix=True else None)
    """
    env = os.environ.copy()

    # Use stdin approach with --diff for better performance
    if fix:
        # Use --diff to get unified diff output, then apply it
        # Note: We don't set CLICOLOR_FORCE for diff mode to avoid ANSI codes
        ruff_command = [
            get_ruff_command(),
            "check",
            "--diff",
            "--no-cache",
            "--ignore=RUF100",  # Ignore unused noqa (we add these for virtual render)
            "--stdin-filename",
            "source.py",
            "-",
        ]

        result = subprocess.run(
            ruff_command,
            input=source,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

        # Apply the diff to get fixed content
        # Note: diff output is in stdout, stderr contains "Would fix N errors" message
        diff_output = result.stdout
        if diff_output.strip():
            try:
                fixed_content = apply_unified_diff(source, diff_output)
            except Exception:
                # If diff application fails, fall back to original
                fixed_content = source
        else:
            # No diff means no fixes needed
            fixed_content = source

        # For CLI usage (output_format="full"), run again on FIXED content
        # to get remaining diagnostics (not the ones we just fixed)
        # LSP doesn't need this since it only uses the fixed content
        if output_format == "full":
            # Run again without --diff to get the full diagnostic output with colors
            # IMPORTANT: Run on fixed_content, not original source
            env_with_color = env.copy()
            env_with_color["CLICOLOR_FORCE"] = "1"

            check_command = [
                get_ruff_command(),
                "check",
                "--output-format=full",
                "--no-cache",
                "--ignore=RUF100",
                "--stdin-filename",
                "source.py",
                "-",
            ]
            result = subprocess.run(
                check_command,
                input=fixed_content,  # Run on fixed content, not original!
                capture_output=True,
                text=True,
                env=env_with_color,
                timeout=30,
            )

        return result, None, fixed_content

    # Check-only mode (no fix) - enable colors for better CLI experience
    env["CLICOLOR_FORCE"] = "1"

    ruff_command = [
        get_ruff_command(),
        "check",
        f"--output-format={output_format}",
        "--no-cache",
        "--ignore=RUF100",  # Ignore unused noqa (we add these for virtual render)
        "--stdin-filename",
        "source.py",
        "-",
    ]

    result = subprocess.run(
        ruff_command,
        input=source,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    return result, None, None
