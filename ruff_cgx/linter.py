import ast
import json
import os
import re
import subprocess
import tempfile
import textwrap
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import List

from collagraph.sfc.compiler import construct_ast
from collagraph.sfc.parser import CGXParser


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


def escape_ansi(line):
    ansi_escape = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", line)


def lint_file(path, fix=False, write=True):
    # plain_result = ast.unparse(tree)
    parser = CGXParser()
    parser.feed(Path(path).read_text())

    # Read the data from script block
    script_node = parser.root.child_with_tag("script")
    start, end = script_node.location[0], script_node.end[0] - 1
    script_range = range(start, end)

    tree, _ = construct_ast(path)

    # The only thing that we can't check is: RUF100: whether
    # there are unneeded noqa statement. That's because we use
    # these noqa statements to comment out the lines of the
    # virtual render function
    ruff_command = ["ruff", "check", "--ignore", "RUF100"]

    with path.open(mode="r", encoding="utf-8") as fh:
        source_raw = fh.readlines()

    # Comment out all non-script lines
    template_commented = [
        line if idx in script_range else "#\n" for idx, line in enumerate(source_raw)
    ]

    component_class_def = next(
        node for node in reversed(tree.body) if isinstance(node, ast.ClassDef)
    )
    component_class_name = component_class_def.name
    render_method = next(
        node
        for node in component_class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "render"
    )
    render_method = ast.unparse(render_method)
    render_method = textwrap.indent(render_method, "    ")

    # Insert a line that mimics a subclass so that any code that follows the last
    # class definition, won't break the virtual render method
    template_commented.append(
        f"class Virtual{component_class_name}({component_class_name}):\n"
    )
    # Append the virtual render method into the virtual subclass definition
    template_commented.extend(
        [f"{line}  # noqa\n" for line in render_method.split("\n")]
    )

    with tempfile.TemporaryDirectory() as directory:
        target_file = Path(directory) / "source.py"
        target_file.write_text("".join(template_commented))

        ruff_command.append(str(target_file))

        # Force color
        # TODO: figure out if we can detect if we can use color or not
        env = os.environ.copy()
        env["CLICOLOR_FORCE"] = "1"

        result = subprocess.run(
            ruff_command,
            capture_output=True,
            text=True,
            env=env,
        )

    stdout = result.stdout.replace(str(target_file), str(path))
    stdout.strip()
    print(stdout, end="")  # noqa: T201
    return result.returncode


def read_lines_from_filename_patched(path: Path) -> list[str]:
    """Read the lines for a file."""
    try:
        parser = CGXParser()
        parser.feed(Path(path).read_text())

        # Read the data from script block
        script_node = parser.root.child_with_tag("script")
        start, end = script_node.location[0], script_node.end[0] - 1

        with tokenize.open(path) as fh:
            result = fh.readlines()

            actual_result = result[start:end]
            # Prepend some empty (commented) lines to make the errors
            # point out the right location in the cgx file
            actual_result = [
                # prepend with some empty lines
                *(start * ["# noqa\n"]),
                *actual_result,
                # append some more empty lines
                *(9 * ["# noqa\n"]),
            ]

            return actual_result

    except (SyntaxError, UnicodeError):
        # If we can't detect the codec with tokenize.detect_encoding, or
        # the detected encoding is incorrect, just fallback to latin-1.
        with open(path, encoding="latin-1") as fd:
            return fd.readlines()


class RuffLinter:
    """Linter that uses ruff to check Python code in CGX files."""

    def __init__(self):
        """Initialize the linter."""
        self.ruff_available = self._check_ruff_available()

    def _check_ruff_available(self) -> bool:
        """Check if ruff is available in the system."""
        try:
            result = subprocess.run(
                ["ruff", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def lint_cgx_file(
        self, content: str, file_path: str = "<stdin>"
    ) -> List[Diagnostic]:
        """
        Lint a CGX file by extracting the script section and running ruff.

        This follows the approach from ruff-cgx:
        1. Parse the CGX file using Collagraph's parser
        2. Extract the script section with line numbers
        3. Comment out non-script lines to preserve line numbers
        4. Use construct_ast to create a render method from the template
        5. Append the render method to see template variable usage
        6. Run ruff on the modified content

        Args:
            content: The CGX file content
            file_path: Optional file path for better error messages

        Returns:
            List of diagnostics
        """
        if not self.ruff_available:
            return [
                Diagnostic(
                    line=0,
                    column=0,
                    end_line=0,
                    end_column=0,
                    message="Ruff is not available. "
                    "Please install it: uv tool install ruff",
                    code="ruff-unavailable",
                    severity="error",
                )
            ]

        # Parse the CGX file using Collagraph's parser
        try:
            parser = CGXParser()
            parser.feed(content)
        except Exception as e:
            return [
                Diagnostic(
                    line=0,
                    column=0,
                    end_line=0,
                    end_column=0,
                    message=f"Failed to parse CGX file: {e!s}",
                    code="parse-error",
                    severity="error",
                )
            ]

        # Check if there's a script section
        script_node = parser.root.child_with_tag("script")
        if not script_node:
            # No script section, nothing to lint
            return []

        # Get the line range of the script section
        # script_node.location[0] is the starting line (0-indexed)
        # script_node.end[0] is the ending line (0-indexed)
        start_line = script_node.location[0]
        # -1 because end points to closing tag
        end_line = script_node.end[0] - 1

        # Create a modified version where non-script lines are commented out
        source_lines = content.splitlines(keepends=True)

        # Add newline to lines that don't have it
        source_lines = [
            line if line.endswith("\n") else line + "\n" for line in source_lines
        ]

        script_range = range(start_line, end_line)

        # Comment out all non-script lines to preserve line numbers
        modified_lines = [
            line if idx in script_range else "#\n"
            for idx, line in enumerate(source_lines)
        ]

        # Try to construct AST and append virtual render method
        # This allows ruff to see template variable usage
        virtual_content = self._append_render_method(modified_lines, content, file_path)

        # Run ruff on the virtual file
        diagnostics = self._run_ruff(virtual_content)

        return diagnostics

    def _append_render_method(
        self, modified_lines: List[str], original_content: str, file_path: str
    ) -> str:
        """
        Append a virtual render method to see template variable usage.

        Args:
            modified_lines: The lines with non-script sections commented out
            original_content: The original CGX file content
            file_path: Path to the file (used by construct_ast)

        Returns:
            The modified content with appended render method
        """
        try:
            # We need to write to a temp file for construct_ast to work
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cgx", delete=False
            ) as f:
                f.write(original_content)
                temp_cgx_path = Path(f.name)

            try:
                # construct_ast compiles the template into a render() method
                tree, _ = construct_ast(temp_cgx_path)

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

            finally:
                # Clean up temp file
                try:
                    temp_cgx_path.unlink()
                except Exception:
                    pass

        except Exception:
            # If anything fails, just return the basic commented content
            # This ensures linting still works even if AST construction fails
            return "".join(modified_lines)

    def _run_ruff(self, python_content: str) -> List[Diagnostic]:
        """
        Run ruff on Python content and return diagnostics.

        Args:
            python_content: The Python code (with non-script lines commented)

        Returns:
            List of diagnostics
        """
        # Write content to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_content)
            temp_path = f.name

        try:
            # Run ruff with JSON output
            # Ignore RUF100 (unused noqa) because we add noqa to virtual render method
            result = subprocess.run(
                [
                    "ruff",
                    "check",
                    "--output-format=json",
                    "--no-cache",
                    "--ignore=RUF100",
                    temp_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Parse ruff output
            if result.stdout:
                try:
                    ruff_diagnostics = json.loads(result.stdout)
                except json.JSONDecodeError:
                    return []

                # Convert ruff diagnostics to our format
                diagnostics = []
                for diag in ruff_diagnostics:
                    # Ruff returns 1-indexed line numbers
                    line = (
                        diag.get("location", {}).get("row", 1) - 1
                    )  # Convert to 0-indexed
                    column = (
                        diag.get("location", {}).get("column", 1) - 1
                    )  # Convert to 0-indexed
                    end_line = diag.get("end_location", {}).get("row", line + 1) - 1
                    end_column = (
                        diag.get("end_location", {}).get("column", column + 1) - 1
                    )

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
            else:
                return []

        except subprocess.TimeoutExpired:
            return [
                Diagnostic(
                    line=0,
                    column=0,
                    end_line=0,
                    end_column=0,
                    message="Ruff timed out while linting",
                    code="ruff-timeout",
                    severity="error",
                )
            ]
        except Exception as e:
            return [
                Diagnostic(
                    line=0,
                    column=0,
                    end_line=0,
                    end_column=0,
                    message=f"Error running ruff: {e!s}",
                    code="ruff-error",
                    severity="error",
                )
            ]
        finally:
            # Clean up temporary file
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
