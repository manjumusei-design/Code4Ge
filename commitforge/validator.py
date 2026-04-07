"""Conventional Commit format validation & rule enforcement."""

from __future__ import annotations

import re
from typing import List, Tuple

from commitforge.types import Config

_COMMIT_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\(.+\))?!?: .{1,72}$"
)


def validate_commit_message(
    message: str, config: Config
) -> Tuple[bool, List[str]]:
    """Validate *message* against Conventional Commit rules.

    Returns ``(is_valid, list_of_violations)``.
    """
    violations: List[str] = []
    lines = message.splitlines()
    header = lines[0]

    if not header.strip():
        violations.append("Commit header must not be empty.")
        return False, violations

    if not _COMMIT_RE.match(header):
        violations.append(
            "Header does not match Conventional Commit format: "
            "type(scope)?: description (<=72 chars)"
        )

    ctype = header.split("(")[0].split("!")[0]
    valid_types = set(config.commit_mappings.values())
    if ctype not in valid_types:
        violations.append(
            f"Type '{ctype}' is not in configured commit_mappings: {sorted(valid_types)}"
        )

    if len(header) > 72:
        violations.append(
            f"Header length is {len(header)} chars; maximum is 72."
        )

    if len(lines) > 1 and lines[1].strip():
        violations.append("Second line must be blank before body.")

    if not _is_imperative(header):
        violations.append(
            "Header should use imperative mood (e.g., 'add', not 'added')."
        )

    return len(violations) == 0, violations


def _is_imperative(header: str) -> bool:
    """Heuristic: reject headers starting with past-tense verbs."""
    past_markers = {
        "added", "fixed", "updated", "removed",
        "changed", "bumped", "deleted", "modified",
    }
    words = header.split(":", 1)
    if len(words) > 1:
        first_word = words[1].strip().split()[0].lower() if words[1].strip() else ""
        return first_word not in past_markers
    return True
