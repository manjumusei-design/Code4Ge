"""CLI argument parsing and subcommand handlers for CommitForge."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from commitforge import __version__
from commitforge.config import load_config, validate_config, write_default_config
from commitforge.generator import generate_commit_suggestion
from commitforge.parser import detect_repo_root, parse_diff_working
from commitforge.report import (
    FORMAT_HTML,
    FORMAT_MARKDOWN,
    FORMAT_TERMINAL,
    print_terminal,
    render_html,
    render_markdown,
    write_report,
)
from commitforge.scanner import scan_repo

logger = logging.getLogger("commitforge")


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="commitforge",
        description="Offline CLI for semantic commit suggestions and repo health checks.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--repo", type=Path, default=None, help="Path to Git repository (default: auto-detect)"
    )

    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # init
    sub.add_parser("init", help="Create a default .commitforge.json")

    # scan
    sub.add_parser("scan", help="Analyse working tree and suggest a commit message")

    # health
    health_p = sub.add_parser("health", help="Scan repo for code-health issues")
    health_p.add_argument(
        "--format",
        choices=[FORMAT_TERMINAL, FORMAT_MARKDOWN, FORMAT_HTML],
        default=FORMAT_TERMINAL,
        help="Output format (default: terminal)",
    )
    health_p.add_argument(
        "--output", type=Path, default=None, help="Write report to file (e.g. report.html)"
    )

    # report (alias for health with file output)
    report_p = sub.add_parser("report", help="Generate a Markdown/HTML report (alias for health --output)")
    report_p.add_argument(
        "--output", type=Path, default=Path("commitforge_report.html"),
        help="Report output path (default: commitforge_report.html)",
    )
    report_p.add_argument(
        "--format",
        choices=[FORMAT_TERMINAL, FORMAT_MARKDOWN, FORMAT_HTML],
        default=None,
        help="Format (auto-detected from --output extension if omitted)",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the CommitForge CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "init":
        return _cmd_init(args)
    if args.command == "scan":
        return _cmd_scan(args)
    if args.command == "health":
        return _cmd_health(args)
    if args.command == "report":
        return _cmd_report(args)

    parser.print_help()
    return 1


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def _cmd_init(args: argparse.Namespace) -> int:
    """Handle `commitforge init`."""
    repo_root = _resolve_repo(args.repo)
    if repo_root is None:
        logger.error("Not inside a Git repository. Run `git init` first.")
        return 1

    path = write_default_config(repo_root)
    warnings = validate_config(load_config(repo_root))
    for w in warnings:
        logger.warning(w)

    print(f"Config created: {path}")
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    """Handle `commitforge scan`."""
    repo_root = _resolve_repo(args.repo)
    if repo_root is None:
        logger.error("Not inside a Git repository.")
        return 1

    cfg = load_config(repo_root)
    diff_result = parse_diff_working(repo_root)

    if diff_result.error:
        logger.warning("Diff encountered issues: %s", diff_result.error)

    if not diff_result.files:
        print("No changes detected in the working tree.")
        return 0

    print_terminal(diff_result)
    return 0


def _cmd_health(args: argparse.Namespace) -> int:
    """Handle `commitforge health`."""
    repo_root = _resolve_repo(args.repo)
    if repo_root is None:
        logger.error("Not inside a Git repository.")
        return 1

    cfg = load_config(repo_root)
    diff_result = parse_diff_working(repo_root)
    scan_result = scan_repo(
        repo_root,
        ignored_paths=cfg.get("ignored_paths", []),
        max_file_size_kb=cfg.get("max_file_size_kb", 500),
    )

    fmt = getattr(args, "format", FORMAT_TERMINAL)
    output_path: Path | None = getattr(args, "output", None)

    if output_path:
        write_report(diff_result, output_path, scan_result)
        print(f"Report written to {output_path}")
    else:
        print_terminal(diff_result, scan_result)

    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Handle `commitforge report`."""
    repo_root = _resolve_repo(args.repo)
    if repo_root is None:
        logger.error("Not inside a Git repository.")
        return 1

    cfg = load_config(repo_root)
    diff_result = parse_diff_working(repo_root)
    scan_result = scan_repo(
        repo_root,
        ignored_paths=cfg.get("ignored_paths", []),
        max_file_size_kb=cfg.get("max_file_size_kb", 500),
    )

    output_path = args.output
    fmt = getattr(args, "format", None)

    # Auto-detect format from extension when not specified
    if fmt is None:
        ext = output_path.suffix.lower()
        fmt_map = {".md": FORMAT_MARKDOWN, ".html": FORMAT_HTML, ".htm": FORMAT_HTML}
        fmt = fmt_map.get(ext, FORMAT_MARKDOWN)

    if fmt == FORMAT_HTML:
        content = render_html(diff_result, scan_result)
    else:
        content = render_markdown(diff_result, scan_result)

    output_path.write_text(content, encoding="utf-8")
    print(f"Report written to {output_path}")
    return 0


#Helpers
def _resolve_repo(explicit: Path | None) -> Path | None:
    """Return the repository root Path or None if not a git repo."""
    if explicit:
        resolved = explicit.resolve() if explicit.is_dir() else explicit.parent.resolve()
        # Verify it's actually a git repo
        if (resolved / ".git").exists():
            return resolved
        return None
    return detect_repo_root(Path.cwd())


def _setup_logging(verbose: bool) -> None:
    """Configure root logger based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
