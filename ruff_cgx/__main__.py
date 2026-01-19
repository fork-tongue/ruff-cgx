from pathlib import Path

from ruff_cgx.formatter import format_file
from ruff_cgx.linter import lint_file


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
        print("No .cgx files found")
        return 0

    # Process all files
    results = [lint_file(file_path, fix=args.fix) for file_path in files]

    # Count results
    total_diagnostics_remaining = sum(len(r["diagnostics"]) for r in results)

    # Count fixable diagnostics (before fix) and total diagnostics before fix
    total_diagnostics_before = sum(len(r["diagnostics_before_fix"]) for r in results)
    total_fixable = sum(
        sum(1 for d in r["diagnostics_before_fix"] if d.fixable) for r in results
    )

    # Print diagnostics (remaining ones after fix, or all if not fixing)
    for result in results:
        if result["diagnostics"]:
            for diag in result["diagnostics"]:
                print(format_diagnostic(diag, result["path"]))

    # Empty line between diagnostics and summary
    if total_diagnostics_remaining > 0:
        print()

    # Print summary
    if args.fix:
        # Show "Found N error(s) (X fixed, Y remaining)."
        if total_diagnostics_before > 0:
            error_word = "error" if total_diagnostics_before == 1 else "errors"
            fixed_count = total_diagnostics_before - total_diagnostics_remaining
            print(
                f"Found {total_diagnostics_before} {error_word} ({fixed_count} fixed, "
                f"{total_diagnostics_remaining} remaining)."
            )
            return 1 if total_diagnostics_remaining > 0 else 0
        else:
            print(f"All checks passed! ({len(files)} file(s) checked)")
            return 0
    else:
        # Show "N fixable with the `--fix` option." or "Found N error(s)."
        if total_diagnostics_remaining > 0:
            if total_fixable > 0:
                print(f"{total_fixable} fixable with the `--fix` option.")
            else:
                error_word = "error" if total_diagnostics_remaining == 1 else "errors"
                print(f"Found {total_diagnostics_remaining} {error_word}.")
            return 1
        else:
            print(f"All checks passed! ({len(files)} file(s) checked)")
            return 0


def run_format_command(args):
    """Run the format command with batch processing and summary output."""
    files = collect_files(args.path)

    if not files:
        print("No .cgx files found")
        return 0

    # Process all files
    results = [format_file(file_path, check=args.check) for file_path in files]

    # Count results
    files_changed = sum(1 for r in results if r["changed"])
    files_unchanged = len(results) - files_changed

    # For --check mode, print which files would be reformatted
    if args.check:
        for result in results:
            if result["changed"]:
                print(f"Would reformat: {result['path']}")

    # Print summary
    if args.check:
        # --check mode summary
        if files_changed > 0:
            would_word = "file would" if files_changed == 1 else "files would"
            formatted_word = "file" if files_unchanged == 1 else "files"

            if files_unchanged > 0:
                print(
                    f"{files_changed} {would_word} be reformatted, "
                    f"{files_unchanged} {formatted_word} already formatted"
                )
            else:
                print(f"{files_changed} {would_word} be reformatted")
            return 1
        else:
            formatted_word = "file" if files_unchanged == 1 else "files"
            print(f"{files_unchanged} {formatted_word} already formatted")
            return 0
    else:
        # Normal format mode summary
        reformatted_word = "file" if files_changed == 1 else "files"
        unchanged_word = "file" if files_unchanged == 1 else "files"

        if files_changed > 0 and files_unchanged > 0:
            print(
                f"{files_changed} {reformatted_word} reformatted, "
                f"{files_unchanged} {unchanged_word} left unchanged"
            )
        elif files_changed > 0:
            print(f"{files_changed} {reformatted_word} reformatted")
        else:
            print(f"{files_unchanged} {unchanged_word} left unchanged")

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
        default=[Path(".")],
        help="path(s) of files and/or folders to check",
    )

    format_parser = subcommand.add_parser("format")
    format_parser.add_argument("--check", action="store_true")
    format_parser.add_argument(
        "path",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="path(s) of files and/or folders to format",
    )

    args = parser.parse_args(argv)

    match args.command:
        case "check":
            code = run_check_command(args)
        case "format":
            code = run_format_command(args)

    if code:
        exit(code)


if __name__ == "__main__":
    main()
