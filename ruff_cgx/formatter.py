import logging
from pathlib import Path

from .template_formatter import format_template
from .utils import (
    extract_script_content,
    get_script_range,
    parse_cgx_file,
    run_ruff_format,
)

logger = logging.getLogger(__name__)


def format_script(script_node, source_lines, check=False):
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
        # No content to format
        start, end = get_script_range(script_node)
        return source_lines[start:end], (start, end)

    # Format using ruff
    formatted_source = run_ruff_format(script_content.python_code, check=check)

    # Convert to lines
    formatted_lines = formatted_source.splitlines(keepends=True)

    # If Python was on same line as tag, prepend the tag on its own line
    if not script_content.starts_on_new_line:
        formatted_lines = ["<script>\n", *formatted_lines]

    # Return formatted content with range that will be replaced
    # This ensures Python code always starts on a new line after <script>
    return formatted_lines, (script_content.start_line, script_content.end_line)


def format_file(path, check=False, write=True):
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
        return

    content = path.read_text(encoding="utf-8")
    parsed = parse_cgx_file(content)

    lines = content.splitlines(keepends=True)

    script_content, script_location = format_script(parsed.script_node, lines)
    formatted_template_nodes = [format_template(node) for node in parsed.template_nodes]

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
            print(f"Would reformat: {path}")  # noqa: T201
            return 1
        print("1 file already formatted")  # noqa: T201
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

    # Print status message based on changes
    if changed:
        print("1 file reformatted")  # noqa: T201
    else:
        print("1 file left unchanged")  # noqa: T201

    if not write:
        # For testing, return the lines instead of writing
        return lines

    if changed:
        with path.open(mode="w", encoding="utf-8") as fh:
            fh.writelines(lines)

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

        # Split content into lines
        lines = content.splitlines(keepends=True)

        # Check for script node
        if not parsed.script_node:
            logger.warning(f"Missing script node in {uri}")
            return content

        # Format script section
        script_content, script_location = format_script(parsed.script_node, lines)

        # Format all template nodes
        formatted_template_nodes = [
            format_template(node) for node in parsed.template_nodes
        ]

        # Check if newline is needed at end of file
        needs_newline_at_end_of_file = lines and not lines[-1].endswith("\n")

        # Sort all formatted parts by their starting location
        # (in reverse order for replacement)
        formatted_parts = reversed(
            sorted(
                [
                    (script_content, script_location),
                    *formatted_template_nodes,
                ],
                key=lambda x: x[1][0],
            )
        )

        # Replace content in reverse order to maintain correct line indices
        for formatted_content, (start, end) in formatted_parts:
            lines[start:end] = formatted_content

        # Add newline at end if needed
        if needs_newline_at_end_of_file:
            lines.append("\n")

        return "".join(lines)

    except Exception as e:
        logger.error(f"Error formatting {uri}: {e}", exc_info=True)
        # Return original content on error
        return content
