#!/usr/bin/env python3
"""Validate release metadata and repository hygiene without Home Assistant."""

from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "custom_components"
DOMAIN = "pylontech_fh3x"
INTEGRATION = COMPONENTS / DOMAIN
REPOSITORY_URL = "https://github.com/pylontech-sw/HA-pylontech-force-H3X"
SEMANTIC_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
FORBIDDEN_TRACKED_PATTERNS = (
    re.compile(r"(^|/)__pycache__(/|$)"),
    re.compile(r"\.py[co]$"),
    re.compile(r"(^|/)node_modules(/|$)"),
    re.compile(r"^output/"),
    re.compile(r"(^|/)\.env($|\.)"),
    re.compile(r"\.(db|db-shm|db-wal|log|pem|key)$"),
    re.compile(r"^docs/.*\.docx$", re.IGNORECASE),
)


def _load_json(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        message = f"Unable to read valid JSON from {relative_path}: {err}"
        raise ValueError(message) from err
    if not isinstance(value, dict):
        raise ValueError(f"{relative_path} must contain a JSON object")
    return value


def _key_paths(value: Any, prefix: str = "") -> set[str]:
    if not isinstance(value, dict):
        return set()
    paths: set[str] = set()
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        paths.add(path)
        paths.update(_key_paths(child, path))
    return paths


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _png_dimensions(relative_path: str) -> tuple[int, int] | None:
    path = ROOT / relative_path
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def validate() -> list[str]:
    """Return all repository validation errors."""
    errors: list[str] = []
    integration_directories = sorted(
        path.name for path in COMPONENTS.iterdir() if path.is_dir()
    )
    if integration_directories != [DOMAIN]:
        errors.append(
            "custom_components must contain only "
            f"{DOMAIN}; found {integration_directories}"
        )

    try:
        manifest = _load_json(f"custom_components/{DOMAIN}/manifest.json")
        hacs = _load_json("hacs.json")
        strings = _load_json(f"custom_components/{DOMAIN}/strings.json")
        english = _load_json(f"custom_components/{DOMAIN}/translations/en.json")
        chinese = _load_json(f"custom_components/{DOMAIN}/translations/zh-Hans.json")
    except ValueError as err:
        return [str(err)]

    required_manifest_keys = {
        "domain",
        "name",
        "codeowners",
        "config_flow",
        "documentation",
        "integration_type",
        "iot_class",
        "issue_tracker",
        "requirements",
        "version",
    }
    missing = sorted(required_manifest_keys - manifest.keys())
    if missing:
        errors.append(f"manifest.json is missing keys: {', '.join(missing)}")
    if manifest.get("domain") != DOMAIN:
        errors.append(f"manifest domain must be {DOMAIN}")
    if manifest.get("documentation") != REPOSITORY_URL:
        errors.append("manifest documentation URL must point to this repository")
    if manifest.get("issue_tracker") != f"{REPOSITORY_URL}/issues":
        errors.append("manifest issue_tracker URL must point to this repository")
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMANTIC_VERSION.fullmatch(version):
        errors.append("manifest version must use MAJOR.MINOR.PATCH")
    else:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        if f"## {version} " not in changelog:
            errors.append(f"CHANGELOG.md has no section for {version}")

    if hacs.get("name") != manifest.get("name"):
        errors.append("hacs.json and manifest.json names must match")
    if hacs.get("render_readme") is not True:
        errors.append("hacs.json must enable render_readme")

    reference_keys = _key_paths(strings)
    for language, translation in (("en", english), ("zh-Hans", chinese)):
        translation_keys = _key_paths(translation)
        missing_keys = sorted(reference_keys - translation_keys)
        extra_keys = sorted(translation_keys - reference_keys)
        if missing_keys:
            errors.append(
                f"{language} translation is missing: {', '.join(missing_keys)}"
            )
        if extra_keys:
            errors.append(
                f"{language} translation has extra keys: {', '.join(extra_keys)}"
            )

    required_brand_dimensions = {
        f"custom_components/{DOMAIN}/brand/icon.png": (256, 256),
        f"custom_components/{DOMAIN}/brand/icon@2x.png": (512, 512),
    }
    for relative_path, expected_dimensions in required_brand_dimensions.items():
        dimensions = _png_dimensions(relative_path)
        if dimensions is None:
            errors.append(f"{relative_path} must be a valid PNG")
        elif dimensions != expected_dimensions:
            errors.append(
                f"{relative_path} must be {expected_dimensions[0]}x"
                f"{expected_dimensions[1]}; found {dimensions[0]}x{dimensions[1]}"
            )

    for tracked_file in _tracked_files():
        if any(pattern.search(tracked_file) for pattern in FORBIDDEN_TRACKED_PATTERNS):
            errors.append(
                f"forbidden generated or sensitive file is tracked: {tracked_file}"
            )

    return errors


def main() -> int:
    """Run validation and print an actionable result."""
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Repository metadata, translations, and tracked files are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
