"""Shared paths for standalone integration tests."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT_PATH = ROOT / "custom_components" / "pylontech_fh3x"
