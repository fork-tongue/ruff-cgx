import logging
from pathlib import Path

from .template_formatter import format_template
from .utils import (
    extract_script_content,
    parse_cgx_file,
    run_ruff_format,
)

logger = logging.getLogger(__name__)


def format_script(script_node, check=False):
    """
    Format script section using ruff.

    Args:
        script_node: script node from collagraph's parser
        source_lines: contents of source file as list of lines
        check: If True, only check without modifying (for ruff format --check)

    Returns:
        Tuple of (formatted_lines, (start_line, end_line))
    """
    if script_node.end is None:
        raise RuntimeError("Invalid script node: no end")

    # Extract pure Python content
    script_content = extract_script_content(script_node)
    if not script_content:
        # No content to format - return original lines unchanged
        start = script_node.location[0] - 1  # Convert to 0-indexed
        end = script_node.end[0] - 1  # End tag line
        return [], (start, end)

    # Format using ruff
    formatted_source = run_ruff_format(script_content.python_code, check=check)

    # Convert to lines
    formatted_lines = formatted_source.splitlines(keepends=True)

    # If Python was on same line as tag, prepend the tag on its own line
    if not script_content.starts_on_new_line:
        formatted_lines = formatted_lines

    # If closing tag was inline with Python code, we need to:
    # 1. Append closing tag to formatted output
    # 2. Extend replacement range to include that line
    if script_content.closing_tag_inline:
        replacement_end = script_content.end_line
    else:
        replacement_end = script_content.end_line

    # Return formatted content with range that will be replaced
    return formatted_lines, (script_content.start_line, replacement_end)


def format_file(path: str | Path, check: bool = False, write: bool = True) -> int | str:
    """
    Format CGX files (the contents of the script tag) with ruff.

    Args:
        content: The CGX file content as a string
        uri: Optional URI for logging purposes

    Returns:
        0 if everything succeeded, or nothing changed.
        1 when running check and something would change.
        list of lines when write is set to False instead
        of an error code (used for the test-suite).
    """
    path = Path(path)
    if path.suffix != ".cgx":
        return 1

    content = path.read_text(encoding="utf-8")

    formatted_content = format_cgx_content(content, str(path))

    changed = content != formatted_content
    if check:
        if changed:
            print(f"Would reformat: {path}")  # noqa: T201
            return 1
        print("1 file already formatted")  # noqa: T201
        return 0

    # Print status message based on changes
    if changed:
        print("1 file reformatted")  # noqa: T201
    else:
        print("1 file left unchanged")  # noqa: T201

    if not write:
        return formatted_content

    if changed:
        with path.open(mode="w", encoding="utf-8") as fh:
            fh.write(formatted_content)

    return 0


def format_cgx_content(content: str, uri: str = "") -> str:
    """
    Format CGX file content (for LSP use).

    Args:
        content: The CGX file content as a string
        uri: Optional URI for logging purposes

    Returns:
        Formatted content as a string
    """
    try:
        # Parse the CGX file
        parsed = parse_cgx_file(content)

        # Check for script node
        if not parsed.script_node:
            logger.warning(f"Missing script node in {uri}")
            return content

        # Format script section
        script_lines, script_location = format_script(parsed.script_node)
        script_node = ["<script>\n", *script_lines, "</script>\n"]

        # Format all template nodes
        formatted_template_nodes = [
            format_template(node) for node in parsed.template_nodes
        ]

        # Sort all formatted parts by their starting location
        # as to keep the same order that was in the original file
        formatted_parts = sorted(
            [
                (script_node, script_location),
                *formatted_template_nodes,
            ],
            key=lambda x: x[1][0],
        )

        # Flatten the formatted parts
        formatted = []
        for content, _ in formatted_parts:
            formatted += content
            # Put one empty line between root elements
            formatted += "\n"

        # Pop the last added line break
        formatted.pop()

        return "".join(formatted)

    except Exception as e:
        logger.error(f"Error formatting {uri}: {e}", exc_info=True)
        # Return original content on error
        return content
