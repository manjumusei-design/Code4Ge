"""Typer-based CLI for commitforge."""

from __future__ import annotations

from pathlib import Path

import typer

from commitforge.analyzer import analyze_changes
from commitforge.config import create_default_config, load_config
from commitforge.scanner import scan_repo
from commitforge.utils import _log
from commitforge.validator import validate_commit_message

import logging

app = typer.Typer(
    name="commitforge",
    help="Repository analysis and commit standardization tool.",
    add_completion=False,
)


@app.command()
def init(repo_root: Path = typer.Argument(
    Path("."), help="Path to the repository root."
)) -> None:
    """Create a default .commitforge.json configuration file."""
    if not repo_root.is_dir():
        typer.echo(f"Error: '{repo_root}' is not a directory.", err=True)
        raise typer.Exit(2)
    create_default_config(repo_root)
    typer.echo(f"Config created at: {repo_root / '.commitforge.json'}")


@app.command()
def scan(
    repo_root: Path = typer.Argument(
        Path("."), help="Path to the repository root."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed findings."
    ),
) -> None:
    """Scan the repository and print findings."""
    config = load_config(repo_root)
    scan_result = scan_repo(repo_root, config)
    scan_result = analyze_changes(repo_root, config, scan_result)

    if verbose:
        typer.echo(f"Files scanned: {scan_result.files_scanned}")
        for finding in scan_result.findings:
            typer.echo(
                f"  [{finding.severity.upper():8s}] {finding.path}: {finding.message}"
            )
    else:
        typer.echo(
            f"Scanned {scan_result.files_scanned} files, "
            f"{len(scan_result.findings)} findings."
        )

    if scan_result.thresholds_exceeded:
        typer.echo("WARNING: Severity thresholds exceeded.", err=True)
        raise typer.Exit(1)


@app.command()
def suggest(
    repo_root: Path = typer.Argument(
        Path("."), help="Path to the repository root."
    ),
    scope: str | None = typer.Option(
        None, "--scope", "-s", help="Commit scope (e.g., 'core', 'api')."
    ),
    breaking: bool = typer.Option(
        False, "--breaking", "-b", help="Mark as a breaking change."
    ),
) -> None:
    """Generate a conventional commit suggestion."""
    config = load_config(repo_root)
    scan_result = scan_repo(repo_root, config)
    scan_result = analyze_changes(repo_root, config, scan_result)

    if not scan_result.findings:
        typer.echo("No changes detected to generate a suggestion from.")
        return

    types = {f.type for f in scan_result.findings}
    commit_type = types.pop() if len(types) == 1 else "chore"
    count = scan_result.files_scanned
    suggestion = f"{commit_type}"
    if scope:
        suggestion += f"({scope})"
    if breaking:
        suggestion += "!"
    suggestion += f": update {count} file{'s' if count != 1 else ''}"
    typer.echo(suggestion)


@app.command()
def validate(
    message: str = typer.Argument(..., help="The commit message to validate."),
    repo_root: Path = typer.Argument(
        Path("."), help="Path to the repository root (for config)."
    ),
) -> None:
    """Validate a commit message against Conventional Commit rules."""
    config = load_config(repo_root)
    is_valid, violations = validate_commit_message(message, config)
    if is_valid:
        typer.echo("Commit message is valid.")
    else:
        typer.echo("Commit message has errors:")
        for v in violations:
            typer.echo(f"  - {v}")
        raise typer.Exit(1)


@app.command()
def status(
    repo_root: Path = typer.Argument(
        Path("."), help="Path to the repository root."
    ),
) -> None:
    """Show a quick summary of the current configuration and scan state."""
    config = load_config(repo_root)
    typer.echo("=== CommitForge Status ===")
    typer.echo(f"Ignored paths: {len(config.ignore_paths)}")
    typer.echo(f"Max file size: {config.max_file_size_mb} MB")
    typer.echo(f"Severity thresholds: {config.severity_thresholds}")
    typer.echo(f"Commit mappings: {len(config.commit_mappings)} types")
    scan_result = scan_repo(repo_root, config)
    typer.echo(f"Files scanned: {scan_result.files_scanned}")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
