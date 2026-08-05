"""Time controls for Pylontech Force H3X schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FH3XConfigEntry
from .entity import FH3XCoordinatorEntity


@dataclass(frozen=True, kw_only=True)
class FH3XTimeEntityDescription(TimeEntityDescription):
    """Describe an FH3X schedule time register."""

    register_address: int


TIME_DESCRIPTIONS = tuple(
    description
    for period in range(1, 5)
    for description in (
        FH3XTimeEntityDescription(
            key=f"period_{period}_start",
            name=f"Schedule period {period} start",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            register_address=40909 + (period - 1) * 6,
        ),
        FH3XTimeEntityDescription(
            key=f"period_{period}_end",
            name=f"Schedule period {period} end",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            register_address=40910 + (period - 1) * 6,
        ),
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FH3X schedule time controls."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        FH3XScheduleTime(coordinator, description) for description in TIME_DESCRIPTIONS
    )


class FH3XScheduleTime(FH3XCoordinatorEntity, TimeEntity):
    """Represent one schedule start or end time."""

    entity_description: FH3XTimeEntityDescription

    def __init__(self, coordinator: Any, description: FH3XTimeEntityDescription):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> time | None:
        value = self.coordinator.data.values.get(self.entity_description.key)
        if not isinstance(value, str) or value == "invalid":
            return None
        try:
            hour, minute = (int(part) for part in value.split(":", 1))
            return time(hour=hour, minute=minute)
        except (TypeError, ValueError):
            return None

    async def async_set_value(self, value: time) -> None:
        encoded = (value.hour << 8) | value.minute
        await self._async_write_u16(self.entity_description.register_address, encoded)
