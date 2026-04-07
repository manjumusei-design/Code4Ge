# CommitForge

Tired of writing vague commit messages!? CommitForge parses your actual git diff, infers the right conventional commit type, and scans your repo for things you probably should not be shipping. Stuff like binary blobs you forgot about, TODOs that piled up, functions with no docstrings, imports nobody uses. All in one command with no netowrk needed!

## Setup

```bash
git clone https://github.com/commitforge/commitforge.git && cd commitforge
python -m commitforge init          # creates .commitforge.json
python -m commitforge scan          # suggests commit message
python -m commitforge health        # code health table
python -m commitforge analyze --format html --output report.html
```

**Requires:** Python 3.8+, Git. Works on Windows, macOS, Linux. Zero `pip install`.

## Commands

| Command | Description |
|---|---|
| `init` | Create `.commitforge.json` config |
| `scan` | Parse `git diff` → suggest conventional commit |
| `health` | Scan for large files, binaries, TODOs, missing docstrings, unused imports |
| `report` | Generate Markdown/HTML report of suggested commit |
| `analyze` | Full pipeline: scan + health + report |

**Flags:** `--format text|md|html`, `--since YYYY-MM-DD`, `--author NAME`, `--ignore PATTERN`, `--output FILE`, `--verbose`, `--quiet`, `--no-cache`, `--repo PATH`

## Troubleshooting Outputs for reference
- **Not a git repo**: Run `git init` first.
- **Permission denied**: Config file unreadable → falls back to defaults.
- **Encoding errors**: Files read with utf-8 → latin-1 → ignore fallback.
- **Git not found**: Install Git and ensure it's on your `PATH`.
