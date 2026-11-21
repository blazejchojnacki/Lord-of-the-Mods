"""
@file tests/python/test_version_sync.py
@brief Guardrail test ensuring package, CMake, and documentation versions stay synchronized.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

import pytest

import lotm

REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_doc_file(candidates: tuple[str, ...]) -> Path:
    """Return the first existing repository file from `candidates`."""
    for rel in candidates:
        candidate = REPO_ROOT / rel
        if candidate.is_file():
            return candidate
    pytest.skip(f"None of {candidates} found in repository root")


def _parse_version_tuple(raw: str) -> tuple[int, ...]:
    """Parse leading numeric segments of a version string like '0.10.0' into an integer tuple."""
    parts = re.findall(r"\d+", raw.split("-", 1)[0])
    return tuple(int(p) for p in parts)


def test_version_consistency_across_project_files() -> None:
    """Verify pyproject.toml version matches runtime metadata, CMakeLists.txt, and docs."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    expected_version: str = data["project"]["version"]
    expected_tuple = _parse_version_tuple(expected_version)
    major_minor = ".".join(expected_version.split(".")[:2])

    # Runtime package __version__
    assert lotm.__version__ == expected_version

    # CMakeLists.txt fallback/resolved version
    cmake_text = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "_lotm_pyproject" in cmake_text
    assert f'_lotm_fallback_version "{expected_version}"' in cmake_text

    # CHANGELOG (latest heading matches expected_version using numeric tuple comparison)
    changelog_path = _find_doc_file(("CHANGELOG.md", "docs/CHANGELOG.md"))
    changelog_text = changelog_path.read_text(encoding="utf-8")
    headings = re.findall(r"^##\s+\[?v?(\d+\.\d+\.\d+(?:[a-zA-Z0-9._-]*)?)\]?", changelog_text, re.MULTILINE)
    assert headings, f"No versioned release heading found in {changelog_path.name}"
    parsed_headings = [_parse_version_tuple(h) for h in headings]
    assert headings[0] == expected_version, (
        f"Latest {changelog_path.name} heading ({headings[0]}) != pyproject.toml ({expected_version})"
    )
    assert max(parsed_headings) == expected_tuple, (
        f"Highest numeric version in {changelog_path.name} ({max(parsed_headings)}) != {expected_tuple}"
    )

    # SECURITY.md (supported version table references current major.minor or full version)
    security_path = _find_doc_file(("SECURITY.md", "docs/SECURITY.md"))
    security_text = security_path.read_text(encoding="utf-8")
    assert expected_version in security_text or f"{major_minor}.x" in security_text, (
        f"{security_path.name} does not mention {expected_version} or {major_minor}.x"
    )

    # coverage-log (latest entry mentions expected_version)
    coverage_path = _find_doc_file(("coverage-log.md", "coverage-log.txt", "coverage-log", "docs/coverage-log.md"))
    coverage_text = coverage_path.read_text(encoding="utf-8")
    assert expected_version in coverage_text, (
        f"{coverage_path.name} does not contain current version {expected_version}"
    )
