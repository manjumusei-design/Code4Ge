"""Anti pattern detectionand code health scanning for commitforge """

from __future__ import annotations

import ast
import fnmatch
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

#Data models

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

@dataclass
class Issue:
    """A single health issue found in a file"""
    file: str
    rule: str
    severity: str
    message: str
    line: Optional[int] = None
    
    
@dataclass
class ScanResult:
    """Aggregrated output of a health scan"""
    issues: List[Issue] = field(default_factory=list)
    files_scanned: int = 0
    summary: Dict[str, int] = field(default_factory=dict)
    
#Public API

def scan_repo(
    repo_root: Path,
    ignored_paths: Sequence[str] | None = None,
    max_file_size_kb: float = 500,
) -> ScanResult:
    """Run all of the built in scanners and health checks across *repo_root"""
    result = ScanResult()
    ignored = list(ignored_paths or [])
    
    for filepath in _iter_repo_files(repo_root, ignored):
        result.files_scanned += 1
        _check_large_file(filepath, repo_root, max_file_size_kb, result)
        _check_binary_in_repo(filepath, repo_root, result)
        if filepath.suffix == ".py":
            _check_python_issues(filepath, repo_root, result)
        _check_todo_fixme(filepath, repo_root, result)
        
    _check_untracked_config(repo_root, result)
    _build_summary(result)
    return result

# Individual checkers

def _check_large_file(
    filepath: Path, repo_root: Path, result: ScanResult
) -> None:
    """This is to detect binary files tracked by git"""
    if not _is_binaryu(filepath):
        return
    rel = filepath.relative_to(repo_root)
    result.issues.append(
        Issue(
            file=str(rel),
            rule="binary-file",
            severity=SEVERITY_INFO,
            message="Binary file detected in repository",
        )
    )
    
def _checl_python_issues(
    filepath: Path, repo_root: Path, result: ScanResult
) -> None:
    """Run python specific checks such as unused imports and missing docstrings for example"""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 
    
    try: 
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return 
    
    rel = filepath.relative_to(repo_root)
    _check_unused_imports(tree,source,str(rel), result)
    _check_missing_docstrings(tree,str(rel), result)
    
    
def _check_unused_imports(
    tree: ast.Module, source:str, rel_path: str, result: ScanResult
) -> None:
    """Very basic unused-import detector via AST name tracking. This is not super perfect but can catch common cases."""
    
    imported_names : Dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                key = alias.asname or alias.name
                imported_names[key] = node.lineno
        elif isinstance(node,ast.ImportFrom):
            for alias in node.names:
                key = alias.asname or alias.name
                imported_names[key]= node.lineno
    
    for name, lineno in imported_names.items():
        if not _name_used_elsewhere(name,tree):
            result.issues.append(
                Issue(
                    file=rel_path,
                    rule="unsued-import",
                    severity=SEVERITY_WARNING,
                    message=f"Possible unused import '{name}'",
                    line=lineno,
                )
            )
            
def _name_used_elsewhere(name: str, tree: ast.Module) -> bool:
    """Return true if the *name* appears in a non importing context"""
    for node in ast.walk(tree):
        if isinstance(node,ast.Name) and node.id == name:
            if not isinstance(node.ctx, ast.Store):
                return True
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == name:
                return True
    return False

                
                                
def _check_missing_docstrings(
    tree: ast.Module, rel_path: str, result: ScanResult
) -> None:
    """This function is to flag public functions and classes that do not have docstrings"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            if not ast.get_docstring(node):
                result.issues.append(
                    Issue(
                        file=rel_path,
                        rule="missing-docstring",
                        severity=SEVERITY_INFO,
                        message=f"'{node.name}' lacks a docstring",
                        line=node.lineno,
                    )
                )
                

        
        
def _check_todo_fixme(
    filepath: Path, repo_root: Path, result: ScanResult
) -> None:
    """Counts excessive TODO or FIXME comments which can be a sign of self technical doubt or things which the author may have forgotten or have not fully finished before pushing changes"""
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return

    count = 0
    for lineno, line in enumerate(lines, start=1):
        count += len(re.findall(r"\b(TODO|FIXME|XXX|HACK)\b", line, re.IGNORECASE))

    if count >= 5:
        rel = filepath.relative_to(repo_root)
        result.issues.append(
            Issue(
                file=str(rel),
                rule="excessive-todo",
                severity=SEVERITY_WARNING,
                message=f"{count} TODO/FIXME markers detected",
            )
        )
        
def _check_untracked_config(repo_root: Path, result: ScanResult) -> None:
    """Warn about config-like files that are tracked by git which can indictate a missing git ignore entry"""
    config_patterns = ["*.env", ".env.*", "config.json", "config.yaml", "config.yml"]
    try:
        import subprocess
        
        output = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        ).stdout
    except Exception:
        return
    
    for line in output.splitlines():
        name = Path(line.strip()).name
        if any(fnmatch.fnmatch(name, pat) for pat in config_patterns):
            result.issues.append(
                Issue(
                    file=line.strip(),
                    rule="untracked-config",
                    severity=SEVERITY_CRITICAL,
                    message="Untracked config-like file detected, consider adding it to .gitignore",
                )
            )

# Helper function

BINARY_EXTENSIONS = {".pyc", ".pyo", ".so", ".dll", ".exe", ".png", ".jpg", ".gif"}

def _is_binary(filepath: Path) -> bool:
    """Quick heuristic for extension check and null-byte scan"""
    if filepath.suffix in BINARY_EXTENSIONS:
        return True
    try:
        chunk = filepath.read_bytes()[8192]
    except OSError:
        return False
    return b"\x00" in chunk


def _iter_repo_files(repo_root: Path, ignored: Sequence[str]) -> List[Path]:
    """Yield files under *repo_root*, skipping ignored patterns."""
    skipped_dirs = {".git"}
    for pattern in ignored:
        skipped_dirs.add(Path(pattern).parts[0])
        
    files: List[Path] =[]
    for root, dirs, filenames in repo_root.walk():
        dirs[:] = [
            d for d in dirs
            if d not in skipped_dirs and not _matches_any(d, ignored)
        ]
        for fname in filenames:
            if _matches_any(fname, ignored):
                continue
            files.append(root / fname)
        return files
    
    def _matches_any(name: str, patterns: Sequence[str]) -> bool:
        """Populate result.summary with severity counts"""
        summary: Dict [str, int] = {}
        for issue in result.issues:
            summary[issue.severity] = summary.get(issue.severity, 0) + 1
        result.summary = summary 
        