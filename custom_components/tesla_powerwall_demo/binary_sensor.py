"""Binary sensors exposed by the Tesla Powerwall demo."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeslaPowerwallDemoCoordinator
from .entity import TeslaPowerwallDemoEntity


DESCRIPTIONS = (
    BinarySensorEntityDescription(key="grid_services", name="Grid Services"),
    BinarySensorEntityDescription(key="grid_status", name="Grid Status", device_class=BinarySensorDeviceClass.CONNECTIVITY),
    BinarySensorEntityDescription(key="charging", name="Powerwall Charging", device_class=BinarySensorDeviceClass.BATTERY_CHARGING),
    BinarySensorEntityDescription(key="connected", name="Powerwall Connected to Tesla", device_class=BinarySensorDeviceClass.CONNECTIVITY),
    BinarySensorEntityDescription(key="powerwall_status", name="Powerwall Status", device_class=BinarySensorDeviceClass.RUNNING),
)


class TeslaPowerwallDemoBinarySensor(TeslaPowerwallDemoEntity, BinarySensorEntity):
    """A simulated Powerwall binary sensor."""

    def __init__(self, coordinator: TeslaPowerwallDemoCoordinator, description: BinarySensorEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get(self._key, False))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the demo binary sensors."""
    coordinator = hass.data["tesla_powerwall_demo"][entry.entry_id]
    async_add_entities(
        TeslaPowerwallDemoBinarySensor(coordinator, description)
        for description in DESCRIPTIONS
    )
