"""Local network discovery for Pylontech Force H3X devices."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import struct
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components import network
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 4.0
MULTICAST_ADDRESS = "239.101.1.250"
MULTICAST_PORT = 1900
BROADCAST_ADDRESS = "255.255.255.255"
BROADCAST_PORT = 10088

_MULTICAST_REQUEST = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {MULTICAST_ADDRESS}:{MULTICAST_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 3\r\n"
    "ST: ssdp:all\r\n"
    "\r\n"
).encode()

_BROADCAST_REQUEST = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {BROADCAST_ADDRESS}:{BROADCAST_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 3\r\n"
    "ST: ssdp:all\r\n"
    "\r\n"
).encode()


@dataclass(frozen=True, slots=True)
class FH3XDiscoveryInfo:
    """An FH3X returned by the proprietary SSDP-like protocol."""

    host: str
    port: int
    server: str
    device_address: int
    usn: str | None = None
    search_target: str | None = None
    cache_control: str | None = None

    @property
    def deduplication_key(self) -> tuple[str, str]:
        """Return the protocol-defined candidate identity key."""
        return (self.usn or "", self.host)

    @property
    def display_name(self) -> str:
        """Return a concise label for the config-flow selector."""
        identity = self.usn or "Unknown serial"
        return f"{self.server} · {identity} · {self.host}"


def parse_discovery_response(
    payload: bytes,
    source_host: str,
    local_networks: Iterable[ipaddress.IPv4Network],
) -> FH3XDiscoveryInfo | None:
    """Parse and validate one proprietary SSDP response."""
    try:
        message = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None

    lines = message.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip().upper() != "HTTP/1.1 200 OK":
        return None

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        name, separator, value = line.partition(":")
        if not separator or not name.strip():
            return None
        headers[name.strip().lower()] = value.strip()

    server = headers.get("server", "")
    if "FH3X" not in server.upper():
        return None

    try:
        device_address = int(headers.get("ext", ""))
    except ValueError:
        return None
    if device_address not in (1, 2):
        return None

    try:
        source = ipaddress.IPv4Address(source_host)
    except ipaddress.AddressValueError:
        return None
    if (
        source.is_unspecified
        or source.is_loopback
        or source.is_multicast
        or source.is_link_local
        or not any(source in local_network for local_network in local_networks)
    ):
        return None

    return FH3XDiscoveryInfo(
        host=str(source),
        port=DEFAULT_PORT,
        server=server,
        device_address=device_address,
        usn=headers.get("usn") or None,
        search_target=headers.get("st") or None,
        cache_control=headers.get("cache-control") or None,
    )


def deduplicate_discoveries(
    discoveries: Iterable[FH3XDiscoveryInfo],
) -> list[FH3XDiscoveryInfo]:
    """Deduplicate multicast and broadcast responses while preserving order."""
    unique: dict[tuple[str, str], FH3XDiscoveryInfo] = {}
    for discovered in discoveries:
        unique.setdefault(discovered.deduplication_key, discovered)
    return list(unique.values())


def _enabled_ipv4_networks(
    adapters: Iterable[Mapping[str, Any]],
) -> list[tuple[str, ipaddress.IPv4Network]]:
    """Return enabled local IPv4 addresses and networks from HA adapters."""
    result: list[tuple[str, ipaddress.IPv4Network]] = []
    for adapter in adapters:
        if not adapter.get("enabled", False):
            continue
        for ipv4 in adapter.get("ipv4", []):
            address = str(ipv4.get("address", ""))
            prefix = ipv4.get("network_prefix")
            try:
                local_address = ipaddress.IPv4Address(address)
                local_network = ipaddress.IPv4Network(
                    f"{local_address}/{prefix}", strict=False
                )
            except (
                ipaddress.AddressValueError,
                ipaddress.NetmaskValueError,
                TypeError,
            ):
                continue
            if local_address.is_loopback or local_address.is_link_local:
                continue
            result.append((str(local_address), local_network))
    return result


class _FH3XDiscoveryProtocol(asyncio.DatagramProtocol):
    """Collect UDP responses until the discovery timeout expires."""

    def __init__(
        self,
        local_networks: tuple[ipaddress.IPv4Network, ...],
        results: list[FH3XDiscoveryInfo],
    ) -> None:
        self._local_networks = local_networks
        self._results = results

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Parse a response without blocking the event loop."""
        discovered = parse_discovery_response(data, addr[0], self._local_networks)
        if discovered is not None:
            self._results.append(discovered)

    def error_received(self, exc: Exception) -> None:
        """Log a per-socket error without failing other adapters."""
        _LOGGER.debug("FH3X discovery socket error: %s", exc)


def _create_socket(local_address: str, *, broadcast: bool) -> socket.socket:
    """Create a non-blocking UDP discovery socket bound to one interface."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if broadcast:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    else:
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_IF,
            socket.inet_aton(local_address),
        )
        membership = socket.inet_aton(MULTICAST_ADDRESS) + socket.inet_aton(
            local_address
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("B", 1))
    # The FH3X firmware listens and replies on the protocol port rather than
    # guaranteeing a unicast response to an ephemeral source port. Bind the
    # same way as its reference implementation; SO_REUSEADDR permits HA's
    # standard SSDP listener to coexist on port 1900.
    sock.bind(
        (
            local_address if broadcast else "",
            BROADCAST_PORT if broadcast else MULTICAST_PORT,
        )
    )
    sock.setblocking(False)
    return sock


async def async_discover_fh3x(
    hass: HomeAssistant,
    *,
    timeout: float = DISCOVERY_TIMEOUT,
) -> list[FH3XDiscoveryInfo]:
    """Actively discover FH3X devices on all HA-enabled IPv4 adapters."""
    adapters = await network.async_get_adapters(hass)
    interfaces = _enabled_ipv4_networks(adapters)
    if not interfaces:
        return []

    loop = asyncio.get_running_loop()
    local_networks = tuple(network_ for _, network_ in interfaces)
    results: list[FH3XDiscoveryInfo] = []
    transports: list[asyncio.DatagramTransport] = []

    try:
        for local_address, _local_network in interfaces:
            for is_broadcast, destination, request in (
                (
                    False,
                    (MULTICAST_ADDRESS, MULTICAST_PORT),
                    _MULTICAST_REQUEST,
                ),
                (True, (BROADCAST_ADDRESS, BROADCAST_PORT), _BROADCAST_REQUEST),
            ):
                sock: socket.socket | None = None
                try:
                    sock = _create_socket(local_address, broadcast=is_broadcast)
                    transport, _protocol = await loop.create_datagram_endpoint(
                        lambda: _FH3XDiscoveryProtocol(local_networks, results),
                        sock=sock,
                    )
                    transports.append(transport)
                    transport.sendto(request, destination)
                except OSError as err:
                    if sock is not None:
                        sock.close()
                    _LOGGER.debug(
                        "Unable to start FH3X discovery on %s via %s: %s",
                        local_address,
                        "broadcast" if is_broadcast else "multicast",
                        err,
                    )

        if not transports:
            return []
        await asyncio.sleep(timeout)
    finally:
        for transport in transports:
            transport.close()

    return deduplicate_discoveries(results)
