import shutil
from pathlib import Path

import pytest


@pytest.fixture
def data_path():
    return Path(__file__).parent / "data"


@pytest.fixture
def tmp_copy_from_data(data_path, tmp_path):
    def copy_temp_cgx(name):
        source = data_path / name
        target = tmp_path / name
        shutil.copyfile(source, target)
        return target

    return copy_temp_cgx
