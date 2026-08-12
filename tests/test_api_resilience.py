"""Tests for FH3X Modbus transport resilience."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from itertools import pairwise
from pathlib import Path
from unittest.mock import AsyncMock, patch

COMPONENT_PATH = Path(__file__).parents[1] / "custom_components" / "pylontech_fh3x"
PACKAGE_NAME = "fh3x_api_test_package"


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


package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(COMPONENT_PATH)]
sys.modules[PACKAGE_NAME] = package


class FakeModbusException(Exception):
    """Stand in for pymodbus transport exceptions."""


class FakeResponse:
    """Return a valid holding-register response."""

    def __init__(self, count: int) -> None:
        self.registers = [0] * count

    def isError(self) -> bool:
        return False


class FakeAsyncModbusTcpClient:
    """Record requests and optionally fail the next transport call."""

    def __init__(self, **kwargs) -> None:
        self.connected = True
        self.calls: list[tuple[int, int, int]] = []
        self.close_calls = 0
        self.connect_calls = 0
        self.failures_remaining = 0

    async def connect(self) -> bool:
        self.connect_calls += 1
        self.connected = True
        return True

    def close(self) -> None:
        self.close_calls += 1
        self.connected = False

    async def read_holding_registers(
        self,
        address: int,
        *,
        count: int,
        device_id: int,
    ) -> FakeResponse:
        self.calls.append((address, count, device_id))
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise FakeModbusException("wrong unit response")
        return FakeResponse(count)

    async def read_input_registers(
        self,
        address: int,
        *,
        count: int,
        device_id: int,
    ) -> FakeResponse:
        return await self.read_holding_registers(
            address,
            count=count,
            device_id=device_id,
        )

    async def write_register(
        self,
        address: int,
        value: int,
        *,
        device_id: int,
    ) -> FakeResponse:
        self.calls.append((address, 1, device_id))
        return FakeResponse(1)


pymodbus = types.ModuleType("pymodbus")
pymodbus_client = types.ModuleType("pymodbus.client")
pymodbus_exceptions = types.ModuleType("pymodbus.exceptions")
pymodbus_client.AsyncModbusTcpClient = FakeAsyncModbusTcpClient
pymodbus_exceptions.ModbusException = FakeModbusException
sys.modules["pymodbus"] = pymodbus
sys.modules["pymodbus.client"] = pymodbus_client
sys.modules["pymodbus.exceptions"] = pymodbus_exceptions

_load_component_module("exposure")
_load_component_module("const")
_load_component_module("protocol")
API = _load_component_module("api")


class _AsyncTimeoutStub:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, traceback):
        return False


if not hasattr(API.asyncio, "timeout"):
    API.asyncio.timeout = lambda _seconds: _AsyncTimeoutStub()


class TestFH3XTransportResilience(unittest.IsolatedAsyncioTestCase):
    """Verify reconnect, pacing and grouped unit-ID behavior."""

    def _client(self, **kwargs):
        return API.FH3XModbusClient(
            "192.0.2.10",
            502,
            request_interval=0,
            device_switch_delay=0,
            read_retry_delay=0,
            **kwargs,
        )

    async def test_transport_failure_reconnects_before_retry(self) -> None:
        client = self._client(read_retries=1)
        transport = client._client
        transport.failures_remaining = 1

        registers = await client._async_read_registers(30100, 4, 2)

        self.assertEqual(registers, [0, 0, 0, 0])
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(transport.close_calls, 1)
        self.assertEqual(transport.connect_calls, 1)

    async def test_switching_device_id_applies_guard_delay(self) -> None:
        client = API.FH3XModbusClient(
            "192.0.2.10",
            502,
            request_interval=0,
            device_switch_delay=0.2,
            read_retries=0,
        )
        sleep = AsyncMock()

        with patch.object(API.asyncio, "sleep", sleep):
            await client._async_read_registers(30100, 1, 2)
            await client._async_read_registers(0x1100, 1, 1)

        sleep.assert_awaited_once()
        self.assertGreater(sleep.await_args.args[0], 0)

    async def test_snapshot_groups_pcs_before_bms_requests(self) -> None:
        client = self._client(read_retries=0)
        client._identity = API.FH3XIdentity(
            manufacturer="Pylontech",
            model="FH3X",
            serial="TEST123",
            software_version="V1.0",
        )
        client._device_info_attempted = True

        await client.async_read_snapshot()

        device_ids = [device_id for _, _, device_id in client._client.calls]
        transitions = sum(
            previous != current for previous, current in pairwise(device_ids)
        )
        first_bms = device_ids.index(1)
        self.assertEqual(device_ids[:first_bms], [2] * first_bms)
        self.assertEqual(device_ids[first_bms:], [1] * (len(device_ids) - first_bms))
        self.assertEqual(transitions, 1)

    async def test_load_energy_selects_single_and_parallel_registers(self) -> None:
        client = self._client(read_retries=0)
        read = AsyncMock(return_value=[0, 1234])
        client._async_read_registers = read

        single = await client._async_read_optional_load_energy()
        self.assertEqual(single["home_load_energy"], 1.234)
        read.assert_awaited_with(API.BMS_LOAD_ENERGY_ADDRESS, 2, 1)

        client._device_values["pcs_parallel_machine_count"] = 2
        parallel = await client._async_read_optional_load_energy()
        self.assertEqual(parallel["home_load_energy"], 1.234)
        read.assert_awaited_with(API.BMS_PARALLEL_LOAD_ENERGY_ADDRESS, 2, 1)

    async def test_load_energy_becomes_unavailable_after_three_failures(self) -> None:
        client = self._client(read_retries=0)
        client._load_energy_values = {"home_load_energy": 42.5}
        client._async_read_registers = AsyncMock(
            side_effect=API.FH3XConnectionError("unavailable")
        )

        self.assertEqual(
            await client._async_read_optional_load_energy(),
            {"home_load_energy": 42.5},
        )
        self.assertEqual(
            await client._async_read_optional_load_energy(),
            {"home_load_energy": 42.5},
        )
        self.assertEqual(await client._async_read_optional_load_energy(), {})

        client._async_read_registers = AsyncMock(return_value=[0, 42_501])
        self.assertEqual(
            await client._async_read_optional_load_energy(),
            {"home_load_energy": 42.501},
        )
        self.assertEqual(client._load_energy_failures, 0)

    async def test_capacity_is_cached_and_zero_is_not_published(self) -> None:
        client = self._client(read_retries=0)
        client._device_values["pcs_parallel_machine_count"] = 2
        registers = [0] * API.PCS_MONITOR_EXT_COUNT
        registers[49] = 1234
        client._async_read_registers = AsyncMock(return_value=registers)

        values = await client._async_read_optional_monitor_ext()
        self.assertEqual(values["battery_capacity"], 12.34)
        self.assertEqual(client._device_values["battery_capacity"], 12.34)
        self.assertEqual(
            client._device_values["battery_capacity_source"], "pcs_parallel"
        )

        registers[49] = 0
        values = await client._async_read_optional_monitor_ext()
        self.assertNotIn("battery_capacity", values)
        self.assertEqual(client._device_values["battery_capacity"], 12.34)

    async def test_single_pcs_does_not_use_parallel_capacity(self) -> None:
        client = self._client(read_retries=0)
        client._device_values["pcs_parallel_machine_count"] = 1
        registers = [0] * API.PCS_MONITOR_EXT_COUNT
        registers[49] = 1234
        client._async_read_registers = AsyncMock(return_value=registers)

        values = await client._async_read_optional_monitor_ext()

        self.assertNotIn("battery_capacity", values)
        self.assertNotIn("battery_capacity", client._device_values)

    async def test_single_capacity_uses_and_caches_bms_nominal_values(self) -> None:
        client = self._client(read_retries=0)
        client._device_values["pcs_parallel_machine_count"] = 0
        read = AsyncMock(return_value=[1024, 50])
        client._async_read_registers = read

        values = await client._async_read_optional_battery_capacity(
            {"bms_parallel_pile_count": 1}
        )

        self.assertEqual(values["battery_capacity"], 5.12)
        self.assertEqual(values["battery_capacity_source"], "bms_nominal")
        read.assert_awaited_once_with(API.BMS_PILE_NOMINAL_ADDRESS, 2, 1)

        read.reset_mock()
        self.assertEqual(
            await client._async_read_optional_battery_capacity(
                {"bms_parallel_pile_count": 1}
            ),
            {},
        )
        read.assert_not_awaited()

    async def test_parallel_pcs_skips_bms_nominal_capacity(self) -> None:
        client = self._client(read_retries=0)
        client._device_values["pcs_parallel_machine_count"] = 2
        read = AsyncMock()
        client._async_read_registers = read

        values = await client._async_read_optional_battery_capacity(
            {"bms_parallel_pile_count": 2}
        )

        self.assertEqual(values, {})
        read.assert_not_awaited()

    async def test_write_waits_when_switching_from_bms_to_pcs(self) -> None:
        client = self._client(read_retries=0)
        client.device_switch_delay = 0.2
        client._last_device_id = 1
        client._last_request_completed_at = API.asyncio.get_running_loop().time()
        sleep = AsyncMock()

        with patch.object(API.asyncio, "sleep", sleep):
            await client._async_write_and_verify(0x9FC5, [0], 2)

        sleep.assert_awaited_once()
        self.assertGreater(sleep.await_args.args[0], 0)


if __name__ == "__main__":
    unittest.main()
