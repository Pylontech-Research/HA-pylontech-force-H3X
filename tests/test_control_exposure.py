"""Tests for the standalone FH3X control-exposure policy."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

EXPOSURE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "pylontech_fh3x" / "exposure.py"
)
SPEC = importlib.util.spec_from_file_location("fh3x_exposure", EXPOSURE_PATH)
assert SPEC is not None and SPEC.loader is not None
EXPOSURE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPOSURE
SPEC.loader.exec_module(EXPOSURE)


class TestControlExposure(unittest.TestCase):
    """Verify the three native Home Assistant control tiers."""

    def test_daily_profile_has_six_controls_and_no_configuration(self) -> None:
        enabled = {
            key
            for key in EXPOSURE.ALL_WRITABLE_KEYS
            if EXPOSURE.control_enabled(key, EXPOSURE.CONTROL_PROFILE_DAILY)
        }
        self.assertEqual(enabled, EXPOSURE.DAILY_CONTROL_KEYS)
        self.assertEqual(len(enabled), 6)
        self.assertTrue(all(EXPOSURE.is_primary_control(key) for key in enabled))

    def test_basic_profile_adds_four_common_settings(self) -> None:
        enabled = {
            key
            for key in EXPOSURE.ALL_WRITABLE_KEYS
            if EXPOSURE.control_enabled(key, EXPOSURE.CONTROL_PROFILE_BASIC)
        }
        self.assertEqual(
            enabled,
            EXPOSURE.DAILY_CONTROL_KEYS | EXPOSURE.BASIC_CONFIG_KEYS,
        )
        self.assertEqual(len(EXPOSURE.DAILY_CONTROL_KEYS), 6)
        self.assertEqual(len(EXPOSURE.BASIC_CONFIG_KEYS), 4)

    def test_advanced_profile_has_eight_controls_and_52_configuration(self) -> None:
        enabled = {
            key
            for key in EXPOSURE.ALL_WRITABLE_KEYS
            if EXPOSURE.control_enabled(key, EXPOSURE.CONTROL_PROFILE_ADVANCED)
        }
        controls = {key for key in enabled if EXPOSURE.is_primary_control(key)}
        configuration = enabled - controls
        self.assertEqual(len(controls), 8)
        self.assertEqual(len(configuration), 52)
        self.assertEqual(enabled, EXPOSURE.ALL_WRITABLE_KEYS)

    def test_schedule_details_are_advanced_only(self) -> None:
        for key in EXPOSURE.SCHEDULE_CONFIG_KEYS:
            self.assertFalse(
                EXPOSURE.control_enabled(key, EXPOSURE.CONTROL_PROFILE_BASIC)
            )
            self.assertTrue(
                EXPOSURE.control_enabled(key, EXPOSURE.CONTROL_PROFILE_ADVANCED)
            )


if __name__ == "__main__":
    unittest.main()
