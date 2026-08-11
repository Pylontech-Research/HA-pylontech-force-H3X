"""Select controls for Pylontech Force H3X."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FH3XConfigEntry
from .const import CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE
from .entity import FH3XCoordinatorEntity
from .profiles import profile_control_description

EMS_MODE_TO_REGISTER = {
    "self_consumption": 0,
    "backup": 1,
    "off_grid": 2,
    "feed_in_priority": 3,
    "user": 4,
    "pn_customer": 5,
}
REGISTER_TO_EMS_MODE = {value: key for key, value in EMS_MODE_TO_REGISTER.items()}
SCHEDULE_MODE_TO_REGISTER = {"charge": 0, "discharge": 1}
REGISTER_TO_SCHEDULE_MODE = {
    value: key for key, value in SCHEDULE_MODE_TO_REGISTER.items()
}


@dataclass(frozen=True, kw_only=True)
class FH3XScheduleSelectDescription(SelectEntityDescription):
    """Describe one schedule-mode register."""

    register_address: int


EMS_MODE_DESCRIPTION = SelectEntityDescription(
    key="ems_mode",
    translation_key="ems_mode",
    options=list(EMS_MODE_TO_REGISTER),
    entity_category=EntityCategory.CONFIG,
    entity_registry_enabled_default=False,
)

SCHEDULE_MODE_DESCRIPTIONS = tuple(
    FH3XScheduleSelectDescription(
        key=f"period_{period}_mode",
        translation_key="schedule_mode",
        translation_placeholders={"period": str(period)},
        options=list(SCHEDULE_MODE_TO_REGISTER),
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40911 + (period - 1) * 6,
    )
    for period in range(1, 5)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the FH3X EMS mode control."""
    coordinator = entry.runtime_data.coordinator
    profile = entry.options.get(CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE)
    async_add_entities(
        [
            FH3XEMSModeSelect(
                coordinator,
                profile_control_description(EMS_MODE_DESCRIPTION, profile),
            )
        ]
        + [
            FH3XScheduleModeSelect(
                coordinator,
                profile_control_description(description, profile),
            )
            for description in SCHEDULE_MODE_DESCRIPTIONS
        ]
    )


class FH3XEMSModeSelect(FH3XCoordinatorEntity, SelectEntity):
    """Select the inverter EMS operating mode."""

    entity_description: SelectEntityDescription

    def __init__(self, coordinator: Any, description: SelectEntityDescription):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.values.get(self.entity_description.key)
        return REGISTER_TO_EMS_MODE.get(value) if isinstance(value, int) else None

    async def async_select_option(self, option: str) -> None:
        await self._async_write_u16(40907, EMS_MODE_TO_REGISTER[option])


class FH3XScheduleModeSelect(FH3XCoordinatorEntity, SelectEntity):
    """Select charge or discharge for one schedule period."""

    entity_description: FH3XScheduleSelectDescription

    def __init__(self, coordinator: Any, description: FH3XScheduleSelectDescription):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.values.get(self.entity_description.key)
        if value in SCHEDULE_MODE_TO_REGISTER:
            return str(value)
        if isinstance(value, int):
            return REGISTER_TO_SCHEDULE_MODE.get(value)
        return None

    async def async_select_option(self, option: str) -> None:
        await self._async_write_u16(
            self.entity_description.register_address,
            SCHEDULE_MODE_TO_REGISTER[option],
        )
