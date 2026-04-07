"""CommitForge CLI — single-flow, report-first."""

from __future__ import annotations

import logging
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import typer

from commitforge.analyzer import analyze_changes, get_checklist, suggest_commit
from commitforge.config import load_config
from commitforge.scanner import scan_repo
from commitforge.types import Config, ScanResult
from commitforge.utils import _log

app = typer.Typer(
    name="commitforge",
    help="Offline commit assistant and repo health checker.",
    add_completion=False,
)


def _find_git_root(start: Path) -> Path | None:
    """Walk up from *start* to find the git repository root."""
    current = start.resolve()
    while True:
        if (current / ".git").is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _generate_html(repo_root: Path, scan_result: ScanResult, config: Config) -> str:
    """Generate a self-contained HTML report."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    counts: dict[str, int] = {}
    for f in scan_result.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    colors = {"critical": "#dc3545", "warning": "#fd7e14", "info": "#6c757d"}

    cards = ""
    for level in ("critical", "warning", "info"):
        c = counts.get(level, 0)
        cards += (
            f'<div class="card" style="border-left:4px solid {colors[level]}">'
            f'<div class="card-num" style="color:{colors[level]}">{c}</div>'
            f'<div class="card-label">{level.upper()}</div></div>'
        )

    rows = ""
    for f in scan_result.findings:
        c = colors.get(f.severity, "#6c757d")
        loc = f.path
        if f.line_number > 0:
            loc += f":{f.line_number}"
        rows += (
            f'<tr><td><span class="badge" style="background:{c}20;color:{c}">'
            f'{f.severity.upper()}</span></td>'
            f'<td class="mono">{loc}</td>'
            f'<td>{f.message}</td></tr>\n'
        )

    suggestion = suggest_commit(config, scan_result=scan_result)
    suggestion_html = (
        f'<div class="suggestion"><code>{suggestion}</code>'
        f'<button onclick="navigator.clipboard.writeText(\'{suggestion}\')">'
        f'Copy</button></div>'
    )

    checklist = get_checklist(scan_result)
    actionable = [(s, l, m) for s, l, m in checklist if s in ("WARNING", "CRITICAL")]
    checklist_html = ""
    if actionable:
        items = "".join(
            f'<li><strong>[{s}]</strong> {l}: {m}</li>'
            for s, l, m in actionable
        )
        checklist_html = f'<h2>Before You Commit</h2><ul class="checklist">{items}</ul>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CommitForge Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
max-width:960px;margin:0 auto;padding:24px;color:#1a1a2e;background:#f8f9fa}}
h1{{font-size:1.6rem;margin-bottom:4px}}
.meta{{color:#666;font-size:.9rem;margin-bottom:20px}}
.cards{{display:flex;gap:12px;margin-bottom:24px}}
.card{{background:#fff;border-radius:8px;padding:16px 24px;flex:1;text-align:center;
box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card-num{{font-size:2rem;font-weight:700}}
.card-label{{font-size:.75rem;color:#666;text-transform:uppercase;letter-spacing:.05em}}
.suggestion{{background:#fff;border-radius:8px;padding:16px;margin-bottom:24px;
box-shadow:0 1px 3px rgba(0,0,0,.08);display:flex;align-items:center;gap:12px}}
.suggestion code{{flex:1;font-size:1rem;background:#f1f3f5;padding:8px 12px;
border-radius:6px;word-break:break-all}}
.suggestion button{{background:#4361ee;color:#fff;border:none;padding:8px 16px;
border-radius:6px;cursor:pointer;font-size:.85rem}}
.suggestion button:hover{{background:#3a56d4}}
h2{{font-size:1.1rem;margin:20px 0 12px;color:#333}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;
overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
th{{background:#f1f3f5;text-align:left;padding:10px 14px;font-size:.8rem;
text-transform:uppercase;color:#666;letter-spacing:.04em}}
td{{padding:10px 14px;border-top:1px solid #eee;font-size:.9rem}}
.mono{{font-family:"SF Mono",Consolas,monospace;font-size:.85rem}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75rem;
font-weight:600;letter-spacing:.03em}}
.checklist{{list-style:none;padding:0}}
.checklist li{{padding:8px 0;border-bottom:1px solid #eee;font-size:.9rem}}
.checklist li:last-child{{border-bottom:none}}
footer{{margin-top:32px;padding-top:16px;border-top:1px solid #ddd;
color:#999;font-size:.8rem;text-align:center}}
</style>
</head>
<body>
<h1>CommitForge Report</h1>
<p class="meta">{ts} &middot; {repo_root.resolve()}</p>
<div class="cards">{cards}</div>
{suggestion_html}
{checklist_html}
<h2>Findings</h2>
<table><thead><tr><th>Severity</th><th>Location</th><th>Details</th></tr></thead>
<tbody>{rows}</tbody></table>
<footer>Generated by CommitForge &middot; 100% offline &middot; zero config</footer>
</body>
</html>"""


@app.command()
def main(
    path: str = typer.Argument(
        ".", help="Path to your Git repository."
    ),
    no_open: bool = typer.Option(
        False, "--no-open", help="Don't open the report in browser."
    ),
) -> None:
    """Scan your repo, suggest a commit message, and open an HTML report."""
    repo_root = _find_git_root(Path(path).resolve())
    if repo_root is None:
        typer.echo("Error: not a Git repository.", err=True)
        raise typer.Exit(2)

    config = load_config(repo_root)
    scan_result = scan_repo(repo_root, config)
    scan_result = analyze_changes(repo_root, config, scan_result)

    counts: dict[str, int] = {}
    for f in scan_result.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    typer.echo(f"Files scanned: {scan_result.files_scanned}")
    typer.echo(f"Changes found: {len(scan_result.findings)}")

    parts = []
    for level in ("critical", "warning", "info"):
        if level in counts:
            parts.append(f"{counts[level]} {level}")
    typer.echo(f"Summary: {', '.join(parts)}")

    suggestion = suggest_commit(config, scan_result=scan_result)
    typer.echo(f"\nSuggested commit message:")
    typer.echo(f"  {suggestion}")

    checklist = get_checklist(scan_result)
    actionable = [(s, l, m) for s, l, m in checklist if s in ("WARNING", "CRITICAL")]
    if actionable:
        typer.echo("\nBefore you commit:")
        for i, (severity, location, message) in enumerate(actionable, 1):
            typer.echo(f"  {i}. [{severity}] {location}: {message}")

    report_path = repo_root / "commitforge-report.html"
    html = _generate_html(repo_root, scan_result, config)
    report_path.write_text(html, encoding="utf-8")
    typer.echo(f"\nReport: {report_path}")

    if not no_open:
        webbrowser.open(f"file://{report_path}")

    if scan_result.thresholds_exceeded:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
