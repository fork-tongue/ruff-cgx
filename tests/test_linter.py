import pytest

from ruff_cgx.__main__ import main


def test_check_command(capsys, data_path):
    simple_cgx = data_path / "lint.cgx"

    with pytest.raises(SystemExit) as e:
        main(["check", str(simple_cgx)])

    captured = capsys.readouterr()

    assert "tests/data/lint.cgx" in captured.out
    assert "F401" in captured.out
    assert "`PySide6.QtGui.QAction` imported but unused" in captured.out
    assert "Found 1 error." in captured.out
    assert len(captured.out.splitlines()) == 2, captured.out
