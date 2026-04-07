# CommitForge Demo

## Step-by-Step Walkthrough

### 1. Initialize

```
$ python -m commitforge --repo /path/to/myrepo init
Config created at: /path/to/myrepo/.commitforge.json
```

### 2. Scan (suggest commit)

```
$ python -m commitforge --repo /path/to/myrepo scan
Branch: main
Files changed: 3
Suggested: feat(src): add 3 files
- added: src/auth.py
- modified: src/main.py
- added: tests/test_auth.py
```

### 3. Health Check

```
$ python -m commitforge --repo /path/to/myrepo health
=== CommitForge ===
  health(repo): Health check
  No issues found.
```

Or with issues:

```
=== CommitForge ===
  health(repo): Health check
  Issues: 0 critical, 2 warnings, 0 info

  [WARNING] src/legacy.py -- 5 TODO/FIXME markers
  [WARNING] assets/logo.png -- Binary content detected
```

### 4. Full Analysis → HTML

```
$ python -m commitforge --repo /path/to/myrepo analyze --format html --output report.html
```

## Sample Repo Setup (for reviewers)

```bash
mkdir demo-repo && cd demo-repo && git init
echo 'def hello(): pass' > app.py
echo '# TODO: implement this' >> app.py
git add . && git commit -m "init"
echo 'def world(): pass' >> app.py
python -m commitforge scan
```

## Screenshot/GIF Instructions

1. Install `asciinema`: `pip install asciinema` (or use terminal recording)
2. Run: `asciinema rec demo.cast`
3. Execute commands above
4. Stop: `Ctrl+D`
5. Upload to asciinema.io or convert to GIF with `agg`
