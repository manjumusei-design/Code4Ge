"""Tests for commitforge.generator module — stdlib unittest only."""

import unittest

from commitforge.generator import (
    suggest_commit, _infer_type, _infer_scope,
    _build_summary, _build_body, _is_config_only,
)
from commitforge.types import Config, DiffResult, FileChange


def _make_result(files: list) -> DiffResult:
    return DiffResult(files=files, repo_root="/fake")


class TestGenerator(unittest.TestCase):

    def test_suggest_commit_empty(self) -> None:
        result = _make_result([])
        commit = suggest_commit(result, Config())
        self.assertEqual(commit["type"], "chore")
        self.assertEqual(commit["summary"], "initial commit")

    def test_suggest_commit_single_file(self) -> None:
        files = [FileChange(path="src/main.py", additions=10, deletions=3)]
        commit = suggest_commit(_make_result(files), Config())
        self.assertIn(commit["type"], ("refactor", "feat"))
        self.assertLessEqual(len(commit["summary"]), 72)

    def test_infer_type_feat_heavy(self) -> None:
        files = [
            FileChange(path="src/a.py", status="A"),
            FileChange(path="src/b.py", status="A"),
            FileChange(path="src/c.py", status="A"),
            FileChange(path="src/d.py", status="A"),
        ]
        self.assertEqual(_infer_type(files), "feat")

    def test_infer_type_fix_keyword(self) -> None:
        files = [FileChange(path="src/fix_bug.py")]
        self.assertEqual(_infer_type(files), "fix")

    def test_infer_type_docs(self) -> None:
        files = [FileChange(path="docs/readme.md")]
        self.assertEqual(_infer_type(files), "docs")

    def test_infer_type_config_only(self) -> None:
        files = [FileChange(path=".gitignore"), FileChange(path="pyproject.toml")]
        self.assertEqual(_infer_type(files), "chore")

    def test_infer_scope_from_top_dir(self) -> None:
        files = [
            FileChange(path="src/a.py"), FileChange(path="src/b.py"),
            FileChange(path="tests/c.py"),
        ]
        self.assertEqual(_infer_scope(files), "src")

    def test_infer_scope_fallback(self) -> None:
        self.assertEqual(_infer_scope([]), "core")

    def test_build_summary_length(self) -> None:
        files = [FileChange(path=f"src/f{i}.py") for i in range(100)]
        summary = _build_summary(files, "feat")
        self.assertLessEqual(len(summary), 72)

    def test_build_body_max_lines(self) -> None:
        files = [FileChange(path=f"src/f{i}.py") for i in range(15)]
        body = _build_body(files)
        lines = body.strip().splitlines()
        self.assertLessEqual(len(lines), 11)
