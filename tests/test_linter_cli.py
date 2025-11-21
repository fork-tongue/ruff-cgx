import pytest

from ruff_cgx.__main__ import main


def test_check_command(capsys, tmp_copy_from_data):
    simple_cgx = tmp_copy_from_data("lint.cgx")

    with pytest.raises(SystemExit) as e:
        main(["check", str(simple_cgx)])

    captured = capsys.readouterr()

    assert e.value.code == 1
    assert "lint.cgx:72:27" in captured.out
    assert "F401 `PySide6.QtGui.QAction` imported but unused" in captured.out
    assert "Found 1 error." in captured.out


def test_check_fixable_command(capsys, tmp_copy_from_data):
    simple_cgx = tmp_copy_from_data("simple.cgx")

    with pytest.raises(SystemExit) as e:
        main(["check", str(simple_cgx)])

    assert e.value.code == 1
    captured = capsys.readouterr()

    assert "I001 Import block is un-sorted or un-formatted" in captured.out
    assert "1 fixable with the `--fix` option." in captured.out


def test_check_fix_command(capsys, tmp_copy_from_data):
    simple_cgx = tmp_copy_from_data("simple.cgx")

    main(["check", "--fix", str(simple_cgx)])

    captured = capsys.readouterr()

    assert "Found 1 error (1 fixed, 0 remaining)." in captured.out
