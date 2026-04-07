"""Tests for commitforge.config module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from commitforge.config import (
    _coerce_dict,
    _coerce_float,
    _coerce_list,
    _deep_merge,
    create_default_config,
    load_config,
    validate_config,
)
from commitforge.types import Config


class TestLoadConfig:
    def test_missing_config_returns_defaults(self, tmp_repo: Path) -> None:
        cfg = load_config(tmp_repo)
        assert isinstance(cfg, Config)
        assert cfg.max_file_size_mb == 0.5

    def test_malformed_json_falls_back(self, tmp_repo: Path) -> None:
        (tmp_repo / ".commitforge.json").write_text("{not json")
        cfg = load_config(tmp_repo)
        assert cfg.max_file_size_mb == 0.5

    def test_invalid_utf8_falls_back(self, tmp_repo: Path) -> None:
        (tmp_repo / ".commitforge.json").write_bytes(b"\x80\x81\x82")
        cfg = load_config(tmp_repo)
        assert cfg.max_file_size_mb == 0.5

    def test_permission_error_falls_back(self, tmp_repo: Path) -> None:
        cfg_file = tmp_repo / ".commitforge.json"
        cfg_file.write_text("{}")
        with patch("builtins.open", side_effect=PermissionError):
            cfg = load_config(tmp_repo)
        assert cfg.max_file_size_mb == 0.5

    def test_valid_config_merges(self, tmp_repo: Path) -> None:
        (tmp_repo / ".commitforge.json").write_text(
            json.dumps({"max_file_size_mb": 2.0})
        )
        cfg = load_config(tmp_repo)
        assert cfg.max_file_size_mb == 2.0


class TestCreateDefaultConfig:
    def test_creates_file(self, tmp_repo: Path) -> None:
        create_default_config(tmp_repo)
        assert (tmp_repo / ".commitforge.json").exists()
        data = json.loads((tmp_repo / ".commitforge.json").read_text())
        assert data["max_file_size_mb"] == 0.5

    def test_does_not_overwrite(self, tmp_repo: Path) -> None:
        cfg_file = tmp_repo / ".commitforge.json"
        cfg_file.write_text('{"custom": true}')
        create_default_config(tmp_repo)
        assert json.loads(cfg_file.read_text()) == {"custom": True}


class TestValidateConfig:
    def test_path_normalization(self) -> None:
        raw = {"ignore_paths": ["node_modules\\", "dist/"]}
        cfg = validate_config(raw)
        assert "node_modules" in cfg.ignore_paths
        assert "dist" in cfg.ignore_paths

    def test_boolean_float_rejection(self) -> None:
        raw = {"max_file_size_mb": True}
        cfg = validate_config(raw)
        assert cfg.max_file_size_mb == 0.5

    def test_out_of_bounds_float(self) -> None:
        raw = {"max_file_size_mb": 9999.0}
        cfg = validate_config(raw)
        assert cfg.max_file_size_mb == 0.5

    def test_list_coercion(self) -> None:
        raw = {"ignore_paths": "not_a_list"}
        cfg = validate_config(raw)
        assert cfg.ignore_paths == [
            "node_modules", ".git", ".venv", "__pycache__", "dist", "build"
        ]

    def test_dict_coercion(self) -> None:
        raw = {"severity_thresholds": "bad"}
        cfg = validate_config(raw)
        assert cfg.severity_thresholds == {"warning": 3, "critical": 1}


class TestHelpers:
    def test_deep_merge_nested(self) -> None:
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 10}}
        result = _deep_merge(base, override)
        assert result["a"]["b"] == 10
        assert result["a"]["c"] == 2

    def test_deep_merge_no_mutation(self) -> None:
        base = {"x": 1}
        _deep_merge(base, {"y": 2})
        assert "y" not in base

    def test_coerce_float_bounds(self) -> None:
        assert _coerce_float(0.005, 0.5, 0.01, 1024.0) == 0.5
        assert _coerce_float(2048.0, 0.5, 0.01, 1024.0) == 0.5

    def test_coerce_float_bool_guard(self) -> None:
        assert _coerce_float(True, 0.5, 0.01, 1024.0) == 0.5

    def test_deep_merge_conflicts(self) -> None:
        """When override has a non-dict value for a dict key, override wins."""
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": "replaced"}
        result = _deep_merge(base, override)
        assert result["a"] == "replaced"

    def test_deep_merge_preserves_base_keys(self) -> None:
        """Keys only in base should be preserved."""
        base = {"x": 1, "y": {"z": 10}}
        override = {"y": {"w": 20}}
        result = _deep_merge(base, override)
        assert result["x"] == 1
        assert result["y"] == {"z": 10, "w": 20}
