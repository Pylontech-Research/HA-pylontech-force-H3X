"""Diagnostics support for Pylontech Force H3X."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import FH3XConfigEntry
from .const import BMS_DEVICE_ID, PCS_DEVICE_ID

TO_REDACT = {
    CONF_HOST,
    "serial",
    "pcs_extended_serial",
    "bms_pile_serial",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
) -> dict[str, Any]:
    """Return privacy-safe diagnostics for a config entry."""
    snapshot = entry.runtime_data.coordinator.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "identity": async_redact_data(
            {
                "manufacturer": snapshot.identity.manufacturer,
                "model": snapshot.identity.model,
                "serial": snapshot.identity.serial,
                "software_version": snapshot.identity.software_version,
            },
            TO_REDACT,
        ),
        "protocol": {
            "transport": "Modbus TCP",
            "pcs_device_id": PCS_DEVICE_ID,
            "bms_device_id": BMS_DEVICE_ID,
        },
        "values": dict(snapshot.values),
        "coordinator_last_update_success": (
            entry.runtime_data.coordinator.last_update_success
        ),
        "communication": {
            "data_stale": entry.runtime_data.coordinator.poll_failure_state.stale,
            "consecutive_poll_failures": (
                entry.runtime_data.coordinator.poll_failure_state.consecutive_failures
            ),
            "unavailable_after_failures": (
                entry.runtime_data.coordinator.poll_failure_state.failure_threshold
            ),
        },
    }
