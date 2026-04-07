# CommitForge

Offline commit assistant and repo health checker. One command. One report. Done.

Developers waste mental energy writing inconsistent commit messages and unknowingly let technical debt accumulate. Existing tools are either cloud-dependent, heavy, or require complex setup.

CommitForge eliminates that friction with a **100% offline, zero-config CLI** that analyzes your working tree, suggests conventional commit messages, flags repo anti-patterns, and outputs clean reports in under 2 seconds.

## What It Solves

| Pain Point | How You Experience It | How CommitForge Solves It |
|---|---|---|
| **Commit inconsistency** | "What should I name this commit?" → vague messages that break changelogs | Analyzes `git diff` + file paths → maps to conventional commit format. One command → ready-to-copy message. |
| **Silent codebase decay** | Large files, accidental binaries, TODO pile-ups go unnoticed until CI fails | Scans working tree for anti-patterns → flags them with severity → exports to HTML before they become debt. |
| **Tooling friction** | Most helpers require npm/pip installs, API keys, cloud processing | Stdlib-only Python. Zero network calls. Zero external packages. Runs on air-gapped machines. |
| **Review blindness** | No fast way to assess repo health without running full CI pipelines | `commitforge` → instant, readable report. Perfect for PR descriptions or quick sanity checks. |

## Quick Start

```bash
# Install
pip install commitforge

# Or download commitforge.exe from Releases
```

### One command. That's it.

```bash
cd your-project
commitforge
```

That's the entire workflow. It:
1. Auto-detects your git root
2. Scans tracked and untracked files
3. Reads your actual diff — detects added/removed functions, classes, imports
4. Runs pre-commit checks — debug prints, TODOs, secrets, missing tests
5. Suggests a commit message based on what it found
6. Opens an HTML report in your browser

### What you'll see

```
$ commitforge
Files scanned: 29
Changes found: 49
Summary: 12 warning, 37 info

Suggested commit message:
  feat(auth): Added function `validate_password()`; Added function `hash_token()`

Before you commit:
  1. [WARNING] src/auth.py: No test file found — consider adding tests
  2. [CRITICAL] src/debug.py: Debug print detected: `print("DEBUG:", x)`

Report: /path/to/your-project/commitforge-report.html
```

The HTML report opens automatically — shareable, readable, no setup needed.

## Flags

| Flag | What it does |
|---|---|
| `--no-open` | Don't open the report in browser |
| `--help` | Show help |

## Pre-Commit Checks

| Check | Severity | What it catches |
|---|---|---|
| Debug prints | Critical | `print()`, `pprint()`, `console.log()`, `debugger;` |
| Secrets | Critical | Hardcoded passwords, API keys, tokens |
| TODOs | Warning | `TODO`, `FIXME`, `HACK`, `XXX`, `BUG` comments |
| Missing tests | Warning | New source files without a corresponding test file |
| Long lines | Info | Lines over 120 characters |
| Deprecated markers | Warning | Comments containing "deprecated", "legacy", "workaround" |
| Large files | Critical | Files over the size limit (default 0.5 MB) |
| Binary files | Critical | `.exe`, `.dll`, `.so`, etc. accidentally committed |

## Configuration (Optional)

CommitForge works with zero config. If you want to customize behavior, run:

```bash
commitforge init
```

This creates `.commitforge.json`:

```json
{
  "ignore_paths": ["node_modules", ".venv", "__pycache__", ".git", "dist"],
  "max_file_size_mb": 0.5,
  "severity_thresholds": {"warning": 3, "critical": 1},
  "commit_mappings": {
    "feat": "feat",
    "fix": "fix",
    "test": "test",
    "docs": "docs",
    "style": "style",
    "refactor": "refactor",
    "perf": "perf",
    "chore": "chore"
  }
}
```

All keys are optional. Missing values merge with built-in defaults.

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Clean — ready to commit |
| `1` | Issues found — review the report before committing |
| `2` | Not a git repository or config error |

## Tech Details

- Python 3.9+
- One dependency: `typer` (CLI framework)
- Everything else is stdlib
- Type-checked with `mypy --strict`
- Tested with `pytest` (90%+ coverage)
- Works identically on Windows, macOS, Linux

## Dev Setup

```bash
pip install pytest ruff mypy
pytest commitforge/tests -v
mypy --strict commitforge/
ruff check commitforge/ tests/
```

## License

MIT
