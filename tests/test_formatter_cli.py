import textwrap

import pytest

from ruff_cgx.__main__ import main


def test_check(capsys, tmp_copy_from_data):
    tmp_cgx = tmp_copy_from_data("simple.cgx")

    with pytest.raises(SystemExit) as e:
        main(["format", "--check", str(tmp_cgx)])

    stdout = capsys.readouterr().out

    assert e.value.code == 1
    assert "Would reformat" in stdout, stdout
    assert "simple.cgx" in stdout, stdout


def test_check_already_formatted(capsys, tmp_copy_from_data):
    tmp_cgx = tmp_copy_from_data("simple_formatted.cgx")

    main(["format", "--check", str(tmp_cgx)])

    stdout = capsys.readouterr().out

    assert "Would reformat" not in stdout, stdout
    assert "simple.cgx" not in stdout, stdout
    assert "1 file already formatted" in stdout, stdout


def test_format_template(capsys, tmp_copy_from_data):
    tmp_cgx = tmp_copy_from_data("template.cgx")

    main(["format", str(tmp_cgx)])

    stdout = capsys.readouterr().out
    formatted = tmp_cgx.read_text()

    expected = textwrap.dedent(
        """\
            <template>
              <root>
                <item
                  attributes="2"
                  multple="1"
                />
                <item @single="'attr'" />
                <blaat
                  :attr="10"
                  attribute
                  blaat="True"
                  @example="hai"
                />
                <nested #header>
                  <attrs
                    key0="blasd"
                    :key1="'asdf'"
                    key2="asdf"
                    key3="fda"
                  />
                  <!-- A comment here -->
                  <subitem />
                  <!--

              multiline comment
            weird
                indents

            -->
                  <subitem id="2" />
                  <!-- <another />
                 multiline
            comment
               -->
                </nested>
                <!-- same line -->
                <item
                  v-if="condition"
                  :attr="'val'"
                  something
                  @action="callback"
                />
                <toet v-else>
                  <!-- Some comment here -->
                </toet>
                <item v-slot:footer>
                  With text content
                  <!--toet -->
                  bloeb
                </item>
              </root>
            </template>

            <script>
            from collagraph import Component


            class Simple(Component):
                pass
            </script>
        """
    )
    assert formatted == expected
    assert "1 file reformatted" in stdout, stdout


def test_works_with_no_template(capsys, tmp_copy_from_data):
    """
    Also checks that a newline will be added at the end
    of the file.
    """
    tmp_cgx = tmp_copy_from_data("no_template.cgx")

    main(["format", str(tmp_cgx)])

    stdout = capsys.readouterr().out
    formatted = tmp_cgx.read_text()

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
    assert "1 file reformatted" in stdout, stdout


def test_works_with_no_template_elaborate(capsys, tmp_copy_from_data):
    """
    Also checks that whitespace between root nodes is preserved.
    """
    tmp_cgx = tmp_copy_from_data("no_template_elaborate.cgx")

    main(["format", str(tmp_cgx)])

    stdout = capsys.readouterr().out
    formatted = tmp_cgx.read_text()

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
    assert "1 file reformatted" in stdout, stdout
