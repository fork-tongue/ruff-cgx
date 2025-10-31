"""Tests for utility functions."""

import os

import pytest

from ruff_cgx import get_ruff_command, reset_ruff_command, set_ruff_command
from ruff_cgx.utils import run_ruff_check, run_ruff_format


@pytest.fixture(autouse=True)
def reset_config():
    """Reset ruff command configuration before and after each test."""
    reset_ruff_command()
    # Clear env var too
    original_env = os.environ.pop("RUFF_COMMAND", None)
    yield
    reset_ruff_command()
    if original_env is not None:
        os.environ["RUFF_COMMAND"] = original_env


def test_get_ruff_command_default():
    """Test that get_ruff_command returns default 'ruff' when not configured."""
    assert get_ruff_command() == "ruff"


def test_set_ruff_command():
    """Test setting ruff command programmatically."""
    set_ruff_command("/custom/path/to/ruff")
    assert get_ruff_command() == "/custom/path/to/ruff"


def test_reset_ruff_command():
    """Test resetting ruff command to default."""
    set_ruff_command("/custom/path/to/ruff")
    assert get_ruff_command() == "/custom/path/to/ruff"

    reset_ruff_command()
    assert get_ruff_command() == "ruff"


def test_priority_programmatic_over_env():
    """Test that programmatic setting takes priority over environment variable."""
    os.environ["RUFF_COMMAND"] = "/env/ruff"
    set_ruff_command("/programmatic/ruff")

    assert get_ruff_command() == "/programmatic/ruff"


def test_env_var_fallback():
    """Test that environment variable is used when programmatic setting not set."""
    os.environ["RUFF_COMMAND"] = "/env/ruff"
    # Don't call set_ruff_command

    assert get_ruff_command() == "/env/ruff"


def test_run_ruff_format_with_custom_command():
    """Test that run_ruff_format uses custom ruff command."""
    # Set to actual ruff command (we can't test with a fake one)
    set_ruff_command("ruff")
    source = "x=1+2"
    formatted = run_ruff_format(source)
    assert "x = 1 + 2" in formatted


def test_run_ruff_check_with_custom_command():
    """Test that run_ruff_check uses custom ruff command."""
    set_ruff_command("ruff")
    source = "import os\nx = 1"
    result, _ = run_ruff_check(source)
    # Should succeed (exit code 0 or 1 for lint issues)
    assert result.returncode in (0, 1)
