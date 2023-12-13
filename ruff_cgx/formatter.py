import logging
import subprocess
import tempfile
from pathlib import Path

from collagraph.cgx import cgx

from template import format_template

logger = logging.getLogger(__name__)


def format_script(script_node, source_lines, check):
    start, end = script_node.location[0], script_node.end[0] - 1

    source = "".join(source_lines[start:end])

    ruff_command = ["ruff", "format"]

    # Write source to a temp file
    with tempfile.TemporaryDirectory() as directory:
        target_file = Path(directory) / "source.py"
        target_file.write_text(source)
        ruff_command.append(str(target_file))

        # Then run ruff to format the temp file
        subprocess.run(ruff_command)
        with target_file.open(mode="r", encoding="utf-8") as fh:
            formatted_source = fh.readlines()

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

    parser = cgx.CGXParser()
    parser.feed(path.read_text())

    with path.open(mode="r") as fh:
        lines = fh.readlines()

    script_node = parser.root.child_with_tag("script")
    template_node = parser.root.child_with_tag("template")

    script_content, script_location = format_script(script_node, lines, check)
    template_content, template_location = format_template(
        template_node, lines, parser=parser
    )

    changed = (
        lines[script_location[0] : script_location[1]] != script_content
        or lines[template_location[0] : template_location[1]] != template_content
    )
    if check:
        if changed:
            logger.warning(f"Would change: {path}")
            return 1
        return 0

    if script_location[0] > template_location[0]:
        lines[script_location[0] : script_location[1]] = script_content
        lines[template_location[0] : template_location[1]] = template_content
    else:
        lines[script_location[0] : script_location[1]] = script_content
        lines[template_location[0] : template_location[1]] = template_content
    if not write:
        return lines

    if changed:
        with path.open(mode="w") as fh:
            fh.writelines(lines)
    return 0
