"""Standalone diagnostics privacy tests."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from typing import ClassVar

from _helpers import COMPONENT_PATH

PACKAGE_NAME = "fh3x_diagnostics_test_package"
REDACTED = "**REDACTED**"


def _redact(value, keys):
    if isinstance(value, dict):
        return {
            key: REDACTED if key in keys else _redact(child, keys)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact(child, keys) for child in value]
    return value


def _load_diagnostics():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(COMPONENT_PATH)]
    package.FH3XConfigEntry = object
    sys.modules[PACKAGE_NAME] = package

    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    diagnostics = types.ModuleType("homeassistant.components.diagnostics")
    diagnostics.async_redact_data = _redact
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.CONF_HOST = "host"
    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.diagnostics"] = diagnostics
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.core"] = ha_core

    const = types.ModuleType(f"{PACKAGE_NAME}.const")
    const.BMS_DEVICE_ID = 1
    const.PCS_DEVICE_ID = 2
    sys.modules[const.__name__] = const

    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_NAME}.diagnostics",
        COMPONENT_PATH / "diagnostics.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DIAGNOSTICS = _load_diagnostics()


@dataclass(frozen=True)
class _Identity:
    manufacturer: str = "Pylontech"
    model: str = "FH3X"
    serial: str = "PRIVATE-PCS-SERIAL"
    software_version: str = "1.0.0"


@dataclass(frozen=True)
class _Snapshot:
    identity: _Identity
    values: dict


@dataclass(frozen=True)
class _PollFailureState:
    stale: bool = False
    consecutive_failures: int = 0
    failure_threshold: int = 3


class _Coordinator:
    data = _Snapshot(
        _Identity(),
        {
            "pv_total_power": 3200,
            "pcs_extended_serial": "PRIVATE-EXTENDED-SERIAL",
            "bms_pile_serial": "PRIVATE-BMS-SERIAL",
        },
    )
    last_update_success = True
    poll_failure_state = _PollFailureState()


class _RuntimeData:
    coordinator = _Coordinator()


class _Entry:
    data: ClassVar[dict[str, object]] = {"host": "192.0.2.10", "port": 502}
    runtime_data = _RuntimeData()


class TestDiagnosticsPrivacy(unittest.IsolatedAsyncioTestCase):
    async def test_host_and_all_serial_values_are_redacted(self) -> None:
        result = await DIAGNOSTICS.async_get_config_entry_diagnostics(
            object(), _Entry()
        )

        self.assertEqual(result["entry"]["host"], REDACTED)
        self.assertEqual(result["identity"]["serial"], REDACTED)
        self.assertEqual(result["values"]["pcs_extended_serial"], REDACTED)
        self.assertEqual(result["values"]["bms_pile_serial"], REDACTED)
        self.assertEqual(result["values"]["pv_total_power"], 3200)
        self.assertEqual(result["protocol"]["pcs_device_id"], 2)
        self.assertEqual(result["protocol"]["bms_device_id"], 1)


if __name__ == "__main__":
    unittest.main()
