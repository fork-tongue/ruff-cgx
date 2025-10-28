"""Tests for the formatter API."""

from ruff_cgx.template_formatter import (
    format_attribute,
    format_python_expression,
    sort_attr,
)


def test_sort_attr_unique():
    """Test attribute sorting for unique attributes."""
    # UNIQUE attributes (id, ref, key) should come early
    assert sort_attr("id").startswith("3")
    assert sort_attr("ref").startswith("3")
    assert sort_attr("key").startswith("3")


def test_sort_attr_conditionals():
    """Test attribute sorting for conditional directives."""
    # CONDITIONALS should come early
    assert sort_attr("v-if").startswith("2")
    assert sort_attr("v-else-if").startswith("2")
    assert sort_attr("v-else").startswith("2")


def test_sort_attr_events():
    """Test attribute sorting for event handlers."""
    # EVENTS should come later
    assert sort_attr("@click").startswith("6")
    assert sort_attr("v-on").startswith("6")


def test_sort_attr_bindings():
    """Test attribute sorting for bindings."""
    # OTHER_ATTR (bindings) should be in the middle
    assert sort_attr(":prop").startswith("5")
    assert sort_attr("v-bind").startswith("5")


def test_sort_attr_regular():
    """Test attribute sorting for regular attributes."""
    # Regular attributes should go in OTHER_ATTR category
    assert sort_attr("class").startswith("5")
    assert sort_attr("disabled").startswith("5")


def test_format_attribute_boolean():
    """Test formatting of boolean attributes."""
    assert format_attribute("disabled", True) == "disabled"


def test_format_attribute_string():
    """Test formatting of string attributes."""
    assert format_attribute("class", "my-class") == 'class="my-class"'


def test_format_attribute_binding():
    """Test formatting of binding attributes."""
    assert format_attribute(":value", "myValue") == ':value="myValue"'


def test_format_attribute_event():
    """Test formatting of event attributes."""
    assert format_attribute("@click", "handleClick") == '@click="handleClick"'


def test_format_python_expression_simple():
    """Test formatting of simple Python expressions."""
    # Simple expression
    assert format_python_expression("x+y") == "x + y"
    assert format_python_expression("a  *  b") == "a * b"


def test_format_python_expression_dict():
    """Test formatting of dictionary expressions."""
    expr = "{'type':'box','direction':QBoxLayout.Direction.LeftToRight}"
    # Ruff should use single quotes (configured for expressions)
    expected = "{'type': 'box', 'direction': QBoxLayout.Direction.LeftToRight}"
    assert format_python_expression(expr) == expected


def test_format_python_expression_list():
    """Test formatting of list expressions."""
    expr = "[1,2,3,4]"
    expected = "[1, 2, 3, 4]"
    assert format_python_expression(expr) == expected


def test_format_python_expression_comparison():
    """Test formatting of comparison expressions."""
    # Ruff should use single quotes (configured for expressions)
    assert format_python_expression("state['counter']==0") == "state['counter'] == 0"


def test_format_python_expression_function_call():
    """Test formatting of function call expressions."""
    expr = "counter_format(  )"
    expected = "counter_format()"
    assert format_python_expression(expr) == expected


def test_format_python_expression_empty():
    """Test formatting of empty or whitespace-only expressions."""
    assert format_python_expression("") == ""
    assert format_python_expression("   ") == "   "


def test_format_attribute_with_expression():
    """Test that attribute formatting includes expression formatting."""
    # Binding attribute with expression
    result = format_attribute(":text", "x+y")
    assert result == ':text="x + y"'

    # Event attribute with expression
    result = format_attribute("@click", "handle(  )")
    assert result == '@click="handle()"'

    # v-if directive with expression
    result = format_attribute("v-if", "counter==0")
    assert result == 'v-if="counter == 0"'

    # v-for directive with expression
    result = format_attribute("v-for", " it  in  enumerate( items, start = 0 ) ")
    assert result == 'v-for="it in enumerate(items, start=0)"'
