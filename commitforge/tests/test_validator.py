"""Tests for commitforge.validator module."""

from __future__ import annotations

import pytest

from commitforge.types import Config
from commitforge.validator import validate_commit_message


class TestValidateCommitMessage:
    def test_valid_standard(self) -> None:
        config = Config()
        valid, violations = validate_commit_message("chore(core): add feature", config)
        assert valid is True
        assert violations == []

    def test_valid_with_scope_and_breaking(self) -> None:
        config = Config()
        valid, violations = validate_commit_message(
            "chore(api)!: patch endpoint", config
        )
        assert valid is True

    def test_invalid_type(self) -> None:
        config = Config()
        valid, violations = validate_commit_message("update: change stuff", config)
        assert valid is False
        assert any("Conventional Commit" in v for v in violations)

    def test_invalid_too_long(self) -> None:
        config = Config()
        msg = "feat(core): " + "a" * 100
        valid, violations = validate_commit_message(msg, config)
        assert valid is False
        assert any("72" in v for v in violations)

    def test_blank_separator_before_body(self) -> None:
        config = Config()
        msg = "feat(core): add feature\nThis is the body"
        valid, violations = validate_commit_message(msg, config)
        assert valid is False
        assert any("Second line must be blank" in v for v in violations)

    def test_past_tense_rejection(self) -> None:
        config = Config()
        valid, violations = validate_commit_message(
            "fix(core): fixed the bug", config
        )
        assert valid is False
        assert any("imperative" in v for v in violations)

    def test_type_not_in_config(self) -> None:
        config = Config(commit_mappings={"feat": "feat"})
        valid, violations = validate_commit_message("build: add CI", config)
        assert valid is False
        assert any("not in configured" in v for v in violations)
