"""Compatibility exports for the shared Pylontech FH3X protocol library."""

import asyncio

from pylontech_fh3x import (
    FH3XConnectionError,
    FH3XError,
    FH3XIdentity,
    FH3XModbusClient,
    FH3XProtocolError,
)
from pylontech_fh3x.client import _LOGGER
from pylontech_fh3x.constants import (
    BMS_DEVICE_ID,
    DEFAULT_DEVICE_SWITCH_DELAY,
    DEFAULT_READ_RETRIES,
    DEFAULT_READ_RETRY_DELAY,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_TIMEOUT,
    PCS_DEVICE_ID,
)
from pylontech_fh3x.protocol import (
    BMS_LOAD_ENERGY_ADDRESS,
    BMS_PARALLEL_LOAD_ENERGY_ADDRESS,
    BMS_PILE_NOMINAL_ADDRESS,
    PCS_MONITOR_EXT_COUNT,
)

__all__ = [
    "BMS_DEVICE_ID",
    "BMS_LOAD_ENERGY_ADDRESS",
    "BMS_PARALLEL_LOAD_ENERGY_ADDRESS",
    "BMS_PILE_NOMINAL_ADDRESS",
    "DEFAULT_DEVICE_SWITCH_DELAY",
    "DEFAULT_READ_RETRIES",
    "DEFAULT_READ_RETRY_DELAY",
    "DEFAULT_REQUEST_INTERVAL",
    "DEFAULT_TIMEOUT",
    "PCS_DEVICE_ID",
    "PCS_MONITOR_EXT_COUNT",
    "_LOGGER",
    "FH3XConnectionError",
    "FH3XError",
    "FH3XIdentity",
    "FH3XModbusClient",
    "FH3XProtocolError",
    "asyncio",
]
