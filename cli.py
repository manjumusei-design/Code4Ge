from __future__ import annotations

import argparse, logging, sys
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
    """This is for the top level argument parser"""
    parser = argparse.ArgumentParser(
        prog="commitforge",
        description="Offline CLI for semantic commit suggestions as well as repo health checks for possible errors",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
            "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    
    
    sub = parser.add_subparsers(dest="command", help="Sub-command")
    
    # Init 
    sub.add_parser("init", help="Create a default .commitforge.json")
    
    # To scan
    sub.add_parser("scan", help="Analyse working tree to suggest a commit message")
    
    # Health 
    health_p = sub.add_parser("health", help="Scan repo for code-health issues")
    health_p.add_argument(
        "--format",
        choices=[FORMAT_TERMINAL, FORMAT_MARKDOWN, FORMAT_HTML],
        default=FORMAT_TERMINAL,
        help="Output format (default: terminal)",
    )
    health_p.add_argument(
        "--output", type=Path, default=None, help="Write report to a file (e.g report.html)"
    )
    
    report_p = sub.add_parser("report", help="Generate a markdown or a HTML report (alias for health --output)")
    report_p.add_argument(
        "--output", type=Path, default=Path("commitforge_report.html"),
        help="Report output path (default: commitforge_report.html)",
    )
    report_p.add_argument(
        "--format",
        choices=[FORMAT_TERMINAL, FORMAT_MARKDOWN, FORMAT_HTML],
        default=None,
        help="Format (Auto-detected from --output extension if omitted)",
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


#some subcommand implemenntations should go here

def _cmd_init(args:argparse.Namespace) -> int:
    """Handle the commitforge scan"""
    
    repo_root = _resolve_repo(args.repo)
    if repo_root is None:
        logger.error("Not inside a git repo.")
        return 1
    
    cfg = load_config(repo_root)
    diff_result = parse_diff_working(repo_root)
    if diff_result.error:
        logger.warning("Diff encountered issues: %s".diff_result.error)
        
def _cmd_health(args: argparse.Namespace) -> int:
    """This is to handle the commmit forge health"""
    repo_root = _resolve_repo(args.repo)
    if repo_root is None:
        logger.error("Not inside a git repo.")
        return 1

    cfg = load_config(repo_root)
    diff_result = parse_diff_working(repo_root)
    scan_result = scan_repo(
        repo_root,
        ignored_paths=cfg.get("ignored_paths", []),
        max_file_size_kb=cfg.get("max_file_size_kb",500),
    )
    
    fmt= getattr(args,"format", FORMAT_TERMINAL)
    out_path: Path | None = getattr(args, "output", None)
    
    if output_path:
        write_report(diff_result, output_path, scan_result)
        print(f"Report written to {output_path}")
    else:
        print_terminal(diff_result, scan_result)
        
    return 0

def _cmd_report(args: argparse.Namespace) -> int:
    """Handle commitforge report"""
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
    
    # Auto-detect format from extension when not explicitly specified
    if fmt is None:
        ext = output_path.suffix.lower()
        fmt_map = {".md": FORMAT_MARKDOWN, ".html": FORMAT_HTML, ".htm": FORMAT_HTML}
        fmt = fmt_map.get(ext, FORMAT_MARKDOWN)
        
        if fmt == FORMAT_HTML:
            content = render_html(diff_result, scan_result)
        
        output_path.write_text(content, encoding="utf-8")
        print(f"Report written to {output_path}")
        return 0
    
    #Help
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