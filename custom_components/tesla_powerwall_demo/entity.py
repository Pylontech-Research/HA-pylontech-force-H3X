"""Shared entities for the Tesla Powerwall demo."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import TeslaPowerwallDemoCoordinator


class TeslaPowerwallDemoEntity(CoordinatorEntity[TeslaPowerwallDemoCoordinator]):
    """Base entity with official Powerwall-like device metadata."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TeslaPowerwallDemoCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"tesla_powerwall_demo_{key}"
        self._attr_suggested_object_id = f"tesla_demo_{key}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "tesla_powerwall_demo")},
            "name": "Tesla Powerwall（模拟设备）",
            "manufacturer": "Tesla",
            "model": "Powerwall 2 · Demo",
            "sw_version": "simulated",
        }

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)
