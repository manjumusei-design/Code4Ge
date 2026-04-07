"""Tests for commitforge.analyzer module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commitforge.analyzer import (
    _check_thresholds,
    _classify,
    _map_commit_type,
    analyze_changes,
)
from commitforge.types import Config, ScanResult


class TestAnalyzeChanges:
    def test_threshold_evaluation(self, tmp_repo: Path) -> None:
        config = Config(severity_thresholds={"info": 2})
        scan_result = ScanResult(files_scanned=5)
        with patch(
            "commitforge.analyzer._get_changed_files",
            return_value=[
                ("src/a.py", "M"),
                ("src/b.py", "M"),
            ],
        ):
            result = analyze_changes(tmp_repo, config, scan_result)
        assert result.thresholds_exceeded is True

    def test_empty_repo(self, tmp_repo: Path) -> None:
        config = Config()
        scan_result = ScanResult(files_scanned=0)
        with patch(
            "commitforge.analyzer._get_changed_files", return_value=[]
        ):
            result = analyze_changes(tmp_repo, config, scan_result)
        assert result.findings == []
        assert result.thresholds_exceeded is False

    def test_commit_type_mapping(self) -> None:
        config = Config()
        assert _map_commit_type("tests/unit.py", config) == "test"
        assert _map_commit_type("docs/readme.md", config) == "docs"

    def test_severity_counting(self) -> None:
        assert _classify("src/main.py", "M") == "info"
        assert _classify("tests/test_main.py", "M") == "warning"

    def test_check_thresholds(self) -> None:
        assert _check_thresholds({"warning": 3}, {"warning": 3}) is True
        assert _check_thresholds({"warning": 2}, {"warning": 3}) is False
        assert _check_thresholds({}, {"critical": 1}) is False
