from pathlib import Path
import textwrap

import pytest

from black_cgx import main, format_file


DATA_PATH = Path(__file__).parent / "data"


def test_check(caplog):
    simple_cgx = DATA_PATH / "simple.cgx"

    with pytest.raises(SystemExit) as e:
        main(["--check", str(simple_cgx)])

    assert e.value.code == 1
    assert "Would change" in caplog.text
    assert "simple.cgx" in caplog.text


def test_check_already_formatted(caplog):
    simple_cgx = DATA_PATH / "simple_formatted.cgx"

    main(["--check", str(simple_cgx)])

    assert "Would change" not in caplog.text
    assert "simple.cgx" not in caplog.text
    assert caplog.text == ""


def test_format_template(caplog):
    template_cgx = DATA_PATH / "template.cgx"

    lines = format_file(template_cgx, write=False)

    expected = textwrap.dedent(
        """
            <template>
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
            </template>

            <script>
            from collagraph import Component


            class Simple(Component):
                pass
            </script>
        """
    ).lstrip()
    assert "".join(lines) == expected
