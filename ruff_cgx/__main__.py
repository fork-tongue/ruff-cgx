from pathlib import Path

from ruff_cgx import format_file


def lint_file(path, fix=False):
    print("Lint", path, f"{fix:}")
    return 0


def main(argv=None):
    import argparse
    import sys

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Lint and format cgx files with ruff")
    subcommand = parser.add_subparsers(dest="command")

    lint_parser = subcommand.add_parser("lint")
    lint_parser.add_argument("--fix", action="store_true")
    lint_parser.add_argument(
        "path",
        nargs="*",
        type=Path,
        # default=[Path(".")],
        help="path(s) of files and/or folders to lint",
    )

    format_parser = subcommand.add_parser("format")
    format_parser.add_argument("--check", action="store_true")
    format_parser.add_argument(
        "path",
        nargs="*",
        type=Path,
        # default=[Path(".")],
        help="path(s) of files and/or folders to format",
    )

    args = parser.parse_args(argv)
    method = {
        "format": format_file,
        "lint": lint_file,
    }[args.command]

    method_arguments = {
        k: v for k, v in vars(args).items() if k not in {"command", "path"}
    }

    code = 0
    for path in args.path:
        if not path.exists():
            pass

        if path.is_file():
            code |= method(path, **method_arguments)
        else:
            for file in path.glob("**/*.cgx"):
                code |= method(file, **method_arguments)

    if code:
        exit(code)


if __name__ == "__main__":
    main()
