# CommitForge

Repository analysis and commit standardization tool for Python projects.

## Installation

```bash
pip install commitforge
```

## Usage

```bash
commitforge init             # Create .commitforge.json
commitforge scan             # Scan repository
commitforge scan --verbose   # Show detailed findings
commitforge suggest          # Generate commit suggestion
commitforge validate "feat(core): add feature"  # Validate a commit message
commitforge status           # Quick config summary
```

## Configuration (.commitforge.json)

```json
{
  "ignore_paths": ["node_modules", ".venv", "__pycache__", ".git", "dist"],
  "max_file_size_mb": 0.5,
  "severity_thresholds": {"warning": 3, "critical": 1},
  "commit_mappings": {
    "test": "test", "docs": "docs", "style": "style",
    "refactor": "refactor", "perf": "perf", "chore": "chore"
  }
}
```

- All keys are optional; missing values merge with defaults.
- `ignore_paths` supports `fnmatch` globs.
- `max_file_size_mb` is clamped between 0.01 and 1024.0.

## Exit Codes

| Code | Meaning |
|------|--------|
| 0 | Success |
| 1 | Thresholds exceeded or validation failure |
| 2 | Configuration or I/O error |
