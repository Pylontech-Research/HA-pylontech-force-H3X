"""Product point mappings and derived values for the FH3X integration.

The product registration sheet uses names that are more descriptive than the
legacy entity keys.  This module keeps those names as a compatibility mapping
without changing existing entity IDs or the sign conventions used by the
integration.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

try:  # Keep this pure mapping module easy to exercise outside HA.
    from .protocol import FH3XIdentity, FH3XValue
except ImportError:  # pragma: no cover - only used by standalone protocol tests
    from protocol import FH3XIdentity, FH3XValue


def _number(values: Mapping[str, FH3XValue], key: str) -> float | None:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _set_alias(values: dict[str, FH3XValue], target: str, source: str) -> None:
    """Copy a legacy decoded value to a product registration key."""
    if target not in values and source in values:
        values[target] = values[source]


def _set_scaled_alias(
    values: dict[str, FH3XValue], target: str, source: str, scale: float
) -> None:
    """Copy and scale a raw protocol value for a product-facing entity."""
    value = _number(values, source)
    if target not in values and value is not None:
        values[target] = round(value * scale, 3)


def normalize_product_values(
    source: Mapping[str, FH3XValue], identity: FH3XIdentity
) -> dict[str, FH3XValue]:
    """Return the decoded snapshot with product registration keys populated.

    Only mappings with a documented source are added here.  Unsupported or
    ambiguous product rows intentionally remain absent so HA exposes them as
    unavailable instead of showing a misleading zero.
    """
    values = dict(source)

    values.setdefault("device_model", identity.model)
    values.setdefault("device_serial_number", identity.serial)
    _set_alias(values, "rated_power", "pcs_max_output_power")
    _set_alias(values, "pcs_state", "inverter_state")
    _set_alias(values, "ac_total_apparent_power", "ac_apparent_power")
    _set_scaled_alias(values, "inverter_power", "ac_total_power", 0.001)
    _set_scaled_alias(values, "inverter_reactive_power", "ac_reactive_power", 0.001)
    _set_alias(values, "ac_frequency", "grid_frequency")
    _set_alias(values, "battery_soc_bms", "bms_soc")
    _set_alias(values, "battery_soh", "bms_soh")
    _set_alias(values, "battery_temperature", "bms_temperature")
    _set_scaled_alias(values, "pv_power", "pv_total_power", 0.001)
    _set_alias(values, "pv_generation_energy", "pv_total_energy")
    _set_alias(values, "inverter_generation_energy", "ac_output_energy")

    for target, source in (("a", "r"), ("b", "s"), ("c", "t")):
        _set_alias(values, f"meter_phase_{target}_voltage", f"meter_voltage_{source}")

    for phase in ("r", "s", "t"):
        _set_alias(values, f"ac_phase_{phase}_voltage", f"grid_voltage_{phase}")
        _set_alias(values, f"ac_phase_{phase}_current", f"grid_current_{phase}")
        _set_alias(values, f"ct_phase_{phase}_current", f"ct_current_{phase}")

    charge_voltage = _number(values, "bms_max_charge_voltage")
    charge_current = _number(values, "bms_max_charge_current")
    if charge_voltage is not None and charge_current is not None:
        values["max_charge_power"] = round(charge_voltage * charge_current / 1000, 3)

    discharge_voltage = _number(values, "bms_min_discharge_voltage")
    discharge_current = _number(values, "bms_max_discharge_current")
    if discharge_voltage is not None and discharge_current is not None:
        values["max_discharge_power"] = round(
            discharge_voltage * abs(discharge_current) / 1000, 3
        )

    acc_phases = tuple(
        _number(values, f"acc_power_{phase}") for phase in ("r", "s", "t")
    )
    if all(value is not None for value in acc_phases):
        values["third_party_pv_power"] = round(sum(acc_phases) / 1000, 3)

    _set_scaled_alias(values, "grid_reactive_power", "meter_reactive_power", 0.001)

    fault = any(
        _number(values, key) not in (None, 0)
        for key in (
            "fault_code",
            "fault_bits",
            "fault_bits_extended",
            "bms_protection_status",
        )
    )
    alarm = any(
        _number(values, key) not in (None, 0)
        for key in (
            "warning_code",
            "warning_bits",
            "warning_bits_extended",
            "bms_alarm_status_1",
            "bms_alarm_status_2",
        )
    )
    if fault:
        values["device_fault_status"] = "fault"
    elif alarm:
        values["device_fault_status"] = "alarm"
    elif any(
        key in values
        for key in (
            "fault_code",
            "warning_code",
            "fault_bits",
            "warning_bits",
            "bms_protection_status",
            "bms_alarm_status_1",
            "bms_alarm_status_2",
        )
    ):
        values["device_fault_status"] = "normal"

    code_parts = [
        str(int(number))
        for key in (
            "fault_code",
            "warning_code",
            "bms_error_code_1",
            "bms_error_code_2",
        )
        if (number := _number(values, key)) not in (None, 0)
    ]
    if code_parts or "device_fault_status" in values:
        values["current_alarm_code"] = ",".join(code_parts) or "0"

    return values
