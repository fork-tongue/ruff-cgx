import logging
import subprocess
import tempfile
from pathlib import Path

from collagraph.sfc.parser import Comment, TextElement

logger = logging.getLogger(__name__)

INDENT = "  "
SORTING = [
    # DEFINITION
    {"v-is"},
    # LIST_RENDERING
    {"v-for"},
    # CONDITIONALS
    {"v-if", "v-else-if", "v-else"},
    # UNIQUE
    {"id", "ref", "key"},
    # SLOT
    {"v-slot", "#"},
    # "v-model",
    # OTHER_ATTR
    {"v-bind", ":"},
    # EVENTS
    {"v-on", "@"},
]
OTHER_ATTR = SORTING.index({"v-bind", ":"})
UNIQUE_ATTR = SORTING.index({"id", "ref", "key"})


def format_python_expression(expr: str) -> str:
    """
    Format a Python expression using ruff with single quotes.

    Args:
        expr: The Python expression as a string

    Returns:
        Formatted expression as a string (using single quotes)
    """
    if not expr or not expr.strip():
        return expr

    try:
        # Wrap the expression in a dummy assignment to make it valid Python
        # This allows ruff to format it properly
        wrapped = f"__dummy__ = {expr}"

        with tempfile.TemporaryDirectory() as directory:
            target_file = Path(directory) / "expr.py"
            target_file.write_text(wrapped)

            # Create a ruff.toml config file to use single quotes
            config_file = Path(directory) / "ruff.toml"
            config_file.write_text('[format]\nquote-style = "single"\n')

            # Format with ruff using the config
            result = subprocess.run(
                ["ruff", "format", "--config", str(config_file), str(target_file)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                formatted = target_file.read_text()
                # Extract the expression back out
                # (remove "__dummy__ = " and trailing newline)
                prefix = "__dummy__ = "
                if formatted.startswith(prefix):
                    formatted_expr = formatted[len(prefix) :].rstrip("\n")
                    return formatted_expr

        # If formatting failed, return original
        return expr

    except Exception as e:
        logger.debug(f"Could not format expression '{expr}': {e}")
        return expr


def format_template(template_node, lines):
    """
    Returns formatted node and the original location of the template node
    """
    # Find beginning and end of script block
    start, end = template_node.location[0] - 1, template_node.end[0]

    result = format_node(template_node, depth=0)
    # Replace all tabs with the default indent and add line breaks
    tab = "\t"
    result = [f"{line.replace(tab, INDENT)}\n" for line in result]
    return result, (start, end)


def sort_attr(attr):
    """
    This rule aims to enforce ordering of component attributes. The default order is
    specified in the Vue.js Style Guide and is:

    * DEFINITION e.g. 'is', 'v-is'
    * LIST_RENDERING e.g. 'v-for item in items'
    * CONDITIONALS e.g. 'v-if', 'v-else-if', 'v-else', 'v-show', 'v-cloak'
    * RENDER_MODIFIERS e.g. 'v-once', 'v-pre'
    * GLOBAL e.g. 'id'
    * UNIQUE e.g. 'ref', 'key'
    * SLOT e.g. 'v-slot', 'slot'.
    * TWO_WAY_BINDING e.g. 'v-model'
    * OTHER_DIRECTIVES e.g. 'v-custom-directive'
    * OTHER_ATTR alias for [ATTR_DYNAMIC, ATTR_STATIC, ATTR_SHORTHAND_BOOL]:
        * ATTR_DYNAMIC e.g. 'v-bind:prop="foo"', ':prop="foo"'
        * ATTR_STATIC e.g. 'prop="foo"', 'custom-prop="foo"'
        * ATTR_SHORTHAND_BOOL e.g. 'boolean-prop'
    * EVENTS e.g. '@click="functionCall"', 'v-on="event"'
    * CONTENT e.g. 'v-text', 'v-html'
    """

    for idx, prefixes in enumerate(SORTING):
        for prefix in prefixes:
            if idx != UNIQUE_ATTR:
                if attr.startswith(prefix):
                    return f"{idx}{attr.lstrip(prefix)}"
            else:
                if attr == prefix:
                    return f"{idx}{attr}"
    else:
        if not attr.startswith(("v-")):
            return f"{OTHER_ATTR}{attr}"

    return f"{len(SORTING)}{attr}"


def format_attribute(key, value):
    """
    Format an attribute key-value pair.

    If the attribute is a binding (:attr) or event (@event) or directive (v-),
    format the Python expression in the value.
    """
    # Handle boolean attributes (including v-else which is always boolean)
    if not key.startswith((":", "@")):
        if value is True:
            return key

    # Format Python expressions in bindings, events, and directives
    if key.startswith((":", "@", "v-")) and isinstance(value, str) and value.strip():
        value = value.strip()
        # For v-for, don't format as it has special syntax
        # For v-slot, don't format as it has special syntax
        if not key.startswith(("v-for", "v-slot", "#")):
            formatted_value = format_python_expression(value)
            return f'{key}="{formatted_value}"'

    return f'{key}="{value}"'


def format_node(node, depth):
    result = []
    indent = depth * INDENT

    if isinstance(node, Comment):
        result.append(f"{indent}<!--{node.content}-->")
    elif isinstance(node, TextElement):
        result.append(f"{indent}{node.content.strip()}")
    else:
        start = f"{indent}<{node.tag}"
        if node.attrs:
            if len(node.attrs) == 1:
                key, val = next(iter(node.attrs.items()))
                attr = format_attribute(key, val)
                start = f"{start} {attr}"
            else:
                attrs = []
                for key in sorted(node.attrs, key=sort_attr):
                    attr = format_attribute(key, node.attrs[key])
                    attrs.append(f"{indent}{INDENT}{attr}")

                start = "\n".join([start, *attrs])

        if not node.children:
            if not node.attrs or len(node.attrs) <= 1:
                start = f"{start} />"
            else:
                start = f"{start}\n{depth * INDENT}/>"
        else:
            if not node.attrs or len(node.attrs) <= 1:
                start = f"{start}>"
            else:
                start = f"{start}\n{depth * INDENT}>"

        result.append(start)

    if hasattr(node, "children"):
        for child in node.children:
            result.extend(format_node(child, depth + 1))

        if node.children:
            result.append(f"{indent}</{node.tag}>")

    return result
