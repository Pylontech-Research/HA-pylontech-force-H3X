"""Switch controls for Pylontech Force H3X."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FH3XConfigEntry
from .const import CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE
from .entity import FH3XCoordinatorEntity
from .profiles import profile_control_description


@dataclass(frozen=True, kw_only=True)
class FH3XSwitchEntityDescription(SwitchEntityDescription):
    """Describe an FH3X writable on/off register."""

    register_address: int
    data_key: str | None = None
    bit_index: int | None = None


SWITCH_DESCRIPTIONS = (
    FH3XSwitchEntityDescription(
        key="eps_enabled",
        translation_key="eps_enabled",
        entity_registry_enabled_default=False,
        register_address=40904,
    ),
    FH3XSwitchEntityDescription(
        key="heat_pump_enabled",
        translation_key="heat_pump_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40848,
    ),
    FH3XSwitchEntityDescription(
        key="period_1_enabled",
        translation_key="period_1_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40908,
    ),
    FH3XSwitchEntityDescription(
        key="period_2_enabled",
        translation_key="period_2_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40914,
    ),
    FH3XSwitchEntityDescription(
        key="period_3_enabled",
        translation_key="period_3_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40920,
    ),
    FH3XSwitchEntityDescription(
        key="period_4_enabled",
        translation_key="period_4_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40926,
    ),
    FH3XSwitchEntityDescription(
        key="peak_shaving_enabled",
        translation_key="peak_shaving_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40973,
    ),
    *(
        FH3XSwitchEntityDescription(
            key=f"period_{period}_{day}",
            translation_key=f"schedule_{day}",
            translation_placeholders={"period": str(period)},
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            register_address=40913 + (period - 1) * 6,
            data_key=f"period_{period}_weekday_mask",
            bit_index=bit,
        )
        for period in range(1, 5)
        for bit, day in enumerate(
            (
                "sunday",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
            )
        )
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FH3X switches."""
    coordinator = entry.runtime_data.coordinator
    profile = entry.options.get(CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE)
    async_add_entities(
        FH3XSwitch(coordinator, profile_control_description(description, profile))
        for description in SWITCH_DESCRIPTIONS
    )


class FH3XSwitch(FH3XCoordinatorEntity, SwitchEntity):
    """Represent a verified FH3X switch setting."""

    entity_description: FH3XSwitchEntityDescription

    def __init__(self, coordinator: Any, description: FH3XSwitchEntityDescription):
        super().__init__(
            coordinator,
            description.key,
            value_key=description.data_key,
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        description = self.entity_description
        value = self.coordinator.data.values.get(
            description.data_key or description.key
        )
        if description.bit_index is not None and isinstance(value, int):
            return bool(value & (1 << description.bit_index))
        return value if isinstance(value, bool) else None

    async def _async_set_state(self, enabled: bool) -> None:
        description = self.entity_description
        if description.bit_index is None:
            await self._async_write_u16(description.register_address, int(enabled))
            return

        current = self.coordinator.data.values.get(description.data_key or "")
        if not isinstance(current, int):
            return
        mask = 1 << description.bit_index
        value = current | mask if enabled else current & ~mask
        await self._async_write_u16(description.register_address, value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_state(False)
