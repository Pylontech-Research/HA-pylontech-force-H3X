"""Tests for FH3X polling resilience policy."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

RESILIENCE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "pylontech_fh3x" / "resilience.py"
)
SPEC = importlib.util.spec_from_file_location("fh3x_resilience", RESILIENCE_PATH)
assert SPEC is not None and SPEC.loader is not None
RESILIENCE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RESILIENCE
SPEC.loader.exec_module(RESILIENCE)


class TestPollFailureState(unittest.TestCase):
    """Verify stale-data tolerance and recovery behavior."""

    def test_first_two_failures_preserve_last_snapshot(self) -> None:
        state = RESILIENCE.PollFailureState(failure_threshold=3)

        self.assertTrue(state.record_failure(has_snapshot=True))
        self.assertTrue(state.record_failure(has_snapshot=True))
        self.assertFalse(state.record_failure(has_snapshot=True))
        self.assertEqual(state.consecutive_failures, 3)
        self.assertTrue(state.stale)

    def test_first_refresh_failure_is_not_hidden(self) -> None:
        state = RESILIENCE.PollFailureState(failure_threshold=3)

        self.assertFalse(state.record_failure(has_snapshot=False))
        self.assertEqual(state.consecutive_failures, 1)
        self.assertFalse(state.stale)

    def test_success_resets_failure_state(self) -> None:
        state = RESILIENCE.PollFailureState(failure_threshold=3)
        state.record_failure(has_snapshot=True)
        state.record_failure(has_snapshot=True)

        self.assertEqual(state.record_success(), 2)
        self.assertEqual(state.consecutive_failures, 0)
        self.assertFalse(state.stale)


if __name__ == "__main__":
    unittest.main()
