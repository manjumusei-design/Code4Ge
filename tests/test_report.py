import tempfile
"""Tests for commitforge.report module — stdlib unittest only."""

import unittest
from pathlib import Path

from commitforge.report import (
    render_terminal, render_markdown, render_html,
    write_output, _count_severities, _truncate,
)
from commitforge.types import Issue


def _make_commit() -> dict:
    return {
        "type": "feat", "scope": "api",
        "summary": "add user endpoint", "body": "- added /users route\n- added tests",
    }


def _make_issues() -> list:
    return [
        Issue("src/app.py", "large-file", "warning", "Exceeds 0.5 MB", line=None),
        Issue("src/old.py", "excessive-todo", "critical", "10 TODOs", line=1),
        Issue("src/new.py", "unused-import", "info", "'os' unused", line=3),
    ]


class TestRenderTerminal(unittest.TestCase):

    def test_prints_without_error(self) -> None:
        render_terminal(_make_commit(), [])

    def test_shows_no_issues(self) -> None:
        render_terminal(_make_commit(), [])  # should not raise


class TestRenderMarkdown(unittest.TestCase):

    def test_header_present(self) -> None:
        md = render_markdown(_make_commit(), [])
        self.assertIn("# CommitForge Report", md)

    def test_commit_fields(self) -> None:
        md = render_markdown(_make_commit(), [])
        self.assertIn("feat", md)
        self.assertIn("api", md)

    def test_issues_table(self) -> None:
        md = render_markdown(_make_commit(), _make_issues())
        self.assertIn("| File |", md)
        self.assertIn("src/app.py", md)


class TestRenderHtml(unittest.TestCase):

    def test_doctype(self) -> None:
        html = render_html(_make_commit(), [])
        self.assertIn("<!DOCTYPE html>", html)

    def test_responsive_meta(self) -> None:
        html = render_html(_make_commit(), [])
        self.assertIn("viewport", html)

    def test_issues_table_html(self) -> None:
        html = render_html(_make_commit(), _make_issues())
        self.assertIn("<table>", html)
        self.assertIn("<thead>", html)


class TestWriteOutput(unittest.TestCase):

    def test_write_to_file(self) -> None:
        d = Path(tempfile.mkdtemp())
        out = d / "report.md"
        write_output("# Test", out)
        content = out.read_text(encoding="utf-8")
        self.assertIn("# Test", content)


class TestHelpers(unittest.TestCase):

    def test_count_severities(self) -> None:
        issues = _make_issues()
        counts = _count_severities(issues)
        self.assertEqual(counts["warning"], 1)
        self.assertEqual(counts["critical"], 1)
        self.assertEqual(counts["info"], 1)

    def test_truncate_short(self) -> None:
        self.assertEqual(_truncate("hi", 80), "hi")

    def test_truncate_long(self) -> None:
        result = _truncate("a" * 100, 10)
        self.assertEqual(len(result), 10)
        self.assertTrue(result.endswith("..."))
