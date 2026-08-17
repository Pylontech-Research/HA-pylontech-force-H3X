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

MAX_DISCOVERY_ATTEMPTS = 3
RESPONSE_WINDOW = 3.5
DISCOVERY_TOTAL_WINDOW = 15.0
# Backwards-compatible name for callers that used the old timeout constant.
DISCOVERY_TIMEOUT = RESPONSE_WINDOW
MULTICAST_ADDRESS = "239.101.1.250"
MULTICAST_PORT = 1900
MULTICAST_SOURCE_PORT = 1901
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
        """Return a stable candidate key across multicast, broadcast and IP changes."""
        if self.usn:
            return ("usn", self.usn)
        return ("host", self.host)

    @property
    def display_name(self) -> str:
        """Return a concise label for the config-flow selector."""
        identity = self.usn or "Unknown serial"
        return f"{self.server} · {identity} · {self.host}"


def parse_discovery_response(
    payload: bytes,
    source_host: str,
    local_networks: Iterable[ipaddress.IPv4Network] = (),
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
    # FH3X discovery traffic can be forwarded between private VLANs/subnets.
    # Do not require the response source to belong to the HA interface prefix;
    # the candidate is authoritatively verified over Modbus before setup.
    if not source.is_private or source.is_loopback or source.is_link_local:
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
        key = discovered.deduplication_key
        previous = unique.get(key)
        if previous is not None and previous.host != discovered.host and discovered.usn:
            _LOGGER.warning(
                "FH3X discovery reported USN %s from multiple IPs: %s and %s; "
                "using the latest response",
                discovered.usn,
                previous.host,
                discovered.host,
            )
        unique[key] = discovered
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
        response_event: asyncio.Event,
    ) -> None:
        self._local_networks = local_networks
        self._results = results
        self._response_event = response_event

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Parse a response without blocking the event loop."""
        _LOGGER.debug(
            "FH3X discovery received %s bytes from %s:%s",
            len(data),
            addr[0],
            addr[1],
        )
        discovered = parse_discovery_response(data, addr[0], self._local_networks)
        if discovered is not None:
            self._results.append(discovered)
            self._response_event.set()

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
        # The device only responds after receiving M-SEARCH on its proprietary
        # multicast group.  HA may have several network paths (for example a
        # USB/Ethernet shared network plus the Supervisor bridge), so select
        # the enabled adapter explicitly instead of letting the default route
        # choose a possibly unrelated interface.
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_IF,
            socket.inet_aton(local_address),
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("B", 2))
    # HA's built-in standards-compliant SSDP scanner already owns UDP 1900.
    # FH3X replies to the request's source port, so use the verified alternate
    # port 1901 and avoid competing with the built-in SSDP socket.
    # Binding broadcast to the adapter address becomes invalid when HA's
    # network manager has a stale address during a Wi-Fi/Ethernet handover.
    # An unspecified local address lets the kernel select the current route.
    sock.bind(("", BROADCAST_PORT if broadcast else MULTICAST_SOURCE_PORT))
    sock.setblocking(False)
    return sock


async def async_discover_fh3x(
    hass: HomeAssistant,
    *,
    timeout: float = RESPONSE_WINDOW,
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
    response_event = asyncio.Event()
    requests: list[tuple[asyncio.DatagramTransport, tuple[str, int], str, int]] = []

    try:
        for local_address, _local_network in interfaces:
            for is_broadcast, destination in (
                (False, (MULTICAST_ADDRESS, MULTICAST_PORT)),
                (True, (BROADCAST_ADDRESS, BROADCAST_PORT)),
            ):
                sock: socket.socket | None = None
                try:
                    sock = _create_socket(local_address, broadcast=is_broadcast)
                    transport, _protocol = await loop.create_datagram_endpoint(
                        lambda: _FH3XDiscoveryProtocol(
                            local_networks, results, response_event
                        ),
                        sock=sock,
                    )
                    transports.append(transport)
                    requests.append(
                        (
                            transport,
                            destination,
                            local_address,
                            BROADCAST_PORT if is_broadcast else MULTICAST_SOURCE_PORT,
                        )
                    )
                    _LOGGER.debug(
                        "FH3X discovery sent from %s:%s to %s:%s",
                        local_address,
                        BROADCAST_PORT if is_broadcast else MULTICAST_SOURCE_PORT,
                        destination[0],
                        destination[1],
                    )
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
        # MX is a maximum response delay. Retry at most three times, but keep
        # listening for late devices until the total discovery window ends.
        deadline = loop.time() + DISCOVERY_TOTAL_WINDOW
        for attempt in range(1, MAX_DISCOVERY_ATTEMPTS + 1):
            if loop.time() >= deadline:
                break
            response_event.clear()
            for transport, destination, local_address, source_port in requests:
                try:
                    transport.sendto(
                        _BROADCAST_REQUEST
                        if destination[0] == BROADCAST_ADDRESS
                        else _MULTICAST_REQUEST,
                        destination,
                    )
                except OSError as err:
                    _LOGGER.debug(
                        "Unable to retry FH3X discovery from %s:%s to %s:%s: %s",
                        local_address,
                        source_port,
                        destination[0],
                        destination[1],
                        err,
                    )
                _LOGGER.debug(
                    "FH3X discovery %s from %s:%s to %s:%s",
                    "sent"
                    if attempt == 1
                    else f"retry {attempt}/{MAX_DISCOVERY_ATTEMPTS}",
                    local_address,
                    source_port,
                    destination[0],
                    destination[1],
                )
            try:
                remaining = min(timeout, max(0, deadline - loop.time()))
                await asyncio.wait_for(response_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                if attempt < MAX_DISCOVERY_ATTEMPTS and loop.time() < deadline:
                    continue
                break
            break

        remaining = deadline - loop.time()
        if remaining > 0:
            await asyncio.sleep(remaining)
    finally:
        for transport in transports:
            transport.close()

    return deduplicate_discoveries(results)
