import logging
import os
import subprocess
import tempfile
from pathlib import Path

from collagraph.sfc.parser import CGXParser

from .template_formatter import format_template

logger = logging.getLogger(__name__)


def format_script(path, script_node, source_lines, check):
    """
    Returns formatted source and the original location of the node
    """
    start, end = script_node.location[0], script_node.end[0] - 1

    source = "".join(source_lines[start:end])

    ruff_command = ["ruff", "format"]
    if check:
        ruff_command.append("--check")

    # Write source to a temp file
    with tempfile.TemporaryDirectory() as directory:
        target_file = Path(directory) / "source.py"
        target_file.write_text(source)
        ruff_command.append(str(target_file))

        # Enable color output for ruff
        # TODO: check whether we want to force color or not?
        env = os.environ.copy()
        env["CLICOLOR_FORCE"] = "1"
        # Then run ruff to format the temp file
        output = subprocess.run(ruff_command, capture_output=True, text=True, env=env)
        with target_file.open(mode="r", encoding="utf-8") as fh:
            formatted_source = fh.readlines()

        stdout = output.stdout.replace(str(target_file), str(path))

    print(stdout, end="")  # noqa: T201
    if check:
        if output.returncode:
            exit(output.returncode)

    # Then return the contents
    return formatted_source, (start, end)


def format_file(path, check=False, write=True):
    """
    Format CGX files (the contents of the script tag) with ruff.

    Returns 0 if everything succeeded, or nothing changed.
    Returns 1 when running check and something would change.
    Returns list of lines when write is set to False instead
    of an error code (used for the test-suite).
    """
    path = Path(path)
    if path.suffix != ".cgx":
        return

    parser = CGXParser()
    parser.feed(path.read_text())

    with path.open(mode="r") as fh:
        lines = fh.readlines()

    script_node = parser.root.child_with_tag("script")
    template_nodes = [
        node
        for node in parser.root.children
        if not hasattr(node, "tag") or node.tag != "script"
    ]

    script_content, script_location = format_script(path, script_node, lines, check)
    formatted_template_nodes = [
        format_template(node, lines, parser=parser) for node in template_nodes
    ]

    changed_script = lines[script_location[0] : script_location[1]] != script_content
    changed_template = any(
        [
            lines[template_location[0] : template_location[1]] != template_content
            for template_content, template_location in formatted_template_nodes
        ]
    )
    needs_newline_at_end_of_file = not lines[-1].endswith("\n")
    changed = changed_script or changed_template or needs_newline_at_end_of_file
    if check:
        if changed:
            logger.warning(f"Would change: {path}")
            return 1
        return 0

    formatted_parts = reversed(
        sorted(
            [
                (script_content, script_location),
                *formatted_template_nodes,
            ],
            key=lambda x: x[1][0],
        )
    )

    for formatted_content, (start, end) in formatted_parts:
        lines[start:end] = formatted_content

    if needs_newline_at_end_of_file:
        lines.append("\n")

    if not write:
        return lines

    if changed:
        with path.open(mode="w") as fh:
            fh.writelines(lines)
    return 0
