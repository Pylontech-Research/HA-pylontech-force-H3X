"""Switches exposed by the Tesla Powerwall demo."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeslaPowerwallDemoCoordinator
from .entity import TeslaPowerwallDemoEntity


class TeslaPowerwallDemoOffGridSwitch(TeslaPowerwallDemoEntity, SwitchEntity):
    """Simulate the official Powerwall off-grid operation switch."""

    _attr_name = "Off-Grid operation"
    _attr_icon = "mdi:transmission-tower-off"

    def __init__(self, coordinator: TeslaPowerwallDemoCoordinator) -> None:
        super().__init__(coordinator, "off_grid")

    @property
    def is_on(self) -> bool:
        return self.coordinator.off_grid

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.off_grid = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.off_grid = False
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the demo switch."""
    coordinator = hass.data["tesla_powerwall_demo"][entry.entry_id]
    async_add_entities([TeslaPowerwallDemoOffGridSwitch(coordinator)])
