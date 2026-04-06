"""CLI entry point with a subcommand routing for CommitForge."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from commitforge import __version__
from commitforge.config import load_config, write_default_config
from commitforge.generator import format_commit, generate_commit_suggestion
from commitforge.parser import detect_repo_root, parse_diff_since, parse_diff_working
from commitforge.report import (
    FORMAT_HTML,
    FORMAT_MARKDOWN,
    FORMAT_TERMINAL,
    render_html,
    render_markdown,
    render_terminal,
    write_report,
)
from commitforge.scanner import run_all_scans

logger = logging.getLogger(__name__)
FMT_CHOICES = (FORMAT_TERMINAL, FORMAT_MARKDOWN, FORMAT_HTML)


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser with all subcommands and flags."""
    # Shared parent flags available to every subcommand
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--since", type=str, default=None, help="Only analyse commits since DATE")
    parent.add_argument("--author", type=str, default=None, help="Filter by author email/name")
    parent.add_argument("--ignore", action="append", default=[], help="Ignore glob pattern (repeatable)")
    parent.add_argument("--no-cache", action="store_true", help="Disable any caching (future-proof)")

    p = argparse.ArgumentParser(
        prog="commitforge",
        description="Offline Git repo analyzer & conventional commit generator.",
    )
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential output")
    p.add_argument("--repo", type=Path, default=None, help="Path to Git repository")
    s = p.add_subparsers(dest="command", help="Available commands")
    s.add_parser("init", parents=[parent], help="Create .commitforge.json with defaults")
    sp = s.add_parser("scan", parents=[parent], help="Analyse working tree, suggest commit message")
    sp.add_argument("--format", choices=FMT_CHOICES, default=FORMAT_TERMINAL)
    sp.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
    hp = s.add_parser("health", parents=[parent], help="Scan repo for code-health issues")
    hp.add_argument("--format", choices=FMT_CHOICES, default=FORMAT_TERMINAL)
    hp.add_argument("--output", type=Path, default=None, help="Write report to file")
    rp = s.add_parser("report", parents=[parent], help="Generate Markdown/HTML report")
    rp.add_argument("--format", choices=FMT_CHOICES, default=None)
    rp.add_argument("--output", type=Path, default=Path("commitforge_report.html"))
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, dispatch to subcommand, return exit code."""
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    _setup_logging(args)
    dispatch = {"init": _cmd_init, "scan": _cmd_scan,
                "health": _cmd_health, "report": _cmd_report}
    fn = dispatch.get(getattr(args, "command", None))
    if fn is None:
        build_parser().print_help()
        return 0
    try:
        return fn(args)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return 130


def _setup_logging(args: argparse.Namespace) -> None:
    if args.quiet:
        level = logging.CRITICAL
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s",
                        stream=sys.stderr)


def _resolve_repo(explicit: Path | None) -> Path | None:
    """Return the Git repository root or None."""
    if explicit and explicit.is_dir():
        resolved = explicit.resolve()
    elif explicit:
        resolved = explicit.parent.resolve()
    else:
        return detect_repo_root(Path.cwd())
    return resolved if (resolved / ".git").exists() else None


def _run_pipeline(
    repo: Path, cfg: dict, since: str | None, author: str | None,
    extra_ignore: List[str],
) -> Dict[str, Any]:
    """Run diff + scan + generator; return unified results dict."""
    if since:
        diff = parse_diff_since(repo, since)
    else:
        diff = parse_diff_working(repo)
    if diff.error:
        logger.warning("Diff error: %s", diff.error)
    ignore = list(cfg.get("ignored_paths", [])) + extra_ignore
    issues = run_all_scans(repo, cfg.get("max_file_size_mb", 0.5), ignore)
    commit = generate_commit_suggestion(diff)
    return {
        "commit": commit, "branch": diff.branch,
        "files_changed": diff.files_changed, "additions": diff.additions,
        "deletions": diff.deletions, "file_paths": diff.file_paths,
        "health_issues": issues, "diff": diff,
    }

# Subcommands

def _cmd_init(args: argparse.Namespace) -> int:
    repo = _resolve_repo(args.repo)
    if repo is None:
        logger.error("Not inside a Git repository. Please run `git init` first.")
        return 1
    if not args.quiet:
        print(f"Config created: {write_default_config(repo)}")
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    repo = _resolve_repo(args.repo)
    if repo is None:
        logger.error("Not inside a Git repository.")
        return 1
    cfg = load_config(repo)
    res = _run_pipeline(repo, cfg, args.since, args.author, args.ignore)
    if res["files_changed"] == 0 and not res["health_issues"]:
        if not args.quiet:
            print("No changes detected.")
        return 0
    commit = res["commit"]
    issues = res["health_issues"]
    branch = res["branch"]
    if getattr(args, "as_json", False):
        _emit_json(res)
        return 0
    if args.format == FORMAT_MARKDOWN:
        print(render_markdown(commit, issues, branch))
    elif args.format == FORMAT_HTML:
        print(render_html(commit, issues, branch))
    else:
        render_terminal(commit, issues, branch)
    return 0


def _cmd_health(args: argparse.Namespace) -> int:
    repo = _resolve_repo(args.repo)
    if repo is None:
        logger.error("Not inside a Git repository.")
        return 1
    cfg = load_config(repo)
    res = _run_pipeline(repo, cfg, args.since, args.author, args.ignore)
    commit = res["commit"]
    issues = res["health_issues"]
    branch = res["branch"]
    if args.output:
        content = render_html(commit, issues, branch) if args.output.suffix == ".html" \
            else render_markdown(commit, issues, branch)
        write_report(content, args.output)
        if not args.quiet:
            print(f"Report written to {args.output}")
    else:
        render_terminal(commit, issues, branch)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    repo = _resolve_repo(args.repo)
    if repo is None:
        logger.error("Not inside a Git repository.")
        return 1
    cfg = load_config(repo)
    res = _run_pipeline(repo, cfg, args.since, args.author, args.ignore)
    commit = res["commit"]
    issues = res["health_issues"]
    branch = res["branch"]
    fmt = args.format
    if fmt is None:
        ext = args.output.suffix.lower()
        fmt_map = {".md": FORMAT_MARKDOWN, ".html": FORMAT_HTML, ".htm": FORMAT_HTML}
        fmt = fmt_map.get(ext, FORMAT_MARKDOWN)
    if fmt == FORMAT_HTML:
        content = render_html(commit, issues, branch)
    elif fmt == FORMAT_MARKDOWN:
        content = render_markdown(commit, issues, branch)
    else:
        render_terminal(commit, issues, branch)
        return 0
    write_report(content, args.output)
    if not args.quiet:
        print(f"Report written to {args.output}")
    return 0


def _emit_json(res: Dict[str, Any]) -> None:
    """Print structured JSON payload to stdout."""
    payload = {
        "branch": res["branch"], "files_changed": res["files_changed"],
        "additions": res["additions"], "deletions": res["deletions"],
        "commit_suggestion": format_commit(res["commit"]),
        "commit_detail": res["commit"],
        "issues_count": len(res["health_issues"]),
        "summary": _count_severities(res["health_issues"]),
        "files": res["diff"].files and [
            {"path": f.path, "status": f.status, "ins": f.insertions,
             "del": f.deletions} for f in res["diff"].files
        ] or [],
    }
    print(json.dumps(payload, indent=2))


def _count_severities(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for iss in issues:
        sev = iss.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
    return counts
