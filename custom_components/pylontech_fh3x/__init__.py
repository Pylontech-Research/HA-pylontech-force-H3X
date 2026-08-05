"""Pylontech Force H3X integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .api import FH3XModbusClient
from .const import CONF_DETAILED_BMS, DEFAULT_DETAILED_BMS
from .coordinator import FH3XCoordinator

PANEL_DATA_KEY = "panel_registered"

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TIME,
]


@dataclass
class FH3XRuntimeData:
    """Runtime objects associated with a config entry."""

    client: FH3XModbusClient
    coordinator: FH3XCoordinator


FH3XConfigEntry: TypeAlias = ConfigEntry[FH3XRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: FH3XConfigEntry) -> bool:
    """Set up an FH3X from a config entry."""
    if not hass.data.setdefault("pylontech_fh3x", {}).get(PANEL_DATA_KEY):
        await _async_register_panel(hass)
        hass.data["pylontech_fh3x"][PANEL_DATA_KEY] = True

    client = FH3XModbusClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        detailed_bms=entry.options.get(CONF_DETAILED_BMS, DEFAULT_DETAILED_BMS),
    )
    coordinator = FH3XCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = FH3XRuntimeData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FH3XConfigEntry) -> bool:
    """Unload an FH3X config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.client.async_close()
    return unload_ok


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the commercial FH3X panel once for the HA instance."""
    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/pylontech_fh3x_panel", str(frontend_path), False)]
    )
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="fh3x-energy-panel",
        frontend_url_path="fh3x",
        sidebar_title="FH3X 能源中心",
        sidebar_icon="mdi:solar-power-variant",
        module_url="/pylontech_fh3x_panel/fh3x-panel.js?v=0.5.0",
        embed_iframe=False,
        require_admin=False,
    )
