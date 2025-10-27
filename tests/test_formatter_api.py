"""Tests for the formatter API."""

import textwrap

from ruff_cgx import (
    format_cgx_content,
)
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


def test_format_simple_cgx():
    """Test formatting of a simple CGX file."""
    content = textwrap.dedent(
        """
        <template>
          <item />
        </template>

        <script>
        from collagraph import   (Component,)
        class   Simple( Component  ):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <template>
          <item />
        </template>

        <script>
        from collagraph import (
            Component,
        )


        class Simple(Component):
            pass
        </script>
        """
    ).lstrip()

    assert formatted == expected


def test_format_template_with_attributes():
    """Test formatting of template with multiple attributes."""
    content = textwrap.dedent(
        """
        <template>
          <item @click="handleClick" :value="myValue" disabled class="my-class" />
            </template>

        <script>
        from collagraph import Component

        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <template>
          <item
            class="my-class"
            disabled
            :value="myValue"
            @click="handleClick"
          />
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    # Attributes should be sorted:
    # - class (regular)
    # - disabled (regular boolean)
    # - :value (binding)
    # - @click (event)
    assert formatted == expected


def test_format_nested_template():
    """Test formatting of nested template elements."""
    content = textwrap.dedent(
        """
        <template>
          <root><child><nested /></child>
            </root>
                </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <template>
          <root>
            <child>
              <nested />
            </child>
          </root>
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    assert formatted == expected


def test_format_with_comments():
    """Test formatting preserves comments in template."""
    content = textwrap.dedent(
        """
        <template>
                <!-- This is a comment -->
              <item />


        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <template>
          <!-- This is a comment -->
          <item />
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    assert formatted == expected


def test_format_already_formatted():
    """Test that formatting already formatted content is idempotent."""
    content = textwrap.dedent(
        """
        <template>
          <item />
        </template>

        <script>
        from collagraph import Component


        class Simple(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted_once = format_cgx_content(content)
    formatted_twice = format_cgx_content(formatted_once)

    # Formatting should be idempotent
    assert formatted_once == formatted_twice


def test_format_with_text_content():
    """Test formatting elements with text content."""
    content = textwrap.dedent(
        """
        <template>
          <div>Some text content</div>
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <template>
          <div>
            Some text content
          </div>
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    assert formatted == expected


def test_format_invalid_content():
    """Test that formatting invalid content returns original content."""
    # Content without proper script/template tags
    content = "This is not valid CGX content"

    formatted = format_cgx_content(content)

    # Should return original content on error
    assert formatted == content


def test_format_multiline_attributes():
    """Test formatting elements with many attributes (should be multiline)."""
    content = textwrap.dedent(
        """
        <template>
          <item attr1="val1" attr2="val2" attr3="val3" attr4="val4" />
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    expected_format = textwrap.dedent(
        """
        <template>
          <item
            attr1="val1"
            attr2="val2"
            attr3="val3"
            attr4="val4"
          />
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    # Multiple attributes should be formatted
    # (specific format depends on implementation)
    assert formatted == expected_format


def test_format_no_template_tag():
    """
    Test formatting cgx files without a root template tag.
    Also checks that a newline will be added at the end of the file.
    """
    content = textwrap.dedent(
        """
        <node />

        <script>
        from collagraph import Component
        class Node(Component):
        	pass
        </script>"""
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <node />

        <script>
        from collagraph import Component


        class Node(Component):
            pass
        </script>
        """
    ).lstrip()

    assert formatted == expected


def test_format_no_template_elaborate():
    """
    Test formatting cgx files with multiple root nodes (no template tag).
    Also checks that whitespace between root nodes is preserved.
    """
    content = textwrap.dedent(
        """
        <node />




        <script>
        from collagraph import Component
        class Node(Component):
        	pass
        </script>



        <other-node>


        	<should-work-just-fine />
        		</other-node>"""
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <node />




        <script>
        from collagraph import Component


        class Node(Component):
            pass
        </script>



        <other-node>
          <should-work-just-fine />
        </other-node>

        """
    ).lstrip()

    assert formatted == expected


def test_format_cgx_with_expressions():
    """Test formatting of a complete CGX file with Python expressions in template."""
    content = textwrap.dedent(
        """
        <template>
          <label :text="state['counter']+1" />
          <button @clicked="bump(  )" />
          <widget :layout="{'type':'box'}" />
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    # Ruff should use single quotes for expressions
    # to avoid escaping in HTML attributes
    expected = textwrap.dedent(
        """
        <template>
          <label :text="state['counter'] + 1" />
          <button @clicked="bump()" />
          <widget :layout="{'type': 'box'}" />
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    assert formatted == expected


def test_format_cgx_multiline_with_expressions():
    """Test formatting with multiple attributes including expressions."""
    content = textwrap.dedent(
        """
        <template>
          <item @click="handleClick()" :value="myValue+1" disabled class="my-class" />
        </template>

        <script>
        from collagraph import Component

        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    formatted = format_cgx_content(content)

    expected = textwrap.dedent(
        """
        <template>
          <item
            class="my-class"
            disabled
            :value="myValue + 1"
            @click="handleClick()"
          />
        </template>

        <script>
        from collagraph import Component


        class Test(Component):
            pass
        </script>
        """
    ).lstrip()

    assert formatted == expected
