import ast
import os
import re
import subprocess
import tempfile
import textwrap
import tokenize
from pathlib import Path

from collagraph.cgx import cgx


def escape_ansi(line):
    ansi_escape = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", line)


def lint_file(path, fix=False, write=True):
    # plain_result = ast.unparse(tree)
    parser = cgx.CGXParser()
    parser.feed(Path(path).read_text())

    # Read the data from script block
    script_node = parser.root.child_with_tag("script")
    start, end = script_node.location[0], script_node.end[0] - 1
    script_range = range(start, end)

    tree, _ = cgx.construct_ast(path)

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
        parser = cgx.CGXParser()
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
