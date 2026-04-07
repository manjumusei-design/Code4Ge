"""Renders CommitForge findings to terminal (ANSI), Markdown, or HTML."""

from __future__ import annotations

import html as html_mod
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

FORMAT_TERMINAL = "terminal"
FORMAT_MARKDOWN = "markdown"
FORMAT_HTML = "html"

_SEVERITY_ICONS = {"critical": "🔴", "warning": "🟡", "info": "🟢"}
_COLORS = {"reset": "\033[0m", "bold": "\033[1m", "red": "\033[91m",
           "yellow": "\033[93m", "green": "\033[92m", "cyan": "\033[96m",
           "gray": "\033[90m"}


def render_terminal(
    commit: Dict[str, str], issues: List[Dict[str, Any]], branch: str
) -> None:
    """Print a colored report to stdout with severity emoji icons."""
    from commitforge.generator import format_commit

    _p(_COLORS["bold"] + "=== CommitForge ===" + _COLORS["reset"])
    _p(_COLORS["cyan"] + "Suggested commit:" + _COLORS["reset"])
    for line in format_commit(commit).splitlines():
        _p(f"  {line}")
    _p("")
    _p(_COLORS["cyan"] + f"Branch: {branch}" + _COLORS["reset"])
    _summary = _count_severities(issues)
    for sev in ("critical", "warning", "info"):
        icon = _SEVERITY_ICONS[sev]
        _p(f"  {icon} {sev}: {_summary.get(sev, 0)}")
    if issues:
        _p("")
        for issue in issues[:20]:
            icon = _SEVERITY_ICONS.get(issue.get("severity", "info"), "🟢")
            line_info = f":{issue['line']}" if issue.get("line") else ""
            _p(f"  {icon} [{issue['severity']}] {issue['file']}{line_info} -- {issue['message']}")
        if len(issues) > 20:
            _p(_COLORS["gray"] + f"  ... and {len(issues) - 20} more" + _COLORS["reset"])


def render_markdown(commit: Dict[str, str], issues: List[Dict[str, Any]], branch: str) -> str:
    """Return a GitHub-flavored Markdown report."""
    from commitforge.generator import format_commit

    lines = ["# CommitForge Report\n",
             f"**Branch:** `{branch}`", f"**Issues:** {len(issues)}\n",
             "## Suggested Commit\n```", format_commit(commit), "```\n"]
    if issues:
        lines += ["| File | Rule | Severity | Message | Line |",
                   "|------|------|----------|---------|------|"]
        for iss in issues:
            lines.append(f"| {iss['file']} | {iss['rule']} | {iss['severity']} "
                         f"| {iss['message']} | {iss.get('line') or '-'} |")
    return "\n".join(lines) + "\n"


def render_html(commit: Dict[str, str], issues: List[Dict[str, Any]], branch: str) -> str:
    """Return a self-contained HTML page with inline CSS."""
    from commitforge.generator import format_commit

    esc = html_mod.escape
    commit_html = esc(format_commit(commit))
    rows = ""
    for iss in issues:
        sev = iss.get("severity", "info")
        rows += (f"<tr><td>{esc(iss['file'])}</td><td>{esc(iss['rule'])}</td>"
                 f"<td><span class=\"badge-{sev}\">{sev}</span></td>"
                 f"<td>{esc(iss['message'])}</td>"
                 f"<td>{iss.get('line') or '-'}</td></tr>\n")
    table = ""
    if issues:
        table = ("<h2>Issues</h2><table><tr><th>File</th><th>Rule</th>"
                 "<th>Severity</th><th>Message</th><th>Line</th></tr>\n"
                 f"{rows}</table>")
    return (
        f"<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<title>CommitForge</title><style>"
        f"body{{font-family:sans-serif;margin:2rem;background:#fafafa}}"
        f"table{{border-collapse:collapse;width:100%}}"
        f"th,td{{border:1px solid #ccc;padding:6px 10px;text-align:left}}"
        f"th{{background:#eee}}"
        f".badge-critical{{color:#c00}}.badge-warning{{color:#b80}}"
        f".badge-info{{color:#555}}"
        f"pre{{background:#f4f4f4;padding:1rem;overflow:auto}}"
        f"</style></head><body>"
        f"<h1>CommitForge Report</h1>"
        f"<p><strong>Branch:</strong> {esc(branch)}</p>"
        f"<h2>Suggested Commit</h2><pre>{commit_html}</pre>"
        f"{table}</body></html>"
    )


def write_report(content: str, output: Path) -> None:
    """Write *content* to *output*, creating parent dirs if needed."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    logger.info("Report written to %s", output)


# Helper functions after I boiled them down

def _p(text: str) -> None:
    print(text)


def _count_severities(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for iss in issues:
        sev = iss.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
    return counts
