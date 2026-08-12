"""Tests for the standalone FH3X protocol decoder."""

from __future__ import annotations

import importlib.util
import struct
import sys
import unittest
from pathlib import Path

PROTOCOL_PATH = (
    Path(__file__).parents[1] / "custom_components" / "pylontech_fh3x" / "protocol.py"
)
SPEC = importlib.util.spec_from_file_location("fh3x_protocol", PROTOCOL_PATH)
assert SPEC is not None and SPEC.loader is not None
PROTOCOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROTOCOL
SPEC.loader.exec_module(PROTOCOL)

BMS_SYSTEM_COUNT = PROTOCOL.BMS_SYSTEM_COUNT
BMS_DEVICE_INFO_COUNT = PROTOCOL.BMS_DEVICE_INFO_COUNT
BMS_PILE_HEADER_COUNT = PROTOCOL.BMS_PILE_HEADER_COUNT
PCS_ACTIVE_POWER_CONTROL_COUNT = PROTOCOL.PCS_ACTIVE_POWER_CONTROL_COUNT
PCS_DEVICE_INFO_EXT_COUNT = PROTOCOL.PCS_DEVICE_INFO_EXT_COUNT
PCS_ENERGY_MANAGEMENT_COUNT = PROTOCOL.PCS_ENERGY_MANAGEMENT_COUNT
PCS_INTERNAL_CONTROL_COUNT = PROTOCOL.PCS_INTERNAL_CONTROL_COUNT
PCS_IDENTITY_COUNT = PROTOCOL.PCS_IDENTITY_COUNT
PCS_MONITOR_COUNT = PROTOCOL.PCS_MONITOR_COUNT
PCS_MONITOR_EXT_COUNT = PROTOCOL.PCS_MONITOR_EXT_COUNT
PCS_PEAK_SHAVING_COUNT = PROTOCOL.PCS_PEAK_SHAVING_COUNT
FH3XDecodeError = PROTOCOL.FH3XDecodeError
TotalIncreasingGuard = PROTOCOL.TotalIncreasingGuard
decode_active_power_controls = PROTOCOL.decode_active_power_controls
decode_bms = PROTOCOL.decode_bms
decode_bms_detail_values = PROTOCOL.decode_bms_detail_values
decode_bms_device_info = PROTOCOL.decode_bms_device_info
decode_bms_load_energy = PROTOCOL.decode_bms_load_energy
decode_bms_nominal_capacity = PROTOCOL.decode_bms_nominal_capacity
decode_bms_pile_header = PROTOCOL.decode_bms_pile_header
decode_device_info_ext = PROTOCOL.decode_device_info_ext
decode_energy_management_controls = PROTOCOL.decode_energy_management_controls
decode_identity = PROTOCOL.decode_identity
decode_internal_controls = PROTOCOL.decode_internal_controls
decode_peak_shaving_controls = PROTOCOL.decode_peak_shaving_controls
decode_pcs = PROTOCOL.decode_pcs
decode_pcs_monitor_ext = PROTOCOL.decode_pcs_monitor_ext
update_u16_bit = PROTOCOL.update_u16_bit


def _put_ascii(registers: list[int], offset: int, count: int, value: str) -> None:
    raw = value.encode("ascii").ljust(count * 2, b"\x00")[: count * 2]
    for index in range(count):
        registers[offset + index] = int.from_bytes(
            raw[index * 2 : index * 2 + 2], "big"
        )


def _put_u32(registers: list[int], offset: int, value: int) -> None:
    registers[offset] = (value >> 16) & 0xFFFF
    registers[offset + 1] = value & 0xFFFF


def _put_s32(registers: list[int], offset: int, value: int) -> None:
    _put_u32(registers, offset, value & 0xFFFFFFFF)


def _put_float32(registers: list[int], offset: int, value: float) -> None:
    encoded = struct.unpack(">I", struct.pack(">f", value))[0]
    _put_u32(registers, offset, encoded)


class TestFH3XProtocol(unittest.TestCase):
    """Verify protocol decoding and sign conventions."""

    def _prime_total_guard(
        self, guard: TotalIncreasingGuard, key: str, value: float
    ) -> None:
        first = {key: value}
        guard.apply(first)
        self.assertNotIn(key, first)

        confirmed = {key: value}
        guard.apply(confirmed)
        self.assertEqual(confirmed[key], value)

    def test_u16_bit_updates_preserve_other_weekdays(self) -> None:
        weekday_mask = 0
        weekday_mask = update_u16_bit(weekday_mask, 1, True)
        weekday_mask = update_u16_bit(weekday_mask, 2, True)
        weekday_mask = update_u16_bit(weekday_mask, 5, True)
        self.assertEqual(weekday_mask, 0b0100110)

        weekday_mask = update_u16_bit(weekday_mask, 2, False)
        self.assertEqual(weekday_mask, 0b0100010)

    def test_bms_load_energy_offsets_include_pile_base(self) -> None:
        self.assertEqual(PROTOCOL.BMS_LOAD_ENERGY_ADDRESS, 0x1A91)
        self.assertEqual(PROTOCOL.BMS_PARALLEL_LOAD_ENERGY_ADDRESS, 0x1AD1)

    def test_u16_bit_update_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            update_u16_bit(-1, 0, True)
        with self.assertRaises(ValueError):
            update_u16_bit(0, 16, True)

    def test_total_increasing_guard_rejects_one_bad_sample(self) -> None:
        guard = TotalIncreasingGuard()
        self._prime_total_guard(guard, "battery_charge_energy", 107.488)

        torn_read = {"battery_charge_energy": 60.249}
        guard.apply(torn_read)
        self.assertEqual(torn_read["battery_charge_energy"], 107.488)

        recovered = {"battery_charge_energy": 107.510}
        guard.apply(recovered)
        self.assertEqual(recovered["battery_charge_energy"], 107.510)

    def test_total_increasing_guard_accepts_confirmed_reset(self) -> None:
        guard = TotalIncreasingGuard()
        self._prime_total_guard(guard, "grid_import_energy", 132.5)

        first_reset_sample = {"grid_import_energy": 0.0}
        guard.apply(first_reset_sample)
        self.assertEqual(first_reset_sample["grid_import_energy"], 132.5)

        confirmed_reset = {"grid_import_energy": 0.01}
        guard.apply(confirmed_reset)
        self.assertEqual(confirmed_reset["grid_import_energy"], 0.01)

    def test_total_increasing_guard_rejects_one_huge_increase(self) -> None:
        guard = TotalIncreasingGuard()
        self._prime_total_guard(guard, "pv_total_energy", 71.235)

        torn_read = {"pv_total_energy": 1.3168603261118859e34}
        guard.apply(torn_read)
        self.assertEqual(torn_read["pv_total_energy"], 71.235)

        recovered = {"pv_total_energy": 71.236}
        guard.apply(recovered)
        self.assertEqual(recovered["pv_total_energy"], 71.236)

    def test_total_increasing_guard_accepts_confirmed_large_increase(self) -> None:
        guard = TotalIncreasingGuard()
        self._prime_total_guard(guard, "grid_import_energy", 100.0)

        first_sample = {"grid_import_energy": 125.0}
        guard.apply(first_sample)
        self.assertEqual(first_sample["grid_import_energy"], 100.0)

        confirmed = {"grid_import_energy": 125.01}
        guard.apply(confirmed)
        self.assertEqual(confirmed["grid_import_energy"], 125.01)

    def test_total_increasing_guard_confirms_initial_baseline(self) -> None:
        guard = TotalIncreasingGuard()

        first = {"pv_total_energy": 71.235}
        guard.apply(first)
        self.assertNotIn("pv_total_energy", first)

        second = {"pv_total_energy": 71.236}
        guard.apply(second)
        self.assertEqual(second["pv_total_energy"], 71.236)

    def test_total_increasing_guard_rejects_bad_zero_on_startup(self) -> None:
        guard = TotalIncreasingGuard()

        bad_first = {"pv_total_energy": 0.0}
        guard.apply(bad_first)
        self.assertNotIn("pv_total_energy", bad_first)

        recovered = {"pv_total_energy": 71.236}
        guard.apply(recovered)
        self.assertNotIn("pv_total_energy", recovered)

        confirmed = {"pv_total_energy": 71.236}
        guard.apply(confirmed)
        self.assertEqual(confirmed["pv_total_energy"], 71.236)

    def test_home_load_energy_waits_for_confirmed_lifetime_baseline(self) -> None:
        guard = TotalIncreasingGuard()

        bad_zero = {"home_load_energy": 0.0}
        guard.apply(bad_zero)
        self.assertNotIn("home_load_energy", bad_zero)

        lifetime_total = {"home_load_energy": 613.25}
        guard.apply(lifetime_total)
        self.assertNotIn("home_load_energy", lifetime_total)

        confirmed = {"home_load_energy": 613.251}
        guard.apply(confirmed)
        self.assertEqual(confirmed["home_load_energy"], 613.251)

    def test_identity(self) -> None:
        registers = [0] * PCS_IDENTITY_COUNT
        _put_ascii(registers, 0, 8, "Pylontech")
        _put_ascii(registers, 8, 8, "Force H3X")
        _put_ascii(registers, 16, 8, "FH3X123456")
        registers[29] = 0x0102
        registers[30] = 0x0304

        identity = decode_identity(registers)

        self.assertEqual(identity.manufacturer, "Pylontech")
        self.assertEqual(identity.model, "Force H3X")
        self.assertEqual(identity.serial, "FH3X123456")
        self.assertEqual(identity.software_version, "V1.2.3.4")

    def test_pcs_power_and_energy(self) -> None:
        registers = [0] * PCS_MONITOR_COUNT
        _put_s32(registers, 0, 4500)
        _put_s32(registers, 8, -1320)
        registers[15] = 1
        registers[19] = 4124
        registers[20] = 53
        registers[21] = 4068
        registers[22] = 51
        registers[23] = 3976
        registers[24] = 50
        _put_s32(registers, 27, 6240)
        _put_float32(registers, 29, 428.25)
        registers[31] = 2301
        registers[32] = 101
        registers[33] = 2312
        registers[34] = 115
        registers[35] = 2299
        registers[36] = 130
        registers[40] = 5001
        registers[60] = 1
        registers[61] = 1
        _put_s32(registers, 62, -1740)
        registers[64] = 3087
        registers[65] = (-56) & 0xFFFF
        _put_float32(registers, 74, 152.5)
        _put_float32(registers, 76, 140.25)
        registers[82] = 78

        values = decode_pcs(registers)

        self.assertEqual(values["pv_total_power"], 6240)
        self.assertEqual(values["grid_power"], -1320)
        self.assertEqual(values["battery_power"], -1740)
        self.assertEqual(values["load_power"], 3180)
        self.assertEqual(values["battery_state"], "charging")
        self.assertEqual(values["battery_soc"], 78)
        self.assertAlmostEqual(values["grid_frequency"], 50.01)
        self.assertEqual(values["average_grid_voltage"], 230.4)
        self.assertEqual(values["average_grid_current"], 11.5)
        self.assertEqual(values["grid_operating_mode"], "grid_tied")
        self.assertAlmostEqual(values["pv_total_energy"], 428.25)

    def test_ac_output_substate_operating_modes(self) -> None:
        expected = {0: "unknown", 1: "grid_tied", 2: "backup", 99: "unknown"}
        for substate, mode in expected.items():
            with self.subTest(substate=substate):
                registers = [0] * PCS_MONITOR_COUNT
                registers[60] = substate
                values = decode_pcs(registers)
                self.assertEqual(values["grid_operating_mode"], mode)

    def test_grid_averages_require_all_valid_phases(self) -> None:
        registers = [0] * PCS_MONITOR_COUNT
        registers[31] = 2300
        registers[33] = 0xFFFF
        registers[35] = 2310
        registers[32] = 100
        registers[34] = 110
        registers[36] = 0xFFFF

        values = decode_pcs(registers)

        self.assertNotIn("average_grid_voltage", values)
        self.assertNotIn("average_grid_current", values)

    def test_extended_device_and_monitor_values(self) -> None:
        device = [0] * PCS_DEVICE_INFO_EXT_COUNT
        device[0] = 15000
        device[3] = 0x0102
        device[4] = 0x0304
        device[19] = 1
        device[20] = 2
        device[35] = 3
        _put_ascii(device, 27, 8, "EXT123")

        monitor = [0] * PCS_MONITOR_EXT_COUNT
        monitor[0] = 123
        _put_s32(monitor, 3, 1800)
        _put_s32(monitor, 32, 9200)
        _put_s32(monitor, 34, -2100)
        monitor[49] = 1234
        _put_float32(monitor, 62, 12.5)

        values = decode_device_info_ext(device)
        values.update(decode_pcs_monitor_ext(monitor))

        self.assertEqual(values["pcs_max_output_power"], 15000)
        self.assertEqual(values["pcs_software_version"], "V1.2.3.4")
        self.assertEqual(values["pcs_extended_serial"], "EXT123")
        self.assertEqual(values["pcs_parallel_machine_count"], 3)
        self.assertEqual(values["backup_current_r"], 12.3)
        self.assertEqual(values["backup_power_r"], 1800)
        self.assertEqual(values["parallel_pv_power"], 9200)
        self.assertEqual(values["parallel_battery_power"], -2100)
        self.assertEqual(values["battery_capacity"], 12.34)
        self.assertAlmostEqual(values["grid_to_battery_energy"], 12.5)

    def test_bms_home_load_energy_converts_wh_to_kwh(self) -> None:
        registers = [0, 0]
        _put_u32(registers, 0, 613_250)

        values = decode_bms_load_energy(registers)

        self.assertEqual(values["home_load_energy"], 613.25)

    def test_bms_nominal_capacity_converts_voltage_and_ah_to_kwh(self) -> None:
        values = decode_bms_nominal_capacity([1024, 50])

        self.assertEqual(values["bms_pile_nominal_voltage"], 102.4)
        self.assertEqual(values["bms_pile_nominal_capacity"], 50)
        self.assertEqual(values["battery_capacity"], 5.12)
        self.assertEqual(values["battery_capacity_source"], "bms_nominal")

        parallel_batteries = decode_bms_nominal_capacity([1024, 50], pile_count=2)
        self.assertEqual(parallel_batteries["battery_capacity"], 10.24)
        self.assertEqual(parallel_batteries["battery_capacity_pile_count"], 2)

    def test_bms_zero_nominal_capacity_is_not_published(self) -> None:
        values = decode_bms_nominal_capacity([1024, 0])

        self.assertNotIn("battery_capacity", values)
        self.assertNotIn("battery_capacity_source", values)

    def test_bms_system_values(self) -> None:
        registers = [0] * BMS_SYSTEM_COUNT
        registers[3] = 3087
        _put_s32(registers, 4, 564)
        registers[6] = 286
        registers[7] = 78
        registers[8] = 286
        registers[16] = 3332
        registers[17] = 3320
        registers[20] = 301
        registers[21] = 280
        registers[32] = 97
        registers[54] = 3
        registers[55] = 96
        registers[56] = 1
        registers[59] = 77
        registers[72] = 500
        registers[74] = 322
        registers[75] = 278
        _put_u32(registers, 33, 18600)
        _put_u32(registers, 43, 3250)
        _put_u32(registers, 45, 2980)

        values = decode_bms(registers)

        self.assertEqual(values["bms_soc"], 78)
        self.assertEqual(values["bms_soh"], 97)
        self.assertEqual(values["bms_cycles"], 286)
        self.assertEqual(values["bms_cell_voltage_delta"], 12)
        self.assertAlmostEqual(values["bms_current"], 5.64)
        self.assertAlmostEqual(values["bms_remaining_energy"], 18.6)
        self.assertEqual(values["bms_module_count"], 3)
        self.assertEqual(values["bms_cell_count"], 96)
        self.assertTrue(values["bms_charge_forbidden"])
        self.assertEqual(values["bms_soe"], 77)
        self.assertEqual(values["bms_insulation_resistance"], 500)
        self.assertEqual(values["bms_terminal_temperature_max"], 32.2)

    def test_bms_device_info(self) -> None:
        registers = [0] * BMS_DEVICE_INFO_COUNT
        _put_ascii(registers, 0, 5, "PYLON")
        _put_ascii(registers, 5, 5, "MBMS")
        registers[10] = 0x0106
        registers[11] = 58
        registers[12] = 2
        registers[13] = 1
        _put_ascii(registers, 14, 16, "Force H3X BMS")
        registers[30] = 0x0101

        values = decode_bms_device_info(registers)

        self.assertEqual(values["bms_manufacturer"], "PYLON")
        self.assertEqual(values["bms_device_type"], "MBMS")
        self.assertEqual(values["bms_main_version"], "V1.6")
        self.assertEqual(values["bms_product_model"], "Force H3X BMS")
        self.assertEqual(values["bms_hmi_version"], "V1.1")

    def test_bms_pile_and_dynamic_details(self) -> None:
        header = [0] * BMS_PILE_HEADER_COUNT
        header[3] = 3072
        _put_s32(header, 4, -125)
        header[7] = 65
        header[32] = 96
        header[54] = 3
        header[55] = 96
        header[58] = 3072
        header[59] = 50
        header[72] = 64
        _put_ascii(header, 80, 16, "PILE-001")

        values = decode_bms_pile_header(header)
        values.update(
            decode_bms_detail_values(
                [5120, 5118, 5122],
                [251, 252, 253],
                [3201, 3202, 3203],
                [241, 242, 243],
            )
        )

        self.assertEqual(values["bms_pile_serial"], "PILE-001")
        self.assertEqual(values["bms_pile_total_voltage"], 307.2)
        self.assertEqual(values["bms_pile_current"], -1.25)
        self.assertEqual(values["bms_module_02_voltage"], 51.18)
        self.assertEqual(values["bms_cell_003_voltage"], 3.203)
        self.assertEqual(values["bms_cell_001_temperature"], 24.1)

    def test_control_registers(self) -> None:
        active = [0] * PCS_ACTIVE_POWER_CONTROL_COUNT
        active[0] = 3
        _put_s32(active, 1, -10000)

        internal = [0] * PCS_INTERNAL_CONTROL_COUNT
        internal[0] = 1

        energy = [0] * PCS_ENERGY_MANAGEMENT_COUNT
        energy[0] = (-375) & 0xFFFF
        energy[1] = 95
        energy[2] = 15
        energy[6] = 4
        energy[7] = 1
        energy[8] = 0x071E
        energy[9] = 0x0A2D
        energy[10] = 1
        energy[11] = 500
        energy[12] = 0b0111110
        energy[13] = 0
        energy[19] = 1
        energy[25] = 1

        values = decode_active_power_controls(active)
        values.update(decode_internal_controls(internal))
        values.update(decode_energy_management_controls(energy))
        peak = [1, 20, 5000]
        self.assertEqual(len(peak), PCS_PEAK_SHAVING_COUNT)
        values.update(decode_peak_shaving_controls(peak))

        self.assertEqual(values["active_power_control_mode"], 3)
        self.assertEqual(values["meter_export_power_max"], -10000)
        self.assertTrue(values["heat_pump_enabled"])
        self.assertEqual(values["charge_discharge_power_reference"], -37.5)
        self.assertEqual(values["charge_limit_soc"], 95)
        self.assertEqual(values["eps_limit_soc_on_grid"], 15)
        self.assertEqual(values["ems_mode"], 4)
        self.assertTrue(values["period_1_enabled"])
        self.assertEqual(values["period_1_start"], "07:30")
        self.assertEqual(values["period_1_end"], "10:45")
        self.assertEqual(values["period_1_mode"], "discharge")
        self.assertEqual(values["period_1_power"], 50.0)
        self.assertEqual(values["period_1_weekdays"], "mon,tue,wed,thu,fri")
        self.assertFalse(values["period_2_enabled"])
        self.assertTrue(values["period_3_enabled"])
        self.assertTrue(values["period_4_enabled"])
        self.assertTrue(values["peak_shaving_enabled"])
        self.assertEqual(values["peak_shaving_safety_soc"], 20)
        self.assertEqual(values["peak_shaving_meter_power_limit"], 5000)

    def test_short_response_is_rejected(self) -> None:
        with self.assertRaises(FH3XDecodeError):
            decode_pcs([0] * 12)


if __name__ == "__main__":
    unittest.main()
