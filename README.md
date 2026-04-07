# CommitForge

Your commit messages are a mess. This fixes that.

CommitForge is a CLI tool that reads your actual code changes, tells you what you're about to commit, catches common mistakes, and suggests a proper commit message. No AI, no magic just best practice rules that make you and your team work better together.

## What It Does

- **Reads your diff** — detects added/removed functions, classes, and imports, not just "file changed"
- **Runs pre-commit checks** — catches debug prints, TODOs, hardcoded secrets, missing tests, and long lines
- **Classifies by severity** — info, warning, or critical, so you know what matters
- **Suggests commit messages** — builds a specific message from the actual changes it found
- **Validates messages** — checks against the [Conventional Commits](https://www.conventionalcommits.org/) spec
- **Exports reports** — Markdown or HTML, shareable with your team
- **Auto-detects your git root** — works from any subdirectory, no path guessing

## Quick Start

### Install

```bash
# Option 1: pip (recommended)
pip install commitforge

# Option 2: download the .exe from Releases
# Put it somewhere on your PATH, then just type "commitforge"
```

### Use it before every commit

```bash
cd your-project

# Quick scan — see what's changed and if anything needs fixing
commitforge scan

# Detailed scan — see exactly what functions, classes, and imports changed
commitforge scan --verbose

# Get a commit suggestion based on what it found
commitforge suggest

# Validate your message before committing
commitforge validate "feat(auth): add password validation"

# Export a report to share with your team
commitforge scan --report findings.html
```

## What You'll See

### Quick scan
```
$ commitforge scan
Files scanned: 26
Changes found: 5
Summry: 1 warning, 4 info

Before you commit:
  1. [WARNING] src/auth.py: No test file found — consider adding tests
```

### Detailed scan
```
$ commitforge scan --verbose
Files scanned: 26
Changes found: 5

  [INFO    ] src/auth.py:22
             -> Added function `validate_password()`
  [INFO    ] src/auth.py:45
             -> Added import `hashlib`
  [WARNING ] src/auth.py
             -> No test file found — consider adding tests

Summary: 1 warning, 4 info

Before you commit:
  1. [WARNING] src/auth.py: No test file found — consider adding tests
```

### Commit suggestion
```
$ commitforge suggest
feat(auth): Added function `validate_password()`; Added import `hashlib`
```

### Message validation
```
$ commitforge validate "feat(auth): add password validation"
Commit message is valid.

$ commitforge validate "updated the auth stuff"
Commit message has errors:
  - Header does not match Conventional Commit format: type(scope)?: description (<=72 chars)
  - Header should use imperative mood (e.g., 'add', not 'added').
```

## Commands

| Command | What it does |
|---|---|
| `commitforge init [path]` | Creates `.commitforge.json` with default settings |
| `commitforge scan [path] [-v] [-r report.md]` | Scans changed files, runs checks, reports findings |
| `commitforge suggest [path] [-s scope] [-b]` | Generates a commit suggestion from actual changes |
| `commitforge validate "message"` | Checks a commit message against the spec |
| `commitforge status [path]` | Quick summary of config and scan state |

### Flags

| Flag | What it does |
|---|---|
| `-v`, `--verbose` | Show per-file details: what functions/classes/imports changed |
| `-r`, `--report file.md` | Export findings to Markdown or HTML |
| `-s`, `--scope api` | Set the commit scope for suggestions |
| `-b`, `--breaking` | Mark the suggestion as a breaking change |

## Pre-Commit Checks

When you scan, CommitForge checks every changed file for:

| Check | Severity | What it catches |
|---|---|---|
| Debug prints | Critical | `print()`, `pprint()`, `console.log()`, `debugger;` |
| Secrets | Critical | Hardcoded passwords, API keys, tokens |
| TODOs | Warning | `TODO`, `FIXME`, `HACK`, `XXX`, `BUG` comments |
| Missing tests | Warning | New source files without a corresponding test file |
| Long lines | Info | Lines over 120 characters |
| Deprecated markers | Warning | Comments containing "deprecated", "legacy", "workaround" |

## Configuration

Run `commitforge init` to generate `.commitforge.json`. It looks like this:

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

| Key | What it controls |
|---|---|
| `ignore_paths` | Paths to skip (supports `fnmatch` globs like `**/*.log`) |
| `max_file_size_mb` | Skip files larger than this (clamped 0.01–1024.0) |
| `severity_thresholds` | How many findings of each severity before flagging |
| `commit_mappings` | Maps file patterns to conventional commit types |

All keys are optional. Missing values merge with built-in defaults.

## Exit Codes

| Code | When you'll see it |
|---|---|
| `0` | Everything's fine |
| `1` | Thresholds exceeded (`scan`) or invalid message (`validate`) |
| `2` | Config error, bad JSON, or directory not found |

## Why This Exists

If you've ever been on a team where one person writes `fixed stuff`, another writes `FEAT: NEW THING!!!`, and a third writes a novel as their commit message — you know why this matters.

Conventional Commits give you:
- Auto-generated changelogs
- Clear semantic version bumps
- A history you can actually read six months later

CommitForge enforces that without needing a pre-commit hook, a CI pipeline, or someone policing the team. Run it before you commit, catch mistakes early, move on.

## Tech Details

- Python 3.9+
- One dependency: `typer` (for the CLI)
- Everything else is stdlib
- Type-checked with `mypy --strict`
- Tested with `pytest` (90%+ coverage target)

## Dev Setup

```bash
# Install dev dependencies
pip install pytest ruff mypy

# Run tests
pytest commitforge/tests -v

# Type check
mypy --strict commitforge/

# Lint
ruff check commitforge/ tests/
```

## License

MIT
