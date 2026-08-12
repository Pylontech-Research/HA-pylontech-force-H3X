"""Tests for the FH3X discovery config flow."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, patch

COMPONENT_PATH = Path(__file__).parents[1] / "custom_components" / "pylontech_fh3x"
PACKAGE_NAME = "fh3x_config_flow_test_package"


def _load_component_module(name: str):
    full_name = f"{PACKAGE_NAME}.{name}"
    spec = importlib.util.spec_from_file_location(
        full_name,
        COMPONENT_PATH / f"{name}.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


class _Voluptuous:
    class Schema:
        def __init__(self, schema):
            self.schema = schema

    @staticmethod
    def Required(key, **_kwargs):
        return key

    @staticmethod
    def All(*validators):
        return validators

    @staticmethod
    def Coerce(value_type):
        return value_type

    @staticmethod
    def Range(**kwargs):
        return kwargs

    @staticmethod
    def In(values):
        return values


class _ConfigFlowBase:
    def __init_subclass__(cls, **_kwargs):
        super().__init_subclass__()

    def __init__(self) -> None:
        self.hass = _FakeHass()
        self.context = {}
        self.unique_id = None

    async def async_set_unique_id(self, unique_id, **_kwargs):
        self.unique_id = unique_id

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_show_menu(self, **kwargs):
        return {"type": "menu", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}

    def async_update_reload_and_abort(self, entry, **kwargs):
        entry.data.update(kwargs.get("data_updates", {}))
        return {"type": "abort", "entry": entry, **kwargs}

    def _abort_if_unique_id_configured(self):
        return None

    def _abort_if_unique_id_mismatch(self):
        return None


class _OptionsFlowWithReload:
    pass


class _ConfigEntries:
    def __init__(self) -> None:
        self.existing = None

    def async_entry_for_domain_unique_id(self, _domain, _unique_id):
        return self.existing


class _FakeHass:
    def __init__(self) -> None:
        self.config_entries = _ConfigEntries()


@dataclass
class _Entry:
    data: dict


@dataclass(frozen=True)
class _Identity:
    manufacturer: str
    model: str
    serial: str
    software_version: str


class _ConnectionError(Exception):
    pass


class _ProtocolError(Exception):
    pass


package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(COMPONENT_PATH)]
sys.modules[PACKAGE_NAME] = package

sys.modules["voluptuous"] = _Voluptuous()
homeassistant = types.ModuleType("homeassistant")
config_entries = types.ModuleType("homeassistant.config_entries")
config_entries.ConfigFlow = _ConfigFlowBase
config_entries.ConfigFlowResult = dict
config_entries.OptionsFlowWithReload = _OptionsFlowWithReload
config_entries.ConfigEntry = object
config_entries.OptionsFlow = object
homeassistant.config_entries = config_entries
homeassistant_const = types.ModuleType("homeassistant.const")
homeassistant_const.CONF_HOST = "host"
homeassistant_const.CONF_PORT = "port"
homeassistant_core = types.ModuleType("homeassistant.core")
homeassistant_core.HomeAssistant = object
homeassistant_core.callback = lambda func: func
sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.config_entries"] = config_entries
sys.modules["homeassistant.const"] = homeassistant_const
sys.modules["homeassistant.core"] = homeassistant_core

const = types.ModuleType(f"{PACKAGE_NAME}.const")
for key, value in {
    "CONF_CONTROL_PROFILE": "control_profile",
    "CONF_DETAILED_BMS": "detailed_bms",
    "CONF_ENTITY_PROFILE": "entity_profile",
    "CONF_SCAN_INTERVAL": "scan_interval",
    "CONTROL_PROFILES": ("daily", "basic", "advanced"),
    "DEFAULT_CONTROL_PROFILE": "basic",
    "DEFAULT_DETAILED_BMS": False,
    "DEFAULT_ENTITY_PROFILE": "compact",
    "DEFAULT_NAME": "Pylontech Force H3X",
    "DEFAULT_PORT": 502,
    "DEFAULT_SCAN_INTERVAL": 10,
    "DOMAIN": "pylontech_fh3x",
    "ENTITY_PROFILES": ("compact", "standard", "engineering"),
    "MAX_SCAN_INTERVAL": 300,
    "MIN_SCAN_INTERVAL": 5,
}.items():
    setattr(const, key, value)
sys.modules[const.__name__] = const

api = types.ModuleType(f"{PACKAGE_NAME}.api")
api.FH3XConnectionError = _ConnectionError
api.FH3XProtocolError = _ProtocolError
api.FH3XModbusClient = object
sys.modules[api.__name__] = api

profiles = types.ModuleType(f"{PACKAGE_NAME}.profiles")
profiles.apply_profiles_to_registry = lambda *_args: None
sys.modules[profiles.__name__] = profiles

protocol = types.ModuleType(f"{PACKAGE_NAME}.protocol")
protocol.FH3XIdentity = _Identity
sys.modules[protocol.__name__] = protocol

discovery = types.ModuleType(f"{PACKAGE_NAME}.discovery")


@dataclass(frozen=True)
class _Discovery:
    host: str
    port: int = 502
    server: str = "Pylontech FH3X/V1.0"
    device_address: int = 2
    usn: str | None = "UDP-SERIAL"

    @property
    def display_name(self):
        return f"{self.server} · {self.usn} · {self.host}"


discovery.FH3XDiscoveryInfo = _Discovery
discovery.async_discover_fh3x = AsyncMock(return_value=[])
sys.modules[discovery.__name__] = discovery

CONFIG_FLOW = _load_component_module("config_flow")


class TestFH3XDiscoveryConfigFlow(unittest.IsolatedAsyncioTestCase):
    """Verify user-visible discovery outcomes."""

    def setUp(self) -> None:
        discovery.async_discover_fh3x.reset_mock()
        discovery.async_discover_fh3x.return_value = []

    def _flow(self):
        flow = CONFIG_FLOW.FH3XConfigFlow()
        flow.hass = _FakeHass()
        flow.context = {}
        flow.unique_id = None
        return flow

    async def test_no_device_offers_rescan_and_manual_setup(self) -> None:
        flow = self._flow()

        result = await flow.async_step_user()

        self.assertEqual(result["type"], "menu")
        self.assertEqual(result["step_id"], "discovery_failed")
        self.assertEqual(result["menu_options"], ["scan", "manual"])

    async def test_single_device_is_modbus_validated_before_confirmation(self) -> None:
        flow = self._flow()
        discovery.async_discover_fh3x.return_value = [_Discovery("192.168.1.20")]
        identity = _Identity("Pylontech", "FH3X-12K", "MODBUS-123", "V1")

        with patch.object(
            CONFIG_FLOW, "async_validate_input", AsyncMock(return_value=identity)
        ):
            result = await flow.async_step_user()

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "confirm")
        self.assertEqual(flow.unique_id, "MODBUS-123")
        self.assertEqual(result["description_placeholders"]["host"], "192.168.1.20")

        created = await flow.async_step_confirm({})
        self.assertEqual(created["type"], "create_entry")
        self.assertEqual(created["data"], {"host": "192.168.1.20", "port": 502})

    async def test_multiple_devices_are_presented_for_selection(self) -> None:
        flow = self._flow()
        discovery.async_discover_fh3x.return_value = [
            _Discovery("192.168.1.20", usn="UDP-1"),
            _Discovery("192.168.1.21", usn="UDP-2"),
        ]

        result = await flow.async_step_user()

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "select_device")
        self.assertEqual(len(flow._discoveries), 2)

    async def test_udp_usn_is_not_used_as_unique_id(self) -> None:
        flow = self._flow()
        candidate = _Discovery("192.168.1.20", usn="UNTRUSTED-UDP")
        identity = _Identity("Pylontech", "FH3X", "TRUSTED-MODBUS", "V1")

        with patch.object(
            CONFIG_FLOW, "async_validate_input", AsyncMock(return_value=identity)
        ):
            await flow._async_validate_discovery(candidate)

        self.assertEqual(flow.unique_id, "TRUSTED-MODBUS")

    async def test_rediscovery_updates_existing_host(self) -> None:
        flow = self._flow()
        entry = _Entry({"host": "192.168.1.10", "port": 502})
        flow.hass.config_entries.existing = entry
        identity = _Identity("Pylontech", "FH3X", "MODBUS-123", "V1")

        with patch.object(
            CONFIG_FLOW, "async_validate_input", AsyncMock(return_value=identity)
        ):
            result = await flow._async_validate_discovery(_Discovery("192.168.1.20"))

        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["reason"], "already_configured")
        self.assertEqual(entry.data["host"], "192.168.1.20")

    async def test_modbus_validation_failure_offers_retry_or_manual(self) -> None:
        flow = self._flow()

        with patch.object(
            CONFIG_FLOW,
            "async_validate_input",
            AsyncMock(side_effect=_ConnectionError),
        ):
            result = await flow._async_validate_discovery(_Discovery("192.168.1.20"))

        self.assertEqual(result["type"], "menu")
        self.assertEqual(result["step_id"], "discovery_validation_failed")
        self.assertEqual(result["menu_options"], ["scan", "manual"])

    async def test_manual_fallback_preserves_existing_form(self) -> None:
        flow = self._flow()

        result = await flow.async_step_manual()

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "manual")


if __name__ == "__main__":
    unittest.main()
