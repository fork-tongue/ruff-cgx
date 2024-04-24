[![PyPI version](https://badge.fury.io/py/ruff-cgx.svg)](https://badge.fury.io/py/ruff-cgx)
[![CI status](https://github.com/fork-tongue/ruff-cgx/workflows/CI/badge.svg)](https://github.com/fork-tongue/ruff-cgx/actions)
[![ruff](https://img.shields.io/badge/code%20style-ruff-ruff)](https://pypi.org/project/ruff/)

# Ruff-cgx

Lint and format CGX files (collagraph single-file components) with ruff.


## Usage

```sh
# Install in your environment (for example with poetry)
poetry add -D ruff-cgx
# Show help for the tool
poetry run ruff-cgx -h
# Check/Lint every cgx file in current folder (recursively)
poetry run ruff-cgx check .
# Format every cgx file in the current folder (recursively)
poetry run ruff-cgx format .
# Just check if there would be any changes from the formatter
poetry run ruff-cgx format --check .
# Format just a single file
poetry run ruff-cgx format my-component.cgx
# Format a folder and file
poetry run ruff-cgx format ../folder_with_cgx_files my-component.cgx
```
