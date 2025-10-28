"""Tests for the formatter API."""

import textwrap

from ruff_cgx import format_cgx_content


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
