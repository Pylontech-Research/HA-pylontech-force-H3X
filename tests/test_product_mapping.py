"""Tests for product registration point mappings."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components" / "pylontech_fh3x"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PROTOCOL = _load("protocol", "protocol.py")
PRODUCT = _load("fh3x_product", "product.py")


class TestProductMapping(unittest.TestCase):
    """Verify aliases and derived product values use documented semantics."""

    def test_maps_identity_and_bms_limits(self) -> None:
        identity = PROTOCOL.FH3XIdentity("Pylontech", "Force H3X", "FH3X-1", "V1")
        values = PRODUCT.normalize_product_values(
            {
                "pcs_max_output_power": 12000,
                "bms_max_charge_voltage": 102.4,
                "bms_max_charge_current": 50.0,
                "bms_min_discharge_voltage": 96.0,
                "bms_max_discharge_current": 60.0,
                "bms_soc": 77,
                "bms_soh": 98,
                "bms_temperature": 25.5,
                "ac_total_power": 4200,
                "ac_reactive_power": -500,
                "pv_total_power": 5300,
            },
            identity,
        )

        self.assertEqual(values["device_model"], "Force H3X")
        self.assertEqual(values["device_serial_number"], "FH3X-1")
        self.assertEqual(values["rated_power"], 12000)
        self.assertEqual(values["battery_soc_bms"], 77)
        self.assertEqual(values["battery_soh"], 98)
        self.assertEqual(values["max_charge_power"], 5.12)
        self.assertEqual(values["max_discharge_power"], 5.76)
        self.assertEqual(values["inverter_power"], 4.2)
        self.assertEqual(values["inverter_reactive_power"], -0.5)
        self.assertEqual(values["pv_power"], 5.3)

    def test_sums_third_party_pv_and_classifies_alarm(self) -> None:
        identity = PROTOCOL.FH3XIdentity("Pylontech", "Force H3X", "FH3X-1", "V1")
        values = PRODUCT.normalize_product_values(
            {
                "acc_power_r": 1200,
                "acc_power_s": -200,
                "acc_power_t": 0,
                "fault_bits": 0,
                "warning_bits": 1,
                "bms_alarm_status_1": 0,
                "bms_alarm_status_2": 0,
                "fault_code": 0,
                "warning_code": 12,
            },
            identity,
        )

        self.assertEqual(values["third_party_pv_power"], 1.0)
        self.assertEqual(values["device_fault_status"], "alarm")
        self.assertEqual(values["current_alarm_code"], "12")

        fault_values = PRODUCT.normalize_product_values(
            {"fault_bits": 1, "warning_bits": 1}, identity
        )
        self.assertEqual(fault_values["device_fault_status"], "fault")

    def test_does_not_create_unsupported_values(self) -> None:
        identity = PROTOCOL.FH3XIdentity("Pylontech", "Force H3X", "FH3X-1", "V1")
        values = PRODUCT.normalize_product_values({}, identity)

        self.assertNotIn("max_reactive_power", values)
        self.assertNotIn("third_party_pv_generation_energy", values)


if __name__ == "__main__":
    unittest.main()
