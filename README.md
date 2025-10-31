[![PyPI version](https://badge.fury.io/py/ruff-cgx.svg)](https://badge.fury.io/py/ruff-cgx)
[![CI status](https://github.com/fork-tongue/ruff-cgx/workflows/CI/badge.svg)](https://github.com/fork-tongue/ruff-cgx/actions)
[![ruff](https://img.shields.io/badge/code%20style-ruff-ruff)](https://pypi.org/project/ruff/)

# Ruff-cgx

Lint and format CGX files (collagraph single-file components) with ruff.


## Usage

```sh
# Install in your environment (for example with uv)
uv add --dev ruff-cgx
# Show help for the tool
uv run ruff-cgx -h
# Check/Lint every cgx file in current folder (recursively)
uv run ruff-cgx check .
# Format every cgx file in the current folder (recursively)
uv run ruff-cgx format .
# Just check if there would be any changes from the formatter
uv run ruff-cgx format --check .
# Format just a single file
uv run ruff-cgx format my-component.cgx
# Format a folder and file
uv run ruff-cgx format ../folder_with_cgx_files my-component.cgx
```

## Configuration

To use a specific ruff installation (e.g., in an LSP server):

```python
import ruff_cgx

ruff_cgx.set_ruff_command("/path/to/custom/ruff")
```
