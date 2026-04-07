"""Tests for commitforge.analyzer module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from commitforge.analyzer import (
    _check_thresholds,
    _classify_file,
    _map_commit_type,
    analyze_changes,
)
from commitforge.types import Config, ScanResult


class TestAnalyzeChanges:
    def test_threshold_evaluation(self, tmp_repo: Path) -> None:
        config = Config(severity_thresholds={"info": 1})
        scan_result = ScanResult(files_scanned=5)
        src_dir = tmp_repo / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("# test")
        with patch(
            "commitforge.analyzer._get_diff_stats",
            return_value={"src/a.py": {"added": 10, "removed": 5}},
        ), patch(
            "commitforge.analyzer._extract_functions_from_diff",
            return_value={},
        ), patch(
            "commitforge.analyzer._get_untracked_files",
            return_value=[],
        ):
            result = analyze_changes(tmp_repo, config, scan_result)
        assert result.thresholds_exceeded is True

    def test_empty_repo(self, tmp_repo: Path) -> None:
        config = Config()
        scan_result = ScanResult(files_scanned=0)
        with patch(
            "commitforge.analyzer._get_diff_stats",
            return_value={},
        ), patch(
            "commitforge.analyzer._extract_functions_from_diff",
            return_value={},
        ), patch(
            "commitforge.analyzer._get_untracked_files",
            return_value=[],
        ):
            result = analyze_changes(tmp_repo, config, scan_result)
        assert result.findings == []
        assert result.thresholds_exceeded is False

    def test_commit_type_mapping(self) -> None:
        config = Config()
        assert _map_commit_type("tests/unit.py", config) == "test"
        assert _map_commit_type("docs/readme.md", config) == "docs"

    def test_classify_file(self) -> None:
        assert _classify_file("src/main.py") == "info"
        assert _classify_file("tests/test_main.py") == "warning"
        assert _classify_file("assets/icon.exe") == "critical"

    def test_check_thresholds(self) -> None:
        assert _check_thresholds({"warning": 3}, {"warning": 3}) is True
        assert _check_thresholds({"warning": 2}, {"warning": 3}) is False
        assert _check_thresholds({}, {"critical": 1}) is False
