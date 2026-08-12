"""FH3X Modbus register definitions and decoding.

This module intentionally has no Home Assistant or pymodbus imports so the
protocol layer can be tested independently.
"""

from __future__ import annotations

import math
import struct
from collections.abc import Mapping
from dataclasses import dataclass

PCS_IDENTITY_ADDRESS = 30010
PCS_IDENTITY_COUNT = 31
PCS_DEVICE_INFO_EXT_ADDRESS = 30036
PCS_DEVICE_INFO_EXT_COUNT = 43
PCS_MONITOR_ADDRESS = 30100
PCS_MONITOR_COUNT = 99
PCS_MONITOR_EXT_ADDRESS = 30600
PCS_MONITOR_EXT_COUNT = 70

PCS_ACTIVE_POWER_CONTROL_ADDRESS = 40400
PCS_ACTIVE_POWER_CONTROL_COUNT = 3
PCS_INTERNAL_CONTROL_ADDRESS = 40848
PCS_INTERNAL_CONTROL_COUNT = 1
PCS_ENERGY_MANAGEMENT_ADDRESS = 40901
PCS_ENERGY_MANAGEMENT_COUNT = 31
PCS_PEAK_SHAVING_ADDRESS = 40973
PCS_PEAK_SHAVING_COUNT = 3

BMS_SYSTEM_ADDRESS = 0x1100
BMS_SYSTEM_COUNT = 0x114F - BMS_SYSTEM_ADDRESS
BMS_PILE_ADDRESS = 0x1400
BMS_LOAD_ENERGY_ADDRESS = BMS_PILE_ADDRESS + 0x0691
BMS_PARALLEL_LOAD_ENERGY_ADDRESS = BMS_PILE_ADDRESS + 0x06D1
BMS_LOAD_ENERGY_COUNT = 2
BMS_DEVICE_INFO_ADDRESS = 0x1000
BMS_DEVICE_INFO_COUNT = 0x101F - BMS_DEVICE_INFO_ADDRESS
BMS_PILE_HEADER_COUNT = 0x60
BMS_PILE_NOMINAL_ADDRESS = BMS_PILE_ADDRESS + 0x3A
BMS_PILE_NOMINAL_COUNT = 2
BMS_MODULE_VOLTAGE_OFFSET = 0x60
BMS_MODULE_TEMPERATURE_OFFSET = 0xB0
BMS_CELL_VOLTAGE_OFFSET = 0x100
BMS_CELL_TEMPERATURE_OFFSET = 0x400

FH3XValue = int | float | str


def update_u16_bit(value: int, bit_index: int, enabled: bool) -> int:
    """Return a U16 value with one bit updated and all other bits preserved."""
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"U16 value out of range: {value}")
    if not 0 <= bit_index <= 15:
        raise ValueError(f"U16 bit index out of range: {bit_index}")
    mask = 1 << bit_index
    return value | mask if enabled else value & ~mask


# Values exposed with SensorStateClass.TOTAL_INCREASING.  Some PCS firmware can
# return a single torn Float32 read while the counter is changing.  Passing that
# one-off regression to Home Assistant makes Recorder interpret it as a meter
# reset and permanently inflates Energy Dashboard totals.
TOTAL_INCREASING_KEYS = frozenset(
    {
        "pv_total_energy",
        "grid_import_energy",
        "grid_export_energy",
        "battery_charge_energy",
        "battery_discharge_energy",
        "battery_charge_energy_from_ac",
        "eps_output_energy",
        "home_load_energy",
        "bms_charge_energy_today",
        "bms_discharge_energy_today",
    }
)


class TotalIncreasingGuard:
    """Reject isolated cumulative-meter regressions and implausible jumps.

    A baseline is not published until it is confirmed by a second poll.  This
    prevents a bad first read after an integration reload from becoming the
    Recorder baseline.  A genuine device reset is accepted after the new,
    lower baseline is seen in two consecutive polls.  The first lower sample
    is held back so a torn two-register read cannot corrupt Home Assistant
    long-term statistics.  A large increase is handled the same way: it must
    be repeated by the next poll before it is accepted.
    """

    MAX_TOTAL_KWH = 1_000_000_000
    MAX_UNCONFIRMED_CHANGE_KWH = 10
    INITIAL_CONFIRM_TOLERANCE_KWH = 1

    def __init__(self) -> None:
        self._last: dict[str, int | float] = {}
        self._initial_candidate: dict[str, int | float] = {}
        self._reset_candidate: dict[str, int | float] = {}
        self._increase_candidate: dict[str, int | float] = {}

    def apply(self, values: dict[str, FH3XValue]) -> None:
        """Stabilize cumulative values in place."""
        for key in TOTAL_INCREASING_KEYS:
            value = values.get(key)
            if not isinstance(value, int | float):
                continue

            if not math.isfinite(value) or value < 0 or value > self.MAX_TOTAL_KWH:
                previous = self._last.get(key)
                if previous is None:
                    values.pop(key, None)
                else:
                    values[key] = previous
                continue

            previous = self._last.get(key)
            if previous is None:
                candidate = self._initial_candidate.get(key)
                if (
                    candidate is not None
                    and abs(value - candidate) <= self.INITIAL_CONFIRM_TOLERANCE_KWH
                ):
                    self._last[key] = value
                    self._initial_candidate.pop(key, None)
                    self._reset_candidate.pop(key, None)
                    self._increase_candidate.pop(key, None)
                    continue

                self._initial_candidate[key] = value
                values.pop(key, None)
                continue

            if value >= previous:
                increase = value - previous
                if increase <= self.MAX_UNCONFIRMED_CHANGE_KWH:
                    self._last[key] = value
                    self._reset_candidate.pop(key, None)
                    self._increase_candidate.pop(key, None)
                    continue

                candidate = self._increase_candidate.get(key)
                if (
                    candidate is not None
                    and value >= candidate
                    and value - candidate <= self.MAX_UNCONFIRMED_CHANGE_KWH
                ):
                    self._last[key] = value
                    self._reset_candidate.pop(key, None)
                    self._increase_candidate.pop(key, None)
                    continue

                self._increase_candidate[key] = value
                self._reset_candidate.pop(key, None)
                values[key] = previous
                continue

            self._increase_candidate.pop(key, None)
            candidate = self._reset_candidate.get(key)
            if (
                candidate is not None
                and value >= candidate
                and value - candidate <= self.MAX_UNCONFIRMED_CHANGE_KWH
            ):
                # A second sample at or above the lower baseline confirms a
                # real counter reset. Recorder can now handle the decrease.
                self._last[key] = value
                self._reset_candidate.pop(key, None)
                continue

            self._reset_candidate[key] = value
            values[key] = previous


class FH3XDecodeError(ValueError):
    """Raised when a Modbus response cannot be decoded."""


@dataclass(frozen=True)
class FH3XIdentity:
    """Stable identity read from the PCS."""

    manufacturer: str
    model: str
    serial: str
    software_version: str


@dataclass(frozen=True)
class FH3XSnapshot:
    """A complete immutable polling result."""

    identity: FH3XIdentity
    values: Mapping[str, FH3XValue]
    pcs_registers: tuple[int, ...]
    bms_registers: tuple[int, ...]


INVERTER_STATES = {
    0: "waiting",
    1: "normal",
    2: "fault",
}

BATTERY_STATES = {
    0: "sleeping",
    1: "charging",
    2: "discharging",
    3: "idle",
    4: "standby",
    5: "running",
    6: "fault",
    7: "offline",
}


def _require(registers: list[int], minimum: int, block: str) -> None:
    if len(registers) < minimum:
        raise FH3XDecodeError(
            f"{block} response has {len(registers)} registers; expected {minimum}"
        )


def _u16(registers: list[int], offset: int) -> int:
    return registers[offset] & 0xFFFF


def _s16(registers: list[int], offset: int) -> int:
    return struct.unpack(">h", struct.pack(">H", _u16(registers, offset)))[0]


def _u32(registers: list[int], offset: int) -> int:
    return (_u16(registers, offset) << 16) | _u16(registers, offset + 1)


def _s32(registers: list[int], offset: int) -> int:
    return struct.unpack(">i", struct.pack(">I", _u32(registers, offset)))[0]


def _float32(registers: list[int], offset: int) -> float:
    return struct.unpack(">f", struct.pack(">I", _u32(registers, offset)))[0]


def _ascii(registers: list[int], offset: int, register_count: int) -> str:
    raw = b"".join(
        struct.pack(">H", _u16(registers, index))
        for index in range(offset, offset + register_count)
    )
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()


def _version(registers: list[int], offset: int) -> str:
    raw = b"".join(struct.pack(">H", _u16(registers, i)) for i in (offset, offset + 1))
    return "V" + ".".join(str(part) for part in raw)


def _clock(register: int) -> str:
    hour = (register >> 8) & 0xFF
    minute = register & 0xFF
    return f"{hour:02d}:{minute:02d}" if hour < 24 and minute < 60 else "invalid"


def _weekdays(register: int) -> str:
    days = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")
    return ",".join(day for bit, day in enumerate(days) if register & (1 << bit))


def decode_identity(registers: list[int]) -> FH3XIdentity:
    """Decode PCS registers 30010 through 30040."""
    _require(registers, PCS_IDENTITY_COUNT, "PCS identity")
    return FH3XIdentity(
        manufacturer=_ascii(registers, 0, 8) or "Pylontech",
        model=_ascii(registers, 8, 8) or "Force H3X",
        serial=_ascii(registers, 16, 8),
        software_version=_version(registers, 29),
    )


def decode_device_info_ext(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode PCS device information from registers 30036 through 30078."""
    _require(registers, PCS_DEVICE_INFO_EXT_COUNT, "PCS extended device information")
    return {
        "pcs_max_output_power": _u16(registers, 0),
        "pcs_software_version": _version(registers, 3),
        "pcs_safety_type": _u16(registers, 9),
        "pcs_apparent_power_rating": _u16(registers, 11),
        "pcs_parallel_mode": _u16(registers, 19),
        "pcs_parallel_address": _u16(registers, 20),
        "pcs_afci_firmware_version": _version(registers, 25),
        "pcs_extended_serial": _ascii(registers, 27, 8),
        "pcs_parallel_machine_count": _u16(registers, 35),
        "pcs_discharge_rated_fixed_q": _u16(registers, 39),
        "pcs_charge_rated_fixed_q": _u16(registers, 40),
        "pcs_discharge_rated_cosphi": _u16(registers, 41),
        "pcs_charge_rated_cosphi": _u16(registers, 42),
    }


def decode_pcs(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode PCS monitor registers 30100 through 30198 (device address 2)."""
    _require(registers, PCS_MONITOR_COUNT, "PCS monitor")

    pv1_voltage = _u16(registers, 19) * 0.1
    pv1_current = _u16(registers, 20) * 0.1
    pv2_voltage = _u16(registers, 21) * 0.1
    pv2_current = _u16(registers, 22) * 0.1
    pv3_voltage = _u16(registers, 23) * 0.1
    pv3_current = _u16(registers, 24) * 0.1
    pv_power = _s32(registers, 27)
    grid_power = _s32(registers, 8)
    battery_power = _s32(registers, 62)
    grid_voltage_raw = tuple(_u16(registers, offset) for offset in (31, 33, 35))
    grid_current_raw = tuple(_u16(registers, offset) for offset in (32, 34, 36))
    grid_voltages = tuple(value * 0.1 for value in grid_voltage_raw)
    grid_currents = tuple(value * 0.1 for value in grid_current_raw)
    ac_output_substate = _u16(registers, 60)

    values: dict[str, FH3XValue] = {
        "ac_total_power": _s32(registers, 0),
        "ac_apparent_power": _s32(registers, 2),
        "ac_reactive_power": _s32(registers, 4),
        "ac_power_factor": round(_u16(registers, 6) * 0.01, 2),
        "ac_power_factor_direction": _u16(registers, 7),
        "grid_power": grid_power,
        "third_party_meter_power": _s32(registers, 10),
        "third_party_meter_energy": round(_float32(registers, 12), 3),
        "load_power": pv_power + grid_power + battery_power,
        "inverter_state": INVERTER_STATES.get(_u16(registers, 15), "unknown"),
        "inverter_waiting_time": _u16(registers, 16),
        "fault_code": _u16(registers, 17),
        "warning_code": _u16(registers, 18),
        "pv1_voltage": round(pv1_voltage, 1),
        "pv1_current": round(pv1_current, 1),
        "pv1_power": round(pv1_voltage * pv1_current),
        "pv2_voltage": round(pv2_voltage, 1),
        "pv2_current": round(pv2_current, 1),
        "pv2_power": round(pv2_voltage * pv2_current),
        "pv3_voltage": round(pv3_voltage, 1),
        "pv3_current": round(pv3_current, 1),
        "pv3_power": round(pv3_voltage * pv3_current),
        "pv_total_power": pv_power,
        "pv_total_energy": round(_float32(registers, 29), 3),
        "grid_voltage_r": round(grid_voltages[0], 1),
        "grid_current_r": round(grid_currents[0], 1),
        "grid_voltage_s": round(grid_voltages[1], 1),
        "grid_current_s": round(grid_currents[1], 1),
        "grid_voltage_t": round(grid_voltages[2], 1),
        "grid_current_t": round(grid_currents[2], 1),
        "grid_line_voltage_rs": round(_u16(registers, 37) * 0.1, 1),
        "grid_line_voltage_st": round(_u16(registers, 38) * 0.1, 1),
        "grid_line_voltage_tr": round(_u16(registers, 39) * 0.1, 1),
        "grid_frequency": round(_u16(registers, 40) * 0.01, 2),
        "bus_voltage": round(_u16(registers, 41) * 0.1, 1),
        "isolation_resistance": _u16(registers, 42),
        "dc_injection_current": _s16(registers, 43),
        "ground_fault_current": _s16(registers, 44),
        "neutral_pe_voltage": round(_s16(registers, 45) * 0.1, 1),
        "inverter_ambient_temperature": round(_s16(registers, 46) * 0.1, 1),
        "inverter_heatsink_temperature": round(_s16(registers, 47) * 0.1, 1),
        "fault_bits": _u32(registers, 48),
        "warning_bits": _u32(registers, 50),
        "firmware_update_state": _u16(registers, 52),
        "inverter_boost_temperature": round(_s16(registers, 53) * 0.1, 1),
        "ac_output_energy": round(_float32(registers, 54), 3),
        "grid_import_energy": round(_float32(registers, 56), 3),
        "grid_export_energy": round(_float32(registers, 58), 3),
        "ac_output_substate": ac_output_substate,
        "grid_operating_mode": {1: "grid_tied", 2: "backup"}.get(
            ac_output_substate, "unknown"
        ),
        "battery_state": BATTERY_STATES.get(_u16(registers, 61), "unknown"),
        "battery_power": battery_power,
        "battery_voltage": round(_u16(registers, 64) * 0.1, 1),
        "battery_current": round(_s16(registers, 65) * 0.1, 1),
        "charge_forbidden_mask": _u16(registers, 66),
        "discharge_forbidden_mask": _u16(registers, 67),
        "forced_charge_request": _u16(registers, 68),
        "eps_voltage": round(_u16(registers, 70) * 0.1, 1),
        "eps_frequency": round(_u16(registers, 71) * 0.01, 2),
        "eps_power": _s32(registers, 72),
        "battery_charge_energy": round(_float32(registers, 74), 3),
        "battery_discharge_energy": round(_float32(registers, 76), 3),
        "battery_charge_energy_from_ac": round(_float32(registers, 78), 3),
        "eps_output_energy": round(_float32(registers, 80), 3),
        "battery_soc": _u16(registers, 82),
        "ct_current_r": round(_s16(registers, 83) * 0.1, 1),
        "ct_current_s": round(_s16(registers, 84) * 0.1, 1),
        "ct_current_t": round(_s16(registers, 85) * 0.1, 1),
        "grid_power_r": _s32(registers, 86),
        "grid_power_s": _s32(registers, 88),
        "grid_power_t": _s32(registers, 90),
        "bus_p_to_m_voltage": round(_u16(registers, 97) * 0.1, 1),
    }
    if all(value != 0xFFFF for value in grid_voltage_raw):
        values["average_grid_voltage"] = round(sum(grid_voltages) / 3, 1)
    if all(value != 0xFFFF for value in grid_current_raw):
        values["average_grid_current"] = round(sum(grid_currents) / 3, 1)
    return values


def decode_pcs_monitor_ext(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode PCS extended monitor registers 30600 through 30669."""
    _require(registers, PCS_MONITOR_EXT_COUNT, "PCS extended monitor")
    return {
        "backup_current_r": round(_u16(registers, 0) * 0.1, 1),
        "backup_current_s": round(_u16(registers, 1) * 0.1, 1),
        "backup_current_t": round(_u16(registers, 2) * 0.1, 1),
        "backup_power_r": _s32(registers, 3),
        "backup_power_s": _s32(registers, 5),
        "backup_power_t": _s32(registers, 7),
        "ac_output_power_r": _s32(registers, 9),
        "ac_output_power_s": _s32(registers, 11),
        "ac_output_power_t": _s32(registers, 13),
        "backup_voltage_r": round(_u16(registers, 15) * 0.1, 1),
        "backup_voltage_s": round(_u16(registers, 16) * 0.1, 1),
        "backup_voltage_t": round(_u16(registers, 17) * 0.1, 1),
        "meter_voltage_r": round(_u16(registers, 18) * 0.1, 1),
        "meter_voltage_s": round(_u16(registers, 19) * 0.1, 1),
        "meter_voltage_t": round(_u16(registers, 20) * 0.1, 1),
        "meter_reactive_power": _s32(registers, 21),
        "fan_enabled": bool(_u16(registers, 25)),
        "fault_bits_extended": _u32(registers, 26),
        "warning_bits_extended": _u32(registers, 28),
        "parallel_slave_state": _u16(registers, 31),
        "parallel_pv_power": _s32(registers, 32),
        "parallel_battery_power": _s32(registers, 34),
        "parallel_backup_power_r": _s32(registers, 36),
        "parallel_backup_power_s": _s32(registers, 38),
        "parallel_backup_power_t": _s32(registers, 40),
        "parallel_ac_output_power_r": _s32(registers, 42),
        "parallel_ac_output_power_s": _s32(registers, 44),
        "parallel_ac_output_power_t": _s32(registers, 46),
        "parallel_battery_capacity_ah": _u16(registers, 48),
        "battery_capacity": round(_u16(registers, 49) * 0.01, 2),
        "parallel_pcs_rated_power": _u32(registers, 50),
        "parallel_reactive_power": _s32(registers, 52),
        "acc_power_r": _s32(registers, 54),
        "acc_power_s": _s32(registers, 56),
        "acc_power_t": _s32(registers, 58),
        "meter_power_factor": round(_s16(registers, 60) * 0.001, 3),
        "meter_grid_frequency": round(_u16(registers, 61) * 0.1, 1),
        "grid_to_battery_energy": round(_float32(registers, 62), 3),
        "battery_to_grid_energy": round(_float32(registers, 64), 3),
        "grid_to_eps_energy": round(_float32(registers, 66), 3),
        "battery_to_eps_energy": round(_float32(registers, 68), 3),
    }


def decode_bms_load_energy(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode the BMS lifetime home-load counter from U32 Wh to kWh."""
    _require(registers, BMS_LOAD_ENERGY_COUNT, "BMS load energy")
    return {"home_load_energy": round(_u32(registers, 0) * 0.001, 3)}


def decode_bms_nominal_capacity(
    registers: list[int], pile_count: int = 1
) -> dict[str, FH3XValue]:
    """Decode one BMS pile's nominal voltage/Ah and total nominal energy."""
    _require(registers, BMS_PILE_NOMINAL_COUNT, "BMS nominal capacity")
    nominal_voltage = round(_u16(registers, 0) * 0.1, 1)
    nominal_capacity_ah = _u16(registers, 1)
    effective_pile_count = max(1, pile_count)
    values: dict[str, FH3XValue] = {
        "bms_pile_nominal_voltage": nominal_voltage,
        "bms_pile_nominal_capacity": nominal_capacity_ah,
        "battery_capacity_pile_count": effective_pile_count,
    }
    if nominal_voltage > 0 and nominal_capacity_ah > 0:
        values["battery_capacity"] = round(
            nominal_voltage * nominal_capacity_ah * effective_pile_count / 1000,
            2,
        )
        values["battery_capacity_source"] = "bms_nominal"
    return values


def decode_active_power_controls(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode PCS registers 40400 through 40402 (device address 2)."""
    _require(registers, PCS_ACTIVE_POWER_CONTROL_COUNT, "PCS active power control")
    return {
        "active_power_control_mode": _u16(registers, 0),
        "meter_export_power_max": _s32(registers, 1),
    }


def decode_internal_controls(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode the supported PCS internal-control register block."""
    _require(registers, PCS_INTERNAL_CONTROL_COUNT, "PCS internal control")
    return {"heat_pump_enabled": bool(_u16(registers, 0))}


def decode_energy_management_controls(
    registers: list[int],
) -> dict[str, FH3XValue]:
    """Decode PCS registers 40901 through 40931 (device address 2)."""
    _require(registers, PCS_ENERGY_MANAGEMENT_COUNT, "PCS energy management")
    return {
        "charge_discharge_power_reference": round(_s16(registers, 0) * 0.1, 1),
        "charge_limit_soc": _u16(registers, 1),
        "eps_limit_soc_on_grid": _u16(registers, 2),
        "eps_enabled": bool(_u16(registers, 3)),
        "eps_limit_soc_off_grid": _u16(registers, 4),
        "ems_mode": _u16(registers, 6),
        "period_1_enabled": bool(_u16(registers, 7)),
        "period_1_start": _clock(_u16(registers, 8)),
        "period_1_end": _clock(_u16(registers, 9)),
        "period_1_mode": "discharge" if _u16(registers, 10) else "charge",
        "period_1_power": round(_u16(registers, 11) * 0.1, 1),
        "period_1_weekdays": _weekdays(_u16(registers, 12)),
        "period_1_weekday_mask": _u16(registers, 12),
        "period_2_enabled": bool(_u16(registers, 13)),
        "period_2_start": _clock(_u16(registers, 14)),
        "period_2_end": _clock(_u16(registers, 15)),
        "period_2_mode": "discharge" if _u16(registers, 16) else "charge",
        "period_2_power": round(_u16(registers, 17) * 0.1, 1),
        "period_2_weekdays": _weekdays(_u16(registers, 18)),
        "period_2_weekday_mask": _u16(registers, 18),
        "period_3_enabled": bool(_u16(registers, 19)),
        "period_3_start": _clock(_u16(registers, 20)),
        "period_3_end": _clock(_u16(registers, 21)),
        "period_3_mode": "discharge" if _u16(registers, 22) else "charge",
        "period_3_power": round(_u16(registers, 23) * 0.1, 1),
        "period_3_weekdays": _weekdays(_u16(registers, 24)),
        "period_3_weekday_mask": _u16(registers, 24),
        "period_4_enabled": bool(_u16(registers, 25)),
        "period_4_start": _clock(_u16(registers, 26)),
        "period_4_end": _clock(_u16(registers, 27)),
        "period_4_mode": "discharge" if _u16(registers, 28) else "charge",
        "period_4_power": round(_u16(registers, 29) * 0.1, 1),
        "period_4_weekdays": _weekdays(_u16(registers, 30)),
        "period_4_weekday_mask": _u16(registers, 30),
    }


def decode_peak_shaving_controls(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode PCS registers 40973 through 40975."""
    _require(registers, PCS_PEAK_SHAVING_COUNT, "PCS peak shaving")
    return {
        "peak_shaving_enabled": bool(_u16(registers, 0)),
        "peak_shaving_safety_soc": _u16(registers, 1),
        "peak_shaving_meter_power_limit": _u16(registers, 2),
    }


def decode_bms(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode BMS system registers from 0x1100 (device address 1)."""
    _require(registers, BMS_SYSTEM_COUNT, "BMS system")

    cell_max_voltage = _u16(registers, 16) * 0.001
    cell_min_voltage = _u16(registers, 17) * 0.001

    return {
        "bms_basic_status": _u16(registers, 0),
        "bms_protection_status": _u16(registers, 1),
        "bms_alarm_status_1": _u16(registers, 2),
        "bms_alarm_status_2": _u16(registers, 0x114E - BMS_SYSTEM_ADDRESS),
        "bms_total_voltage": round(_u16(registers, 3) * 0.1, 1),
        "bms_current": round(_s32(registers, 4) * 0.01, 2),
        "bms_temperature": round(_s16(registers, 6) * 0.1, 1),
        "bms_soc": _u16(registers, 7),
        "bms_cycles": _u16(registers, 8),
        "bms_max_charge_voltage": round(_u16(registers, 9) * 0.1, 1),
        "bms_max_charge_current": round(_u32(registers, 10) * 0.01, 2),
        "bms_min_discharge_voltage": round(_u16(registers, 12) * 0.1, 1),
        "bms_max_discharge_current": round(_s32(registers, 13) * 0.01, 2),
        "bms_switching_status": _u16(registers, 15),
        "bms_cell_voltage_max": round(cell_max_voltage, 3),
        "bms_cell_voltage_min": round(cell_min_voltage, 3),
        "bms_cell_voltage_delta": round((cell_max_voltage - cell_min_voltage) * 1000),
        "bms_cell_voltage_max_channel": _u16(registers, 18),
        "bms_cell_voltage_min_channel": _u16(registers, 19),
        "bms_cell_temperature_max": round(_s16(registers, 20) * 0.1, 1),
        "bms_cell_temperature_min": round(_s16(registers, 21) * 0.1, 1),
        "bms_cell_temperature_max_channel": _u16(registers, 22),
        "bms_cell_temperature_min_channel": _u16(registers, 23),
        "bms_module_voltage_max": round(_u16(registers, 24) * 0.01, 2),
        "bms_module_voltage_min": round(_u16(registers, 25) * 0.01, 2),
        "bms_module_voltage_max_channel": _u16(registers, 26),
        "bms_module_voltage_min_channel": _u16(registers, 27),
        "bms_module_temperature_max": round(_s16(registers, 28) * 0.1, 1),
        "bms_module_temperature_min": round(_s16(registers, 29) * 0.1, 1),
        "bms_module_temperature_max_channel": _u16(registers, 30),
        "bms_module_temperature_min_channel": _u16(registers, 31),
        "bms_soh": _u16(registers, 32),
        "bms_remaining_energy": round(_u32(registers, 33) / 1000, 3),
        "bms_charge_energy_rolling": round(_u32(registers, 35) / 1000, 3),
        "bms_discharge_energy_rolling": round(_u32(registers, 37) / 1000, 3),
        "bms_charge_energy_today": round(_u32(registers, 39) / 1000, 3),
        "bms_discharge_energy_today": round(_u32(registers, 41) / 1000, 3),
        "bms_charge_energy_total": _u32(registers, 43),
        "bms_discharge_energy_total": _u32(registers, 45),
        "bms_force_charge_requested": bool(_u16(registers, 47)),
        "bms_balance_charge_requested": bool(_u16(registers, 48)),
        "bms_parallel_pile_count": _u16(registers, 49),
        "bms_error_code_1": _u32(registers, 50),
        "bms_error_code_2": _u32(registers, 52),
        "bms_module_count": _u16(registers, 54),
        "bms_cell_count": _u16(registers, 55),
        "bms_charge_forbidden": bool(_u16(registers, 56)),
        "bms_discharge_forbidden": bool(_u16(registers, 57)),
        "bms_low_soc": bool(_u16(registers, 58)),
        "bms_soe": _u16(registers, 59),
        "bms_heartbeat": _u16(registers, 60),
        "bms_module_pcb_temperature_max": round(_s16(registers, 61) * 0.1, 1),
        "bms_module_pcb_temperature_min": round(_s16(registers, 62) * 0.1, 1),
        "bms_module_pcb_temperature_max_channel": _u16(registers, 63),
        "bms_module_pcb_temperature_min_channel": _u16(registers, 64),
        "bms_system_operation_status": _u16(registers, 65),
        "bms_insulation_resistance": _u16(registers, 72),
        "bms_insulation_error_level": _u16(registers, 73),
        "bms_terminal_temperature_max": round(_s16(registers, 74) * 0.1, 1),
        "bms_terminal_temperature_min": round(_s16(registers, 75) * 0.1, 1),
        "bms_terminal_temperature_max_channel": _u16(registers, 76),
        "bms_terminal_temperature_min_channel": _u16(registers, 77),
    }


def decode_bms_device_info(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode BMS equipment information from 0x1000 through 0x101E."""
    _require(registers, BMS_DEVICE_INFO_COUNT, "BMS device information")
    main_version = _u16(registers, 10)
    hmi_version = _u16(registers, 30)
    return {
        "bms_manufacturer": _ascii(registers, 0, 5),
        "bms_device_type": _ascii(registers, 5, 5),
        "bms_main_version": f"V{main_version >> 8}.{main_version & 0xFF}",
        "bms_internal_version": _u16(registers, 11),
        "bms_configured_parallel_piles": _u16(registers, 12),
        "bms_local_parallel_address": _u16(registers, 13),
        "bms_product_model": _ascii(registers, 14, 16),
        "bms_hmi_version": f"V{hmi_version >> 8}.{hmi_version & 0xFF}",
    }


def decode_bms_pile_header(registers: list[int]) -> dict[str, FH3XValue]:
    """Decode single-pile header at BMS 0x1400."""
    _require(registers, BMS_PILE_HEADER_COUNT, "BMS pile header")
    return {
        "bms_pile_basic_status": _u16(registers, 0),
        "bms_pile_protection_status": _u16(registers, 1),
        "bms_pile_alarm_status_1": _u16(registers, 2),
        "bms_pile_total_voltage": round(_u16(registers, 3) * 0.1, 1),
        "bms_pile_current": round(_s32(registers, 4) * 0.01, 2),
        "bms_pile_temperature": round(_s16(registers, 6) * 0.1, 1),
        "bms_pile_soc": _u16(registers, 7),
        "bms_pile_cycles": _u16(registers, 8),
        "bms_pile_soh": _u16(registers, 32),
        "bms_pile_module_count": _u16(registers, 54),
        "bms_pile_cell_count": _u16(registers, 55),
        "bms_pile_nominal_voltage": round(_u16(registers, 58) * 0.1, 1),
        "bms_pile_nominal_capacity": _u16(registers, 59),
        "bms_pile_soe": _u16(registers, 72),
        "bms_pile_alarm_status_2": _u16(registers, 73),
        "bms_pile_serial": _ascii(registers, 80, 16),
    }


def decode_bms_detail_values(
    module_voltages: list[int],
    module_temperatures: list[int],
    cell_voltages: list[int],
    cell_temperatures: list[int],
) -> dict[str, FH3XValue]:
    """Decode dynamic module and cell arrays from the BMS pile region."""
    values: dict[str, FH3XValue] = {}
    for index, value in enumerate(module_voltages, start=1):
        values[f"bms_module_{index:02d}_voltage"] = round(value * 0.01, 2)
    for index, value in enumerate(module_temperatures, start=1):
        values[f"bms_module_{index:02d}_temperature"] = round(
            struct.unpack(">h", struct.pack(">H", value & 0xFFFF))[0] * 0.1, 1
        )
    for index, value in enumerate(cell_voltages, start=1):
        values[f"bms_cell_{index:03d}_voltage"] = round(value * 0.001, 3)
    for index, value in enumerate(cell_temperatures, start=1):
        values[f"bms_cell_{index:03d}_temperature"] = round(
            struct.unpack(">h", struct.pack(">H", value & 0xFFFF))[0] * 0.1, 1
        )
    return values
