"""Alarm decoding and HA Logbook event tracking for FH3X."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .const import DOMAIN
from .protocol import FH3XSnapshot, FH3XValue

_LOGGER = logging.getLogger(__name__)

# These maps intentionally use stable bit positions.  The human-readable text
# is kept in this module so the coordinator and entity platform decode exactly
# the same alarm snapshot.
PCS_FAULTS = {
    0: "MCU fault",
    1: "Current sensor fault",
    2: "GFCI device fault",
    3: "Relay fault",
    4: "PV voltage high",
    5: "Isolation fault",
    6: "GFCI fault",
    7: "Overtemperature",
    8: "Grid missing",
    9: "Grid overvoltage",
    10: "Grid overfrequency",
    11: "DC injection current high",
    12: "Flash fault",
    13: "Main/voice MCU communication fault",
    14: "Bus voltage high",
    15: "Bus voltage low",
    16: "DRM S9 fault",
    17: "DRM S0 fault",
    18: "PE connection missing",
    19: "Bus voltage imbalance",
    20: "BMS communication failure",
    21: "CT not connected",
    22: "CT reverse connection",
    23: "Battery not connected",
    24: "Backup load overvoltage",
    25: "DC arc fault",
    26: "AFCI self-test fault",
    27: "Parallel address assignment fault",
    28: "Battery precharge circuit fault",
    29: "Battery protection GPIO fault",
    30: "Shutdown circuit fault",
    31: "Battery relay fault",
    32: "Meter communication fault",
    34: "Parallel slave CAN communication loss",
    35: "Parallel slave received master fault",
    36: "Parallel slave synchronization loss",
    39: "Parallel software version mismatch",
    40: "Battery voltage exceeds limit",
    42: "Parallel grid phase-order mismatch",
    43: "EPS voltage exceeds limit",
    44: "Grid phase fault",
}
PCS_WARNINGS = {
    0: "PV1 overcurrent",
    1: "PV2 overcurrent",
    2: "PV3 overcurrent",
    4: "PV1 undervoltage",
    5: "PV2 undervoltage",
    6: "PV3 undervoltage",
    8: "Bus overvoltage",
    9: "Bus undervoltage",
    10: "Inverter overcurrent",
    11: "Anti-islanding protection",
    12: "Grid peak overvoltage",
    13: "Firmware update active",
    14: "PE connection missing",
    15: "Grid voltage consistency warning",
    16: "Fan abnormal",
    17: "Backup load overload",
    18: "SPD failure",
    28: "Battery overcurrent",
    35: "First grid-connection parameters error",
    37: "Bus boost anomaly",
    38: "EPS instantaneous overcurrent",
}
BMS_PROTECTIONS = {
    0: "Cell undervoltage protection",
    1: "Cell overvoltage protection",
    2: "Pile undervoltage protection",
    3: "Pile overvoltage protection",
    4: "Charge low-temperature protection",
    5: "Charge high-temperature protection",
    6: "Discharge low-temperature protection",
    7: "Discharge high-temperature protection",
    8: "Charge overcurrent protection",
    9: "Discharge overcurrent protection",
    10: "Short-circuit protection",
    11: "Terminal temperature protection",
    12: "Module PCB overtemperature protection",
    13: "Module undervoltage protection",
    14: "Module overvoltage protection",
    15: "Secondary cell undervoltage protection",
}
BMS_ALARMS_1 = {
    0: "Cell low-voltage alarm",
    1: "Cell high-voltage alarm",
    2: "Pile low-voltage alarm",
    3: "Pile high-voltage alarm",
    4: "Charge low-temperature alarm",
    5: "Charge high-temperature alarm",
    6: "Discharge low-temperature alarm",
    7: "Discharge high-temperature alarm",
    8: "Charge overcurrent alarm",
    9: "Discharge overcurrent alarm",
    10: "Leakage current alarm",
    11: "BMS overtemperature alarm",
    12: "Module PCB high-temperature alarm",
    13: "Module low-voltage alarm",
    14: "Module high-voltage alarm",
    15: "Terminal temperature alarm",
}
BMS_ALARMS_2 = {
    0: "Cell-voltage imbalance alarm",
    1: "Cell-temperature imbalance alarm",
    2: "BMS communication lost alarm",
    3: "BMS disconnected alarm",
    4: "Abnormal system-use alarm",
    5: "LED communication timeout",
}


def decode_issue_bits(
    bits: int, names: Mapping[int, str], category: str, offset: int = 0
) -> tuple[list[str], list[str], list[int]]:
    """Return stable IDs, names, and unknown bit positions."""
    issue_ids: list[str] = []
    issue_names: list[str] = []
    unknown: list[int] = []
    for bit in range(max(bits.bit_length(), max(names, default=-1) + 1)):
        if not bits & (1 << bit):
            continue
        absolute_bit = bit + offset
        if bit in names:
            issue_ids.append(f"{category}_bit_{absolute_bit}")
            issue_names.append(names[bit])
        else:
            unknown.append(absolute_bit)
            issue_ids.append(f"{category}_unknown_bit_{absolute_bit}")
            issue_names.append(f"Unknown alarm bit {absolute_bit}")
    return issue_ids, issue_names, unknown


def alarm_attributes(data: Mapping[str, FH3XValue], category: str) -> dict[str, Any]:
    """Build consistent live attributes for one alarm category."""
    if category == "inverter_fault":
        raw1, raw2, names = (
            int(data.get("fault_bits", 0)),
            int(data.get("fault_bits_extended", 0)),
            PCS_FAULTS,
        )
        code = data.get("fault_code", 0)
    elif category == "inverter_warning":
        raw1, raw2, names = (
            int(data.get("warning_bits", 0)),
            int(data.get("warning_bits_extended", 0)),
            PCS_WARNINGS,
        )
        code = data.get("warning_code", 0)
    elif category == "bms_protection":
        raw1, raw2, names = (
            int(data.get("bms_protection_status", 0)),
            0,
            BMS_PROTECTIONS,
        )
        code = data.get("bms_error_code_1", 0)
    else:
        raw1, raw2 = (
            int(data.get("bms_alarm_status_1", 0)),
            int(data.get("bms_alarm_status_2", 0)),
        )
        ids1, names1, unknown1 = decode_issue_bits(raw1, BMS_ALARMS_1, category)
        ids2, names2, unknown2 = decode_issue_bits(raw2, BMS_ALARMS_2, category, 16)
        return {
            "active_issues": names1 + names2,
            "active_issue_ids": ids1 + ids2,
            "raw_status_1": raw1,
            "raw_status_2": raw2,
            "unknown_bits_1": unknown1,
            "unknown_bits_2": [bit - 16 for bit in unknown2],
        }
    combined = raw1 | (raw2 << 32)
    ids1, issue_names, unknown = decode_issue_bits(combined, names, category)
    return {
        "active_issues": issue_names,
        "active_issue_ids": ids1,
        "raw_status_1": raw1,
        "raw_status_2": raw2,
        "unknown_bits_1": [bit for bit in unknown if bit < 32],
        "unknown_bits_2": [bit - 32 for bit in unknown if bit >= 32],
        "fault_code"
        if category == "inverter_fault"
        else "warning_code"
        if category == "inverter_warning"
        else "error_code_1": code,
    }


class AlarmEventTracker:
    """Emit one Logbook event per alarm transition or changed bitmask."""

    def __init__(self, hass: Any, serial: str, model: str) -> None:
        self.hass = hass
        self.serial = serial
        self.model = model
        self._active: dict[str, tuple[Any, str, Mapping[str, Any], str]] = {}
        self._initialized = False

    def process(self, snapshot: FH3XSnapshot) -> None:
        self.serial = snapshot.identity.serial or self.serial
        self.model = snapshot.identity.model or self.model
        values = snapshot.values
        current = {
            "inverter_fault": alarm_attributes(values, "inverter_fault"),
            "inverter_warning": alarm_attributes(values, "inverter_warning"),
            "bms_protection": alarm_attributes(values, "bms_protection"),
            "bms_alarm": alarm_attributes(values, "bms_alarm"),
        }
        now = datetime.now(timezone.utc).isoformat()
        for category, attrs in current.items():
            required = {
                "inverter_fault": ("fault_bits", "fault_bits_extended"),
                "inverter_warning": ("warning_bits", "warning_bits_extended"),
                "bms_protection": ("bms_protection_status",),
                "bms_alarm": ("bms_alarm_status_1", "bms_alarm_status_2"),
            }[category]
            # A partial snapshot is a communication gap, not a recovery.  Keep
            # the previous active event until a complete block is read again.
            if not all(key in values for key in required):
                continue
            issue_ids = tuple(attrs["active_issue_ids"])
            signature = (
                issue_ids,
                attrs["raw_status_1"],
                attrs["raw_status_2"],
                attrs.get(
                    "error_code_1",
                    attrs.get("fault_code", attrs.get("warning_code", 0)),
                ),
            )
            active = bool(issue_ids)
            previous = self._active.get(category)
            if active and previous is None:
                self._active[category] = (signature, now, attrs, now)
                self._emit(
                    category,
                    attrs,
                    "startup" if not self._initialized else "triggered",
                    now,
                )
            elif active and previous is not None and previous[0] != signature:
                self._emit(category, attrs, "updated", now)
                self._active[category] = (signature, previous[1], attrs, now)
            elif not active and previous is not None:
                self._emit(
                    category, previous[2], "recovered", now, started_at=previous[1]
                )
                self._active.pop(category, None)
        self._initialized = True

    def live_metadata(self, category: str) -> dict[str, str]:
        """Return timestamps for an active alarm, if any."""
        active = self._active.get(category)
        if active is None:
            return {}
        return {"first_seen": active[1], "last_seen": active[3]}

    def _emit(
        self,
        category: str,
        attrs: Mapping[str, Any],
        status: str,
        now: str,
        *,
        started_at: str | None = None,
    ) -> None:
        slug = re.sub(r"[^a-z0-9_]+", "_", self.serial.lower()).strip("_") or "fh3x"
        entity_id = f"binary_sensor.{slug}_{category}"
        payload = {
            "event_type": "pylontech_fh3x_alarm",
            "device_id": self.serial,
            "device_name": self.model or self.serial,
            "category": category,
            "status": status,
            "issue_ids": attrs["active_issue_ids"],
            "issues": attrs["active_issues"],
            "raw_status_1": attrs["raw_status_1"],
            "raw_status_2": attrs["raw_status_2"],
            "error_code_1": attrs.get("error_code_1"),
            "error_code_2": attrs.get("error_code_2"),
            "timestamp": now,
            "started_at": started_at or now,
            "entity_id": entity_id,
        }
        try:
            self.hass.bus.async_fire("pylontech_fh3x_alarm", payload)
            self.hass.bus.async_fire(
                "logbook_entry",
                {
                    "name": f"FH3X {category}",
                    "message": "; ".join(attrs["active_issues"]) or status,
                    "domain": DOMAIN,
                    **payload,
                },
            )
        except Exception:  # pragma: no cover - HA event bus failures are non-fatal
            _LOGGER.exception("Unable to record FH3X alarm event")
