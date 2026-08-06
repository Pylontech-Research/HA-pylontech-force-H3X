"""Tesla Powerwall demo device for previewing HA's native energy UI."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


class TeslaPowerwallDemoCoordinator(DataUpdateCoordinator[dict[str, float | bool]]):
    """Generate a believable but clearly synthetic Powerwall snapshot."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Tesla Powerwall Demo",
            update_interval=timedelta(seconds=2),
        )
        self._started = hass.loop.time()
        self.off_grid = False

    async def _async_update_data(self) -> dict[str, float | bool]:
        """Return the current simulated power flow."""
        elapsed = self.hass.loop.time() - self._started
        # A smooth daytime curve makes the dashboard useful for screenshots and
        # still shows the sign conventions used by the official integration.
        phase = (elapsed % 90) / 90 * 6.283185
        solar = max(0.0, 4.8 * __import__("math").sin(phase))
        load = 2.2 + 0.45 * __import__("math").sin(phase * 2 + 0.7)
        battery = 0.85 * __import__("math").sin(phase - 0.8)
        site = load + battery - solar
        charge = max(0.0, -battery)
        discharge = max(0.0, battery)
        soc = 61.0 + 3.0 * __import__("math").sin(elapsed / 180)
        return {
            "solar_now": round(solar, 3),
            "load_now": round(load, 3),
            "battery_now": round(battery, 3),
            "site_now": round(site, 3),
            "charge_percent": round(soc, 1),
            "backup_reserve": 20.0,
            "frequency": 50.0,
            "voltage": 230.0,
            "solar_import": round(elapsed / 3600 * 0.02, 3),
            "solar_export": round(elapsed / 3600 * 1.8, 3),
            "site_import": round(elapsed / 3600 * 0.7, 3),
            "site_export": round(elapsed / 3600 * 0.4, 3),
            "battery_import": round(elapsed / 3600 * 0.3, 3),
            "battery_export": round(elapsed / 3600 * 0.5, 3),
            "charging": charge > 0.05,
            "grid_services": True,
            "grid_status": not self.off_grid,
            "powerwall_status": True,
            "connected": True,
        }


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up the demo device from a config entry."""
    coordinator = TeslaPowerwallDemoCoordinator(hass)
    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the demo device."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
