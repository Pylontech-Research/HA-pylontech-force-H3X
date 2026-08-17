"""Tests for FH3X local discovery."""

from __future__ import annotations

import asyncio
import importlib.util
import ipaddress
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

COMPONENT_PATH = Path(__file__).parents[1] / "custom_components" / "pylontech_fh3x"
PACKAGE_NAME = "fh3x_discovery_test_package"


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

homeassistant = types.ModuleType("homeassistant")
homeassistant_components = types.ModuleType("homeassistant.components")
homeassistant_network = types.ModuleType("homeassistant.components.network")
homeassistant_core = types.ModuleType("homeassistant.core")
homeassistant_core.HomeAssistant = object
homeassistant_components.network = homeassistant_network
sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.components"] = homeassistant_components
sys.modules["homeassistant.components.network"] = homeassistant_network
sys.modules["homeassistant.core"] = homeassistant_core

_load_component_module("exposure")
_load_component_module("const")
DISCOVERY = _load_component_module("discovery")

LOCAL_NETWORKS = (ipaddress.IPv4Network("192.168.137.0/24"),)


def _response(**headers: str) -> bytes:
    values = {
        "CACHE-CONTROL": "max-age=120",
        "EXT": "2",
        "SERVER": "Pylontech FH3X/V1.0",
        "ST": "ssdp:all",
        "USN": "FH3X-TEST-001",
        **headers,
    }
    lines = ["HTTP/1.1 200 OK", *(f"{key}: {value}" for key, value in values.items())]
    return ("\r\n".join(lines) + "\r\n\r\n").encode()


class TestFH3XDiscovery(unittest.TestCase):
    """Verify discovery parsing, filtering and deduplication."""

    def test_parses_real_response_fields_case_insensitively(self) -> None:
        payload = (
            b"HTTP/1.1 200 OK\r\n"
            b"cache-control: max-age=120\r\n"
            b"ext: 1\r\n"
            b"server: fh3x release-1.2\r\n"
            b"st: ssdp:all\r\n"
            b"usn: SERIAL-123\r\n\r\n"
        )

        result = DISCOVERY.parse_discovery_response(
            payload, "192.168.137.20", LOCAL_NETWORKS
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.host, "192.168.137.20")
        self.assertEqual(result.port, 502)
        self.assertEqual(result.device_address, 1)
        self.assertEqual(result.usn, "SERIAL-123")

    def test_parses_cross_subnet_fh3x_response(self) -> None:
        payload = (
            b"HTTP/1.1 200 OK\r\n"
            b"CACHE-CONTROL: max-age = 1800\r\n"
            b"EXT: 1\r\n"
            b"SERVER: FH3X-V0.30;FH3X-TEST-MODEL -V1.0.0.25\r\n"
            b"ST: ssdp:all\r\n"
            b"USN: FH3X-TEST-CROSS-SUBNET\r\n\r\n"
        )

        result = DISCOVERY.parse_discovery_response(
            payload,
            "192.168.50.39",
            (ipaddress.IPv4Network("192.168.40.0/24"),),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.host, "192.168.50.39")
        self.assertEqual(result.usn, "FH3X-TEST-CROSS-SUBNET")
        self.assertEqual(result.server, "FH3X-V0.30;FH3X-TEST-MODEL -V1.0.0.25")

    def test_accepts_only_fh3x_device_addresses_one_and_two(self) -> None:
        for address in ("1", "2"):
            with self.subTest(address=address):
                self.assertIsNotNone(
                    DISCOVERY.parse_discovery_response(
                        _response(EXT=address), "192.168.137.20", LOCAL_NETWORKS
                    )
                )
        for address in ("0", "3", "invalid"):
            with self.subTest(address=address):
                self.assertIsNone(
                    DISCOVERY.parse_discovery_response(
                        _response(EXT=address), "192.168.137.20", LOCAL_NETWORKS
                    )
                )
        self.assertIsNone(
            DISCOVERY.parse_discovery_response(
                _response(SERVER="RCD_AC/V1.0"),
                "192.168.137.20",
                LOCAL_NETWORKS,
            )
        )

    def test_rejects_non_response_and_unsafe_source(self) -> None:
        self.assertIsNone(
            DISCOVERY.parse_discovery_response(
                b"M-SEARCH * HTTP/1.1\r\n\r\n",
                "192.168.137.1",
                LOCAL_NETWORKS,
            )
        )
        self.assertIsNone(
            DISCOVERY.parse_discovery_response(_response(), "8.8.8.8", LOCAL_NETWORKS)
        )

    def test_multicast_listener_uses_alternate_source_port(self) -> None:
        sock = MagicMock()

        with patch.object(DISCOVERY.socket, "socket", return_value=sock):
            result = DISCOVERY._create_socket("192.168.137.1", broadcast=False)

        self.assertIs(result, sock)
        sock.bind.assert_called_once_with(("", 1901))
        sock.setsockopt.assert_any_call(
            DISCOVERY.socket.IPPROTO_IP,
            DISCOVERY.socket.IP_MULTICAST_IF,
            DISCOVERY.socket.inet_aton("192.168.137.1"),
        )

    def test_deduplicates_multicast_and_broadcast_responses(self) -> None:
        first = DISCOVERY.parse_discovery_response(
            _response(), "192.168.137.20", LOCAL_NETWORKS
        )
        duplicate = DISCOVERY.parse_discovery_response(
            _response(), "192.168.137.20", LOCAL_NETWORKS
        )
        second = DISCOVERY.parse_discovery_response(
            _response(USN="FH3X-TEST-002"),
            "192.168.137.21",
            LOCAL_NETWORKS,
        )
        assert first is not None and duplicate is not None and second is not None

        result = DISCOVERY.deduplicate_discoveries([first, duplicate, second])

        self.assertEqual(result, [first, second])

    def test_missing_usn_deduplicates_by_source_ip(self) -> None:
        first = DISCOVERY.parse_discovery_response(
            _response(USN=""), "192.168.137.20", LOCAL_NETWORKS
        )
        duplicate = DISCOVERY.parse_discovery_response(
            _response(USN=""), "192.168.137.20", LOCAL_NETWORKS
        )
        assert first is not None and duplicate is not None

        self.assertEqual(DISCOVERY.deduplicate_discoveries([first, duplicate]), [first])

    def test_usn_deduplicates_same_device_after_ip_change(self) -> None:
        first = DISCOVERY.parse_discovery_response(
            _response(USN="FH3X-STABLE"), "192.168.137.20", LOCAL_NETWORKS
        )
        moved = DISCOVERY.parse_discovery_response(
            _response(USN="FH3X-STABLE"), "192.168.137.21", LOCAL_NETWORKS
        )
        assert first is not None and moved is not None

        self.assertEqual(DISCOVERY.deduplicate_discoveries([first, moved]), [moved])

    def test_enabled_adapters_define_local_networks(self) -> None:
        adapters = [
            {
                "enabled": True,
                "ipv4": [{"address": "192.168.137.1", "network_prefix": 24}],
            },
            {
                "enabled": False,
                "ipv4": [{"address": "10.0.0.2", "network_prefix": 24}],
            },
            {
                "enabled": True,
                "ipv4": [{"address": "169.254.1.2", "network_prefix": 16}],
            },
        ]

        self.assertEqual(
            DISCOVERY._enabled_ipv4_networks(adapters),
            [("192.168.137.1", ipaddress.IPv4Network("192.168.137.0/24"))],
        )


class TestFH3XAsyncDiscovery(unittest.IsolatedAsyncioTestCase):
    """Verify socket failures and cleanup behavior."""

    async def test_partial_socket_failure_keeps_other_path_running(self) -> None:
        DISCOVERY.network.async_get_adapters = AsyncMock(
            return_value=[
                {
                    "enabled": True,
                    "ipv4": [{"address": "192.168.137.1", "network_prefix": 24}],
                }
            ]
        )
        fake_socket = MagicMock()
        transport = MagicMock()
        event_loop = asyncio.get_running_loop()
        create_endpoint = AsyncMock(return_value=(transport, MagicMock()))

        with (
            patch.object(
                DISCOVERY,
                "_create_socket",
                side_effect=[OSError("multicast blocked"), fake_socket],
            ),
            patch.object(event_loop, "create_datagram_endpoint", create_endpoint),
            patch.object(DISCOVERY, "MAX_DISCOVERY_ATTEMPTS", 1),
            patch.object(DISCOVERY, "DISCOVERY_TOTAL_WINDOW", 1),
        ):
            result = await DISCOVERY.async_discover_fh3x(object(), timeout=0)

        self.assertEqual(result, [])
        create_endpoint.assert_awaited_once()
        transport.sendto.assert_called_once_with(
            DISCOVERY._BROADCAST_REQUEST,
            (DISCOVERY.BROADCAST_ADDRESS, DISCOVERY.BROADCAST_PORT),
        )
        transport.close.assert_called_once()

    async def test_retries_only_after_a_full_response_window(self) -> None:
        DISCOVERY.network.async_get_adapters = AsyncMock(
            return_value=[
                {
                    "enabled": True,
                    "ipv4": [{"address": "192.168.137.1", "network_prefix": 24}],
                }
            ]
        )
        multicast_socket = MagicMock()
        broadcast_socket = MagicMock()
        multicast_transport = MagicMock()
        broadcast_transport = MagicMock()
        event_loop = asyncio.get_running_loop()
        create_endpoint = AsyncMock(
            side_effect=[
                (multicast_transport, MagicMock()),
                (broadcast_transport, MagicMock()),
            ]
        )

        with (
            patch.object(
                DISCOVERY,
                "_create_socket",
                side_effect=[multicast_socket, broadcast_socket],
            ),
            patch.object(event_loop, "create_datagram_endpoint", create_endpoint),
            patch.object(DISCOVERY, "MAX_DISCOVERY_ATTEMPTS", 3),
            patch.object(DISCOVERY, "DISCOVERY_TOTAL_WINDOW", 1),
        ):
            await DISCOVERY.async_discover_fh3x(object(), timeout=0.01)

        self.assertEqual(multicast_transport.sendto.call_count, 3)
        self.assertEqual(broadcast_transport.sendto.call_count, 3)
        multicast_transport.close.assert_called_once()
        broadcast_transport.close.assert_called_once()

    async def test_cancellation_closes_every_transport(self) -> None:
        DISCOVERY.network.async_get_adapters = AsyncMock(
            return_value=[
                {
                    "enabled": True,
                    "ipv4": [{"address": "192.168.137.1", "network_prefix": 24}],
                }
            ]
        )
        multicast_socket = MagicMock()
        broadcast_socket = MagicMock()
        multicast_transport = MagicMock()
        broadcast_transport = MagicMock()
        event_loop = asyncio.get_running_loop()
        create_endpoint = AsyncMock(
            side_effect=[
                (multicast_transport, MagicMock()),
                (broadcast_transport, MagicMock()),
            ]
        )

        async def cancel_wait(awaitable, _timeout=None, **_kwargs):
            awaitable.close()
            raise asyncio.CancelledError

        with (
            patch.object(
                DISCOVERY,
                "_create_socket",
                side_effect=[multicast_socket, broadcast_socket],
            ),
            patch.object(event_loop, "create_datagram_endpoint", create_endpoint),
            patch.object(
                DISCOVERY.asyncio,
                "wait_for",
                side_effect=cancel_wait,
            ),
            self.assertRaises(asyncio.CancelledError),
        ):
            await DISCOVERY.async_discover_fh3x(object())

        multicast_transport.close.assert_called_once()
        broadcast_transport.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
