"""Pylontech Force H3X integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .api import FH3XModbusClient
from .const import (
    CONF_CONTROL_PROFILE,
    CONF_DETAILED_BMS,
    CONF_ENTITY_PROFILE,
    DEFAULT_CONTROL_PROFILE,
    DEFAULT_DETAILED_BMS,
    DEFAULT_ENTITY_PROFILE,
)
from .coordinator import FH3XCoordinator
from .profiles import (
    apply_profiles_to_registry,
    async_apply_english_names_to_registry,
)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TIME,
]

_PANEL_REGISTERED = "panel_registered"


@dataclass
class FH3XRuntimeData:
    """Runtime objects associated with a config entry."""

    client: FH3XModbusClient
    coordinator: FH3XCoordinator


FH3XConfigEntry: TypeAlias = ConfigEntry[FH3XRuntimeData]


async def _async_apply_english_names_after_platform_setup(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
) -> None:
    """Apply names after HA has finished persisting platform entity metadata."""
    await asyncio.sleep(1)
    await async_apply_english_names_to_registry(hass, entry)


async def async_setup_entry(hass: HomeAssistant, entry: FH3XConfigEntry) -> bool:
    """Set up an FH3X from a config entry."""
    if not hass.data.setdefault("pylontech_fh3x", {}).get(_PANEL_REGISTERED):
        await _async_register_panel(hass)
        hass.data["pylontech_fh3x"][_PANEL_REGISTERED] = True
    entity_profile = entry.options.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
    control_profile = entry.options.get(CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE)
    # Apply the profile before touching the network. Existing installations
    # must still get a cleaned-up device page when the inverter is offline and
    # the first coordinator refresh enters setup retry.
    apply_profiles_to_registry(hass, entry, entity_profile, control_profile)
    await async_apply_english_names_to_registry(hass, entry)

    client = FH3XModbusClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        detailed_bms=entry.options.get(CONF_DETAILED_BMS, DEFAULT_DETAILED_BMS),
    )
    coordinator = FH3XCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = FH3XRuntimeData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Entity registry entries keep their previous enabled/disabled state across
    # upgrades.  Reapply the selected exposure tier so changing the recommended
    # default also cleans up existing installations that never chose a profile.
    apply_profiles_to_registry(
        hass,
        entry,
        entity_profile,
        control_profile,
    )
    # Platform entity registration can persist the system-language original
    # name after async_forward_entry_setups returns. Run the final migration on
    # the next settled event-loop turn so it remains authoritative.
    hass.async_create_task(
        _async_apply_english_names_after_platform_setup(hass, entry),
        "Apply FH3X English entity names",
    )
    return True


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the local FH3X panel once for the HA instance."""
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
        module_url="/pylontech_fh3x_panel/fh3x-panel.js?v=0.6.26",
        embed_iframe=False,
        require_admin=False,
    )


async def async_unload_entry(hass: HomeAssistant, entry: FH3XConfigEntry) -> bool:
    """Unload an FH3X config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.client.async_close()
    return unload_ok
