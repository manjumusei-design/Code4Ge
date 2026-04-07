"""Report rendering for CommitForge."""

from __future__ import annotations

import html
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from commitforge.types import Issue
from commitforge.utils import get_terminal_size

logger = logging.getLogger(__name__)

_SEV_COLORS = {"critical": "\033[31m", "warning": "\033[33m", "info": "\033[32m"}
_RESET = "\033[0m"
_BOLD = "\033[1m"


def render_terminal(commit: Dict[str, str],
                    issues: List[Issue],
                    width: int = 0) -> None:
    """Print a coloured, width-adapted report to stdout."""
    cols = width or get_terminal_size()[0]
    print("{}=== CommitForge ==={}".format(_BOLD, _RESET))
    header = "{}({}){}: {}".format(
        commit["type"], commit["scope"], _RESET, commit["summary"])
    print("  {}".format(_truncate(header, cols - 2)))
    if commit.get("body"):
        for line in commit["body"].splitlines():
            print("  {}".format(_truncate(line, cols - 2)))
    print("")
    if not issues:
        print("  No issues found.")
        return
    counts = _count_severities(issues)
    parts = ["{0} critical".format(counts.get("critical", 0)),
             "{0} warnings".format(counts.get("warning", 0)),
             "{0} info".format(counts.get("info", 0))]
    print("  Issues: {}".format(", ".join(parts)))
    print("")
    for iss in issues:
        color = _SEV_COLORS.get(iss.severity, "")
        tag = "[{}]".format(iss.severity.upper())
        loc = "{}:{}".format(iss.file, iss.line) if iss.line else iss.file
        print("  {}{}{} {} -- {}".format(
            color, tag, _RESET, _truncate(loc, cols - 14), iss.message))


def render_markdown(commit: Dict[str, str],
                     issues: List[Issue]) -> str:
    """Return a GitHub-flavoured Markdown report."""
    lines = [
        "# CommitForge Report", "",
        "**Type:** `{type}`  ".format(**commit),
        "**Scope:** `{scope}`  ".format(**commit),
        "**Summary:** {summary}".format(**commit), "",
    ]
    if commit.get("body"):
        lines.append("```")
        lines.append(commit["body"])
        lines.append("```")
        lines.append("")
    if not issues:
        lines.append("No issues found.")
        return "\n".join(lines)
    lines += ["## Issues", "",
              "| File | Type | Severity | Message | Line |",
              "|------|------|----------|---------|------|"]
    for iss in issues:
        lines.append("| `{}` | {} | {} | {} | {} |".format(
            iss.file, iss.type, iss.severity, iss.message,
            iss.line if iss.line else "-"))
    return "\n".join(lines)


def render_html(commit: Dict[str, str],
                issues: List[Issue]) -> str:
    """Return a minimal HTML page with inline CSS."""
    return "\n".join([
        _html_head(),
        _html_header(commit),
        _html_issues(issues),
        "</body></html>",
    ])


def _html_head() -> str:
    """Return the HTML head block with inline CSS."""
    return (
        "<!DOCTYPE html><html lang=\"en\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>CommitForge</title>"
        "<style>"
        "body{font-family:system-ui,sans-serif;margin:2rem;background:#fafafa}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #d0d0d0;padding:6px 10px;text-align:left}"
        "th{background:#f0f0f0}"
        ".critical{color:#c00}.warning{color:#a60}.info{color:#080}"
        ".badge{display:inline-block;padding:2px 6px;border-radius:3px;"
        "font-size:0.85em;color:#fff}"
        ".badge-critical{background:#c00}.badge-warning{background:#a60}"
        ".badge-info{background:#080}"
        "pre{background:#f4f4f4;padding:1rem;overflow-x:auto}"
        "</style></head>"
    )


def _html_header(commit: Dict[str, str]) -> str:
    """Return the report title and summary section."""
    esc = html.escape
    body = ""
    if commit.get("body"):
        body = "<pre>{}</pre>".format(esc(commit["body"]))
    return "".join([
        "<body><h1>CommitForge Report</h1>",
        "<p><strong>Type:</strong> {type} &middot; "
        "<strong>Scope:</strong> {scope}</p>".format(**commit),
        "<h2>Summary</h2><pre>{summary}</pre>".format(**commit),
        body,
    ])


def _html_issues(issues: List[Issue]) -> str:
    """Return the issues table or a no-issues message."""
    if not issues:
        return "<p>No issues found.</p>"
    esc = html.escape
    rows = ""
    for iss in issues:
        rows += (
            "<tr><td><code>{0}</code></td><td>{1}</td>"
            "<td><span class=\"badge badge-{2}\">{2}</span></td>"
            "<td>{3}</td><td>{4}</td></tr>".format(
                esc(iss.file), esc(iss.type), esc(iss.severity),
                esc(iss.message), iss.line if iss.line else "-"))
    return "".join([
        "<h2>Issues</h2>",
        "<table><thead><tr><th>File</th><th>Type</th>"
        "<th>Severity</th><th>Message</th><th>Line</th></tr></thead>",
        "<tbody>{}</tbody></table>".format(rows),
    ])


def write_output(content: str, path: Optional[Path] = None) -> None:
    """Print *content* to stdout, or write to *path* as UTF-8."""
    if path is None:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("Report written to %s", path)


# Helpers -----------------------------------------------------------------

def _count_severities(issues: List[Issue]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for iss in issues:
        counts[iss.severity] = counts.get(iss.severity, 0) + 1
    return counts


def _truncate(text: str, max_len: int) -> str:
    if max_len <= 3 or len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
