import logging
import textwrap

from collagraph.sfc.parser import Comment, TextElement

from .utils import run_ruff_format

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


def collect_expressions(node) -> list[str]:
    """
    Collect all Python expressions from a template node tree.

    Returns a list of expressions that need formatting.
    """
    expressions = []

    def _collect_from_node(n):
        # Skip text and comments
        if isinstance(n, (Comment, TextElement)):
            return

        # Collect expressions from attributes
        if attributes := getattr(n, "attrs", None):
            for key, value in attributes.items():
                if (
                    key.startswith((":", "@", "v-"))
                    and isinstance(value, str)
                    and value.strip()
                ):
                    if key.startswith("v-for"):
                        # Split v-for into target and iterable
                        expr = value.strip()
                        parts = expr.split(" in ", 1)
                        if len(parts) == 2:
                            expressions.append(parts[0].strip())
                            expressions.append(parts[1].strip())
                    else:
                        expressions.append(value.strip())

        # Recurse into children
        if children := getattr(n, "children", None):
            for child in children:
                _collect_from_node(child)

    _collect_from_node(node)
    return expressions


def batch_format_expressions(expressions: list[str]) -> dict[str, str]:
    """
    Format multiple Python expressions in a single ruff call.

    Args:
        expressions: List of Python expressions to format

    Returns:
        Dictionary mapping original expression to formatted expression
    """
    if not expressions:
        return {}

    # Filter out empty expressions
    non_empty = [e for e in expressions if e and e.strip()]
    if not non_empty:
        return {}

    try:
        # Create a batch of assignments
        lines = [f"__e{i}__ = {expr}" for i, expr in enumerate(non_empty)]
        batch_source = "\n".join(lines)

        # Format all at once
        formatted_batch = run_ruff_format(
            batch_source, use_single_quotes=True, skip_import_sort=True
        )

        # Parse the results - need to handle multiline expressions
        result_map = {}
        formatted_lines = formatted_batch.strip().split("\n")
        formatted_lines_count = len(formatted_lines)

        for i, expr in enumerate(non_empty):
            # Find the formatted expression for this variable
            prefix = f"__e{i}__ = "

            # Find the start line
            start_idx = None
            for idx, line in enumerate(formatted_lines):
                if line.startswith(prefix):
                    start_idx = idx
                    break

            if start_idx is None:
                continue

            # Find the end line: next line that starts with __e (next assignment)
            end_idx = formatted_lines_count
            for idx in range(start_idx + 1, formatted_lines_count):
                line = formatted_lines[idx]
                if line.startswith("__e") and " = " in line:
                    end_idx = idx
                    break

            # Extract the expression (everything after "variable = ")
            first_line = formatted_lines[start_idx][len(prefix) :]
            if start_idx + 1 < end_idx:
                # Multiline expression
                remaining_lines = formatted_lines[start_idx + 1 : end_idx]
                formatted_expr = first_line + "\n" + "\n".join(remaining_lines)
            else:
                # Single line expression
                formatted_expr = first_line

            result_map[expr] = formatted_expr

        return result_map

    except Exception as e:
        logger.debug(f"Batch formatting failed: {e}")
        # Return empty dict - will fall back to individual formatting
        return {}


def format_python_expression(
    expr: str, expression_cache: dict[str, str] | None = None
) -> str:
    """
    Format a Python expression using ruff with single quotes.

    Args:
        expr: The Python expression as a string
        expression_cache: Optional cache of pre-formatted expressions

    Returns:
        Formatted expression as a string (using single quotes)
    """
    if not expr or not expr.strip():
        return expr

    # Check cache first
    if expression_cache is not None and expr in expression_cache:
        return expression_cache[expr]

    try:
        prefix = "__dummy__ = "
        # Wrap the expression in a dummy assignment to make it valid Python
        # This allows ruff to format it properly
        wrapped = f"{prefix}{expr}"

        # Format with ruff using single quotes
        # Skip import sorting since template expressions don't have imports
        formatted = run_ruff_format(
            wrapped, use_single_quotes=True, skip_import_sort=True
        )

        # Extract the expression back out
        # (remove "__dummy__ = " and trailing newline)
        if formatted.startswith(prefix):
            formatted_expr = formatted[len(prefix) :].rstrip("\n")
            return formatted_expr

        # If formatting failed, return original
        return expr

    except Exception as e:
        logger.debug(f"Could not format expression '{expr}': {e}")
        return expr


def format_list_expression(
    expr: str, expression_cache: dict[str, str] | None = None
) -> str:
    """
    Format a Python list expression (v-for syntax) using ruff with single quotes.

    The v-for syntax is: "item in items" or "(item, index) in items"
    We need to format both the target and iterable parts separately.

    Args:
        expr: The list expression as a string (e.g., "item in items")
        expression_cache: Optional cache of pre-formatted expressions

    Returns:
        Formatted expression as a string (using single quotes)
    """
    if not expr or not expr.strip():
        return expr

    try:
        expr = expr.strip()

        # Split on ' in ' to separate target from iterable
        # We use the first occurrence to handle cases where
        # 'in' might appear in the iterable
        parts = expr.split(" in ", 1)

        if len(parts) != 2:
            # If no ' in ' found, return as-is (malformed v-for expression)
            return expr

        target, iterable = parts

        # Format each part using format_python_expression
        formatted_target = format_python_expression(target.strip(), expression_cache)
        formatted_iterable = format_python_expression(
            iterable.strip(), expression_cache
        )

        return f"{formatted_target} in {formatted_iterable}"

    except Exception as e:
        logger.debug(f"Could not format list expression '{expr}': {e}")
        return expr


def format_template(template_node) -> tuple[list[str], tuple[int, int]]:
    """
    Returns formatted node and the original location of the template node.

    Uses batch formatting for all Python expressions to improve performance.
    """
    # Find beginning of the node (0-indexed)
    start = template_node.location[0] - 1

    # Comment and TextElement nodes don't have an 'end' attribute
    # For these, we compute the end from the content by counting newlines
    if not hasattr(template_node, "end"):
        # Count newlines in content to determine end line
        newline_count = template_node.content.count("\n")
        end = start + newline_count + 1
    else:
        end = template_node.end[0]

    # Collect all expressions and batch format them
    expressions = collect_expressions(template_node)
    expression_cache = batch_format_expressions(expressions) if expressions else None

    # Format the node tree using the cached expressions
    result = format_node(template_node, depth=0, expression_cache=expression_cache)

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


def format_attribute(
    key, value, indent="", single_attribute=True, expression_cache=None
):
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
        if key.startswith("v-for"):
            formatted_value = format_list_expression(value, expression_cache)
            return f'{key}="{formatted_value}"'
        else:
            formatted_value = format_python_expression(value, expression_cache)
            formatted_value = textwrap.indent(
                formatted_value, indent + ("" if single_attribute else INDENT)
            ).lstrip()
            return f'{key}="{formatted_value}"'

    return f'{key}="{value}"'


def format_node(node, depth: int, expression_cache=None) -> list[str]:
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
                attr = format_attribute(
                    key,
                    val,
                    indent,
                    single_attribute=True,
                    expression_cache=expression_cache,
                )
                start = f"{start} {attr}"
            else:
                attrs = []
                for key in sorted(node.attrs, key=sort_attr):
                    attr = format_attribute(
                        key,
                        node.attrs[key],
                        indent,
                        single_attribute=False,
                        expression_cache=expression_cache,
                    )
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
            result.extend(format_node(child, depth + 1, expression_cache))

        if node.children:
            result.append(f"{indent}</{node.tag}>")

    return result
