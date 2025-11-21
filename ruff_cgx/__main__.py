from pathlib import Path

from ruff_cgx import format_file
from ruff_cgx.linter import lint_file_data


def collect_files(paths):
    """Collect all CGX files from given paths."""
    files = []
    for path in paths:
        if not path.exists():
            continue

        if path.is_file():
            files.append(path)
        else:
            files.extend(path.glob("**/*.cgx"))

    return files


def format_diagnostic(diag, path):
    """Format a diagnostic message for display."""
    # Format: filename:line:col: CODE message
    return f"{path}:{diag.line + 1}:{diag.column + 1}: {diag.code} {diag.message}"


def run_check_command(args):
    """Run the check command with batch processing and summary output."""
    files = collect_files(args.path)

    if not files:
        print("No .cgx files found")  # noqa: T201
        return 0

    # Process all files
    results = []
    for file_path in files:
        result = lint_file_data(file_path, fix=args.fix)
        results.append(result)

    # Count results
    files_fixed = sum(1 for r in results if r["was_fixed"])
    files_with_errors = sum(1 for r in results if not r["success"])
    total_diagnostics = sum(len(r["diagnostics"]) for r in results)

    # Print diagnostics
    for result in results:
        if result["diagnostics"]:
            for diag in result["diagnostics"]:
                print(format_diagnostic(diag, result["path"]))  # noqa: T201

    # Print summary
    print()  # noqa: T201
    if args.fix:
        if files_fixed > 0:
            print(f"Fixed {files_fixed} file(s)")  # noqa: T201

    if total_diagnostics > 0:
        error_word = "error" if total_diagnostics == 1 else "errors"
        print(f"Found {total_diagnostics} {error_word}.")  # noqa: T201
        return 1
    else:
        if not args.fix:
            print(f"All checks passed! ({len(files)} file(s) checked)")  # noqa: T201
        else:
            print(f"All checks passed! ({len(files)} file(s) checked, {files_fixed} fixed)")  # noqa: T201
        return 0


def main(argv=None):
    import argparse
    import sys

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Lint and format cgx files with ruff",
        epilog="Environment: Set RUFF_COMMAND to use a custom ruff executable.",
    )
    subcommand = parser.add_subparsers(dest="command")

    lint_parser = subcommand.add_parser("check")
    lint_parser.add_argument(
        "--fix", action="store_true", help="Apply fixes to resolve lint violations"
    )
    lint_parser.add_argument(
        "path",
        nargs="*",
        type=Path,
        # default=[Path(".")],
        help="path(s) of files and/or folders to check",
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

    if args.command == "check":
        code = run_check_command(args)
    else:  # format
        method = format_file
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
