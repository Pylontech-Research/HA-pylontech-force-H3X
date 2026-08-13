"""Tests for FH3X alarm decoding independent of Home Assistant runtime."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE = "pylontech_fh3x_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components" / "pylontech_fh3x")]
sys.modules[PACKAGE] = package


def load(name: str):
    path = ROOT / "custom_components" / "pylontech_fh3x" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ALARM = load("alarm_history")


class TestAlarmHistory(unittest.TestCase):
    def test_known_and_unknown_bms_bits(self) -> None:
        attrs = ALARM.alarm_attributes(
            {
                "bms_alarm_status_1": (1 << 0) | (1 << 8) | (1 << 15),
                "bms_alarm_status_2": 1 << 7,
            },
            "bms_alarm",
        )
        self.assertEqual(len(attrs["active_issue_ids"]), 4)
        self.assertIn("Cell low-voltage alarm", attrs["active_issues"])
        self.assertIn("Charge overcurrent alarm", attrs["active_issues"])
        self.assertIn("Unknown alarm bit 23", attrs["active_issues"])
        self.assertEqual(attrs["unknown_bits_2"], [7])

    def test_empty_bms_alarm_is_empty(self) -> None:
        attrs = ALARM.alarm_attributes(
            {"bms_alarm_status_1": 0, "bms_alarm_status_2": 0}, "bms_alarm"
        )
        self.assertEqual(attrs["active_issues"], [])
        self.assertEqual(attrs["active_issue_ids"], [])

    def test_tracker_emits_only_transition_events(self) -> None:
        emitted: list[tuple[str, dict]] = []

        class Bus:
            def async_fire(self, event_type: str, data: dict) -> None:
                emitted.append((event_type, data))

        class Hass:
            bus = Bus()

        @dataclass(frozen=True)
        class Identity:
            serial: str = "FH3X-TEST"
            model: str = "Force H3X"

        @dataclass(frozen=True)
        class Snapshot:
            identity: Identity
            values: dict

        tracker = ALARM.AlarmEventTracker(Hass(), "FH3X-TEST", "Force H3X")
        normal = Snapshot(
            Identity(), {"bms_alarm_status_1": 0, "bms_alarm_status_2": 0}
        )
        alarm = Snapshot(Identity(), {"bms_alarm_status_1": 1, "bms_alarm_status_2": 0})
        tracker.process(normal)
        tracker.process(alarm)
        tracker.process(alarm)
        tracker.process(normal)
        logbook = [event for event in emitted if event[0] == "logbook_entry"]
        self.assertEqual(
            [item[1]["status"] for item in logbook], ["triggered", "recovered"]
        )

    def test_partial_snapshot_does_not_record_recovery(self) -> None:
        emitted: list[tuple[str, dict]] = []

        class Bus:
            def async_fire(self, event_type: str, data: dict) -> None:
                emitted.append((event_type, data))

        class Hass:
            bus = Bus()

        @dataclass(frozen=True)
        class Identity:
            serial: str = "FH3X-TEST"
            model: str = "Force H3X"

        @dataclass(frozen=True)
        class Snapshot:
            identity: Identity
            values: dict

        tracker = ALARM.AlarmEventTracker(Hass(), "FH3X-TEST", "Force H3X")
        tracker.process(
            Snapshot(Identity(), {"bms_alarm_status_1": 1, "bms_alarm_status_2": 0})
        )
        tracker.process(Snapshot(Identity(), {"bms_alarm_status_1": 0}))
        logbook = [event for event in emitted if event[0] == "logbook_entry"]
        self.assertEqual([item[1]["status"] for item in logbook], ["startup"])


if __name__ == "__main__":
    unittest.main()
