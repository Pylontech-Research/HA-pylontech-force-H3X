#!/usr/bin/env python3
"""Probe the FH3X proprietary SSDP-like discovery endpoint.

This is a local diagnostic helper.  It mirrors the NetAssist setup used for
FH3X: the request is sent to 239.101.1.250:1900 from UDP source port 1901.
It does not connect to Modbus or change any Home Assistant device.
"""

from __future__ import annotations

import argparse
import socket
import struct
import time

MULTICAST_ADDRESS = "239.101.1.250"
MULTICAST_PORT = 1900
DEFAULT_SOURCE_PORT = 1901


def _request(host: str, port: int) -> bytes:
    return (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {host}:{port}\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 3\r\n"
        "ST: ssdp:all\r\n"
        "\r\n"
    ).encode("ascii")


def probe(
    host: str,
    port: int,
    source_port: int,
    timeout: float,
    interface: str | None = None,
) -> int:
    """Send one request and print every response received before timeout."""
    destination = (host, port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("B", 2))
        if interface:
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_IF,
                socket.inet_aton(interface),
            )
        sock.bind(("", source_port))
        sock.settimeout(max(timeout, 0.1))
        payload = _request(host, port)
        sent_at = time.monotonic()
        sock.sendto(payload, destination)
        print(f"sent {len(payload)} bytes from 0.0.0.0:{source_port} to {host}:{port}")

        count = 0
        while True:
            remaining = timeout - (time.monotonic() - sent_at)
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                response, source = sock.recvfrom(8192)
            except TimeoutError:
                break
            count += 1
            print(f"received {len(response)} bytes from {source[0]}:{source[1]}")
            print(response.decode("utf-8", errors="replace").rstrip())
            print()
        print(f"probe complete: {count} response(s)")
        return 0 if count else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=MULTICAST_ADDRESS)
    parser.add_argument("--port", type=int, default=MULTICAST_PORT)
    parser.add_argument("--source-port", type=int, default=DEFAULT_SOURCE_PORT)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--interface",
        help="Optional local IPv4 address used as IP_MULTICAST_IF",
    )
    args = parser.parse_args()
    return probe(args.host, args.port, args.source_port, args.timeout, args.interface)


if __name__ == "__main__":
    raise SystemExit(main())
