"""Standalone setup and unload lifecycle tests."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from typing import ClassVar
from unittest.mock import AsyncMock

from _helpers import COMPONENT_PATH

PACKAGE_NAME = "fh3x_lifecycle_test_package"


class _ConfigEntry:
    @classmethod
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self) -> None:
        self.data = {"host": "192.0.2.10", "port": 502}
        self.options = {}
        self.runtime_data = None


class _Platform:
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    NUMBER = "number"
    SELECT = "select"
    SWITCH = "switch"
    TIME = "time"


class _Client:
    instances: ClassVar[list[_Client]] = []

    def __init__(self, **_kwargs) -> None:
        self.closed = False
        self.instances.append(self)

    async def async_close(self) -> None:
        self.closed = True


class _Coordinator:
    first_refresh_error: Exception | None = None

    def __init__(self, _hass, _entry, client: _Client) -> None:
        self.client = client

    async def async_config_entry_first_refresh(self) -> None:
        if self.first_refresh_error is not None:
            raise self.first_refresh_error


class _ConfigEntriesManager:
    def __init__(self) -> None:
        self.forwarded = None
        self.unload_result = True

    async def async_forward_entry_setups(self, _entry, platforms) -> None:
        self.forwarded = list(platforms)

    async def async_unload_platforms(self, _entry, _platforms) -> bool:
        return self.unload_result


class _Hass:
    def __init__(self) -> None:
        self.config_entries = _ConfigEntriesManager()
        self.tasks: list[asyncio.Task] = []

    def async_create_task(self, coro, _name=None):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


def _load_integration():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(COMPONENT_PATH)]
    sys.modules[PACKAGE_NAME] = package

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = _ConfigEntry
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.CONF_HOST = "host"
    ha_const.CONF_PORT = "port"
    ha_const.Platform = _Platform
    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.core"] = ha_core

    api = types.ModuleType(f"{PACKAGE_NAME}.api")
    api.FH3XModbusClient = _Client
    sys.modules[api.__name__] = api

    const = types.ModuleType(f"{PACKAGE_NAME}.const")
    for key, value in {
        "CONF_CONTROL_PROFILE": "control_profile",
        "CONF_DETAILED_BMS": "detailed_bms",
        "CONF_ENTITY_PROFILE": "entity_profile",
        "DEFAULT_CONTROL_PROFILE": "basic",
        "DEFAULT_DETAILED_BMS": False,
        "DEFAULT_ENTITY_PROFILE": "compact",
    }.items():
        setattr(const, key, value)
    sys.modules[const.__name__] = const

    coordinator = types.ModuleType(f"{PACKAGE_NAME}.coordinator")
    coordinator.FH3XCoordinator = _Coordinator
    sys.modules[coordinator.__name__] = coordinator

    profiles = types.ModuleType(f"{PACKAGE_NAME}.profiles")
    profiles.apply_profiles_to_registry = lambda *_args: None
    profiles.async_apply_english_names_to_registry = AsyncMock()
    sys.modules[profiles.__name__] = profiles

    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        COMPONENT_PATH / "__init__.py",
        submodule_search_locations=[str(COMPONENT_PATH)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)
    module._async_apply_english_names_after_platform_setup = AsyncMock()
    return module


INTEGRATION = _load_integration()


class TestIntegrationLifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _Client.instances.clear()
        _Coordinator.first_refresh_error = None

    async def test_setup_and_successful_unload_close_client(self) -> None:
        hass = _Hass()
        entry = _ConfigEntry()

        self.assertTrue(await INTEGRATION.async_setup_entry(hass, entry))
        await asyncio.gather(*hass.tasks)

        client = _Client.instances[-1]
        self.assertIs(entry.runtime_data.client, client)
        self.assertEqual(hass.config_entries.forwarded, INTEGRATION.PLATFORMS)
        self.assertFalse(client.closed)

        self.assertTrue(await INTEGRATION.async_unload_entry(hass, entry))
        self.assertTrue(client.closed)

    async def test_failed_first_refresh_closes_client(self) -> None:
        hass = _Hass()
        entry = _ConfigEntry()
        _Coordinator.first_refresh_error = RuntimeError("first refresh failed")

        with self.assertRaisesRegex(RuntimeError, "first refresh failed"):
            await INTEGRATION.async_setup_entry(hass, entry)

        self.assertTrue(_Client.instances[-1].closed)
        self.assertIsNone(entry.runtime_data)

    async def test_failed_platform_unload_keeps_client_open(self) -> None:
        hass = _Hass()
        hass.config_entries.unload_result = False
        entry = _ConfigEntry()
        await INTEGRATION.async_setup_entry(hass, entry)
        await asyncio.gather(*hass.tasks)

        self.assertFalse(await INTEGRATION.async_unload_entry(hass, entry))
        self.assertFalse(_Client.instances[-1].closed)


if __name__ == "__main__":
    unittest.main()
