import textwrap

import pytest

from ruff_cgx import format_file
from ruff_cgx.__main__ import main


def test_check(capsys, data_path):
    simple_cgx = data_path / "simple.cgx"

    with pytest.raises(SystemExit) as e:
        main(["format", "--check", str(simple_cgx)])

    stdout = capsys.readouterr().out

    assert e.value.code == 1
    assert "Would reformat" in stdout, stdout
    assert "simple.cgx" in stdout, stdout


def test_check_already_formatted(capsys, data_path):
    simple_cgx = data_path / "simple_formatted.cgx"

    main(["format", "--check", str(simple_cgx)])

    stdout = capsys.readouterr().out

    assert "Would reformat" not in stdout, stdout
    assert "simple.cgx" not in stdout, stdout
    assert "1 file already formatted" in stdout, stdout


def test_format_template(capsys, data_path):
    template_cgx = data_path / "template.cgx"

    lines = format_file(template_cgx, write=False)

    expected = textwrap.dedent(
        """
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
                <nested>
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
                <item>
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
    ).lstrip()
    assert "".join(lines) == expected

    stdout = capsys.readouterr().out

    assert "1 file reformatted" in stdout, stdout
