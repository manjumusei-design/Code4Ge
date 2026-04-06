"""Terminal markdown and HTML report formatting for commitforge."""

from __future__ import annotations 

import html
import logging
from pathlib import Path
from typing import List, Optional


from commitforge.gemerator import generate_commit_suggestion
from commitforge.parser import DiffrResult
from commitforge.scanner import Issue, ScanResult, SEVERITY_CRITICAL, SEVERITY_WARNING

logger = logging.getLogger(__name__)

FORMAT_TERMINAL = "terminal"
FORMAT_MARKDOWN = "markdown"
FORMAT_HTML= "html"

# Terminal output with colours for clarity ig
_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "green": "\033[92m",
    "cyan": "\033[96m",
    "gray": "\033[90m",
}


def print_terminal(diff_result: DiffResult, scan_result: Optional[ScanResult] = None) -> None:
    """Print a colored summary to stdout."""
    commit_msg = generate_commit_suggestion(diff_result)
    _cprint(_COLORS["bold"] + "=== CommitForge Scan ===" + _COLORS["reset"])
    _cprint(_COLORS["cyan"] + "Suggested commit:" + _COLORS["reset"])
    for line in commit_msg.splitlines():
        _cprint(f"  {line}")
        
    _cprint("")
    _cprint(_COLORS["cyan"] + f"Branch: {diff_result.branch}" + _COLORS["reset"])
    _cprint(
        _COLORS["gray"]
        + f"Files changed: {len(diff_result.files)}"
        + _COLORS["reset"]
    )
    
    if scan_result:
        _cprint("")
        _print_scan_summary_terminal(scan_result)
        
def render_markdown(
    diff_result: DiffResult, scan_result: Optional[ScanResult] = None
) -> str:
    """This is to render findings as a markdown file"""
    lines: List[str] =[]
    lines.append("# CommitForge Report\n")
    lines.append(f"**Branch** `{diff_result.branch}` ")
    lines.append(f"**Files that were changed** {len(diff_result.files)}\n")
    commit_msh = generate_commit_suggestion(diff_result)
    lines.append("## Suggested Commit\n")
    lines.append ("```")
    lines.append(commit_msg)
    lines.append("``\n")
    
    if scan_result:
        lines.append("## Health Scan\n")
        lines.append(f"**Files scanned: ** {scan_result.files_scanned} ")
        summary = scan_result.summary
        lines.append(
            f"**Issues:** "
            f"{summary.get(SEVERITY_CRITICAL, 0)} critical"
            f"{summary.get(SEVERITY_WARNING, 0)} warnings, "
            f"{summary.get('info',0)} info\n"
        )
        if scan_result.issues:
            lines.append("### Issues\n")
            lines.append("| File | Rule | Severity | Message | Line |")
            lines.append("|------|------|----------|---------|------|")
            for issue in scan_result.issues:
                lines.append(
                    f"| {issue.file} | {issue.rule} | {issue.severity} "
                    f"| {issue.message} | {issue.line or '-'} |"
                )

    return "\n".join(lines) + "\n"
                 
                 
def render_html(
    diff_result: DiffResult, scan_result: Optional[ScanResult] = None 
) -> str:
    """This is to rendr findings as a self contained HTML page"""
    commit_msg = html.escape(generate_commit_suggestion(diff_result))
    issues_html = ""
    if scan_result:
        issues_html = _render_scan_html(scan_result)
        
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>CommitForge Report</title>"
        "<style>"
        "body{font-family:sans-serif;margin:2rem;background:#fafafa}"
        "table{border-collapse:collapse;width:100%%}"
        "th,td{border:1px solid #ccc;padding:6px 10px;text-align:left}"
        "th{background:#eee}"
        ".critical{color:#c00}.warning{color:#b80}.info{color:#555}"
        "pre{background:#f4f4f4;padding:1rem;overflow:auto}"
        "</style></head><body>\n"
        f"<h1>CommitForge Report</h1>"
        f"<p><strong>Branch:</strong> {html.escape(diff_result.branch)}<br>"
        f"<strong>Files changed:</strong> {len(diff_result.files)}</p>\n"
        f"<h2>Suggested Commit</h2><pre>{commit_msg}</pre>\n"
        f"{issues_html}"
        "</body></html>"
    )
    
def write_report(
    diff_result: DiffResult,
    output_path: Path,
    scan_result: Optional[ScanResult] = None,
    ) -> None:
    """Detect format from the extension and then write a report for the specified path"""
    ext = output_path.suffix.lower()
    if ext == ".md":
        content = render_markdownh(diff_result, scan_result)
    elif ext == ".html":
        content = render_html(diff_result, scan_result)
        else: 
        logger.warning("Unknown extension %s - writing Markdown.", ext)
        content = render_markdown(diff_result, scan_result)
            
        output_path.write_text(content, encoding="utf-8")
        logger.info("Report written to %s", output_path)
        
        
# Helper functions here
def _cprint(textL str) -> None:
    """Print a compact issue summary"""
    summary = scan_result.summary
    critical = summary.get(SEVERITY_CRITICAL, 0)
    warning = summary.get(SEVERITY_WARNING, 0)
    info = summary.get("info", 0)
    
    color = _COLORS["red"] if critical else _COLORS["yellow"] if warning else _COLORS["green"]
    _cprint(
        color + _COLORS ["bold"]
        + f"Issues: {critical} critical, {warning} warnings, {info} info"
        + _COLORS["reset"]
    )
    for issue in scan_result.issues[:20]:
        sev_color = {
            SEVERITY_CRITICAL: _COLORS["red"],
            SEVERITY_WARNING: _COLORS["yellow"],
        }.get(issue.severity, _COLORS["gray"])
        line_info = f":{issue.line}" if issue.line else ""
        _cprint (
            f"  {sev_color}[{issue.severity.upper()}]{_COLORS['reset']} "
            f"{issue.file}{line_info} - {issue.message}"
        )
    if len(scan_result.issues) >20:
        _cprint(_COLORS["gray"] + f"  ... and {len(scan_result.issues) - 20} more" + _COLORS["reset"])
        
def _render_scan_html(scan_result: ScanResult) -> str:
    """Return a HTML table for the scan results and issues"""
    if not scan_result.issues:
        return "<h2>Health Scan</h2><p>No issues found.</p>\n"
    
    rows = ""
    for issue in scan_result.issues:
        cls = issue.severity
        rows +=(
            f"<tr class=\"{cls}\">"
            f"<td>{html.escape(issue.file)}</td>"
            f"<td>{html.escape(issue.rule)}</td>"
            f"<td>{html.escape(issue.severity)}</td>"
            f"<td>{html.escape(issue.message)}</td>"
            f"<td>{issue.line or '-'}</td>"
            f"</tr>\n"
        )
return (
    "<h2>Health Scan</h2>"
    f"<p>Files scanned: {scan_result.files_scanned}</p>\n"
    "<table><tr><th>File</th><th>Rule</th><th>Severity</th><th>Message</th><th>Line</th></tr>\n"
    f"{rows}</table>\n"
    )
        