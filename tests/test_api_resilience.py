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
        self.assertEqual(device_ids[:-1], [2] * 6)
        self.assertEqual(device_ids[-1], 1)
        self.assertEqual(transitions, 1)

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
