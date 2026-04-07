"""CLI entry point with subcommand routing for CommitForge."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

logger = logging.getLogger(__name__)
FMT_CHOICES = ("text", "md", "html")


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser with all subcommands and global flags."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--format", choices=FMT_CHOICES, default="text",
                        help="Output format (default: text)")
    parent.add_argument("--since", type=str, default=None,
                        help="Analyse commits since ISO date")
    parent.add_argument("--author", type=str, default=None,
                        help="Filter commits by author")
    parent.add_argument("--ignore", action="append", default=[],
                        help="Ignore glob pattern (repeatable)")
    parent.add_argument("--no-cache", action="store_true",
                        help="Disable any caching")
    
    parser = argparse.ArgumentParser(
        prog="commitforge",
        description="Offline Git repo analyzer & conventional commit generator.",
    )
    parser.add_argument("-V", "--version", action="version",
                        version="%(prog)s 1.0.0")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress non-essential output")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write report to file")
    parser.add_argument("--repo", type=Path, default=None,
                        help="Path to Git repository root")

    parent.add_argument("--quiet", action="store_true",
                        help="Suppress non-essential output")

    subs = parser.add_subparsers(dest="command", help="Available subcommands")
    subs.add_parser("init", parents=[parent], help="Create .commitforge.json")
    subs.add_parser("scan", parents=[parent], help="Suggest commit message")
    subs.add_parser("health", parents=[parent], help="Scan code health")
    subs.add_parser("report", parents=[parent], help="Generate MD/HTML report")
    subs.add_parser("analyze", parents=[parent], help="Full analysis pipeline")
    return parser



def _setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure the root logger based on verbosity flag."""
    if quiet:
        level = logging.CRITICAL
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level,
                        format="%(levelname)s: %(message)s",
                        stream=sys.stderr)


def _resolve_repo(explicit: Optional[Path]) -> Optional[Path]:
    """Return a path to the git repo root or None if not found."""
    from commitforge.utils import detect_repo_root
    if explicit and explicit.is_dir():
        return explicit.resolve() if (explicit / ".git").exists() else None
    if explicit:
        resolved = explicit.parent.resolve()
        return resolved if (resolved / ".git").exists() else None
    return detect_repo_root(Path.cwd())


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse arguments, dispatch to subcommand, return exit code."""
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    _setup_logging(args.verbose, args.quiet)

    dispatch = {
        "init": _cmd_init,
        "scan": _cmd_scan,
        "health": _cmd_health,
        "report": _cmd_report,
        "analyze": _cmd_analyze,
    }
    fn = dispatch.get(getattr(args, "command", None))
    if fn is None:
        build_parser().print_help()
        return 0
    try:
        return fn(args)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return 130
    
    
def _cmd_init(args: argparse.Namespace) -> int: 
    """Handle the init subcommand"""
    repo = _resolve_repo(getattr(args, "repo", None))
    if repo is None:
        logger.error("Not inside a git repo, you need to run 'git init' first")
        return 1
    logger.info("Config created at %s", repo / ".commitforge.json")
    if not args.quiet:
        print("Config created: {}".format(repo / ".commitforge.json"))
    return 0
    
    
def _cmd_scan(args: argparse.Namespace) -> int:
    """Handle the scan subcommand."""
    from commitforge.config import load_config
    from commitforge.parser import parse_diff
    from commitforge.generator import suggest_commit

    repo = _resolve_repo(getattr(args, "repo", None))
    if repo is None:
        logger.error("Not inside a git repo; run 'git init' first.")
        return 1
    config = load_config(repo)
    filters = {"since": args.since, "author": args.author, "ignore": args.ignore}
    diff = parse_diff(repo, filters)
    commit = suggest_commit(diff, config)
    if not args.quiet:
        print("Branch: {}".format(diff.branch or "working-tree"))
        print("Files changed: {}".format(len(diff.files)))
        print("Suggested: {}({}): {}".format(
            commit["type"], commit["scope"], commit["summary"]))
        if commit.get("body"):
            print(commit["body"])
    return 0
    
    
def _cmd_health(args: argparse.Namespace) -> int:
    """Handle the health subcommand."""
    from commitforge.config import load_config
    from commitforge.scanner import (
        scan_large_files, scan_binaries, scan_todos_fixmes,
        scan_missing_docstrings, scan_unused_imports,
    )
    from commitforge.report import render_terminal, write_output

    repo = _resolve_repo(getattr(args, "repo", None))
    if repo is None:
        logger.error("Not inside a git repo; run 'git init' first.")
        return 1
    config = load_config(repo)
    ignores = config.ignore_paths
    all_issues = []
    all_issues.extend(scan_large_files(repo, config))
    all_issues.extend(scan_binaries(repo, ignores))
    all_issues.extend(scan_todos_fixmes(repo, ignores))
    all_issues.extend(scan_missing_docstrings(repo, ignores))
    all_issues.extend(scan_unused_imports(repo, ignores))
    fmt = getattr(args, "format", "text")
    commit_stub = {"type": "health", "scope": "repo", "summary": "Health check", "body": ""}
    if fmt == "md":
        from commitforge.report import render_markdown
        content = render_markdown(commit_stub, all_issues)
    elif fmt == "html":
        from commitforge.report import render_html
        content = render_html(commit_stub, all_issues)
    else:
        render_terminal(commit_stub, all_issues)
        content = ""
    if content and args.output:
        write_output(content, args.output)
    return 0
    
    
def _cmd_report(args: argparse.Namespace) -> int:
    """Handle the report subcommand."""
    from commitforge.config import load_config
    from commitforge.parser import parse_diff
    from commitforge.generator import suggest_commit
    from commitforge.report import render_markdown, render_html, write_output

    repo = _resolve_repo(getattr(args, "repo", None))
    if repo is None:
        logger.error("Not inside a git repository.")
        return 1
    config = load_config(repo)
    filters = {"since": args.since, "author": args.author, "ignore": args.ignore}
    diff = parse_diff(repo, filters)
    commit = suggest_commit(diff, config)
    fmt = getattr(args, "format", "text")
    if fmt == "md":
        content = render_markdown(commit, [])
    elif fmt == "html":
        content = render_html(commit, [])
    else:
        from commitforge.report import render_terminal
        render_terminal(commit, [])
        content = ""
    if content:
        write_output(content, args.output)
    return 0
    
    
def _cmd_analyze(args: argparse.Namespace) -> int:
    """Handle the analyze subcommand (full pipeline)."""
    from commitforge.config import load_config
    from commitforge.parser import parse_diff
    from commitforge.generator import suggest_commit
    from commitforge.scanner import (
        scan_large_files, scan_binaries, scan_todos_fixmes,
        scan_missing_docstrings, scan_unused_imports,
    )
    from commitforge.report import render_terminal, render_markdown, render_html, write_output

    repo = _resolve_repo(getattr(args, "repo", None))
    if repo is None:
        logger.error("Not inside a git repo.")
        return 1
    config = load_config(repo)
    filters = {"since": args.since, "author": args.author, "ignore": args.ignore}
    diff = parse_diff(repo, filters)
    commit = suggest_commit(diff, config)
    ignores = config.ignore_paths
    issues = []
    issues.extend(scan_large_files(repo, config))
    issues.extend(scan_binaries(repo, ignores))
    issues.extend(scan_todos_fixmes(repo, ignores))
    issues.extend(scan_missing_docstrings(repo, ignores))
    issues.extend(scan_unused_imports(repo, ignores))
    fmt = getattr(args, "format", "text")
    if fmt == "md":
        content = render_markdown(commit, issues)
    elif fmt == "html":
        content = render_html(commit, issues)
    else:
        render_terminal(commit, issues)
        content = ""
    if content:
        write_output(content, args.output)
    return 0