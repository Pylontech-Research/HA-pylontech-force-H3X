"""Number controls for Pylontech Force H3X."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FH3XConfigEntry
from .const import CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE
from .entity import FH3XCoordinatorEntity
from .profiles import profile_control_description


@dataclass(frozen=True, kw_only=True)
class FH3XNumberEntityDescription(NumberEntityDescription):
    """Describe an FH3X writable numeric register."""

    register_address: int
    register_type: Literal["u16", "s16", "s32"]
    raw_multiplier: float = 1
    required_ems_mode: int | None = None


NUMBER_DESCRIPTIONS = (
    FH3XNumberEntityDescription(
        key="charge_discharge_power_reference",
        translation_key="charge_discharge_power_reference",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40901,
        register_type="s16",
        raw_multiplier=10,
        required_ems_mode=4,
    ),
    FH3XNumberEntityDescription(
        key="charge_limit_soc",
        translation_key="charge_limit_soc",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=50,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40902,
        register_type="u16",
    ),
    FH3XNumberEntityDescription(
        key="eps_limit_soc_on_grid",
        translation_key="eps_limit_soc_on_grid",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=5,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40903,
        register_type="u16",
    ),
    FH3XNumberEntityDescription(
        key="eps_limit_soc_off_grid",
        translation_key="eps_limit_soc_off_grid",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=5,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40905,
        register_type="u16",
    ),
    FH3XNumberEntityDescription(
        key="meter_export_power_max",
        translation_key="meter_export_power_max",
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=-20000,
        native_max_value=-1,
        native_step=100,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40401,
        register_type="s32",
    ),
    FH3XNumberEntityDescription(
        key="peak_shaving_safety_soc",
        translation_key="peak_shaving_safety_soc",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40974,
        register_type="u16",
    ),
    FH3XNumberEntityDescription(
        key="peak_shaving_meter_power_limit",
        translation_key="peak_shaving_meter_power_limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=60000,
        native_step=100,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register_address=40975,
        register_type="u16",
    ),
    *(
        FH3XNumberEntityDescription(
            key=f"period_{period}_power",
            translation_key="schedule_power",
            translation_placeholders={"period": str(period)},
            native_unit_of_measurement=PERCENTAGE,
            native_min_value=0,
            native_max_value=100,
            native_step=1,
            mode=NumberMode.SLIDER,
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
            register_address=40912 + (period - 1) * 6,
            register_type="u16",
            raw_multiplier=10,
        )
        for period in range(1, 5)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FH3X number controls."""
    coordinator = entry.runtime_data.coordinator
    profile = entry.options.get(CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE)
    async_add_entities(
        FH3XNumber(coordinator, profile_control_description(description, profile))
        for description in NUMBER_DESCRIPTIONS
    )


class FH3XNumber(FH3XCoordinatorEntity, NumberEntity):
    """Represent one verified FH3X numeric setting."""

    entity_description: FH3XNumberEntityDescription

    def __init__(self, coordinator: Any, description: FH3XNumberEntityDescription):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.values.get(self.entity_description.key)
        return float(value) if isinstance(value, int | float) else None

    @property
    def available(self) -> bool:
        """Disable mode-dependent controls until their prerequisite is active."""
        description = self.entity_description
        return super().available and (
            description.required_ems_mode is None
            or self.coordinator.data.values.get("ems_mode")
            == description.required_ems_mode
        )

    @property
    def native_max_value(self) -> float:
        """Use the reported PCS rating for the peak-shaving slider when possible."""
        configured_max = float(self.entity_description.native_max_value)
        if self.entity_description.key != "peak_shaving_meter_power_limit":
            return configured_max
        rated_power = self.coordinator.data.values.get("pcs_max_output_power")
        if isinstance(rated_power, int | float) and rated_power > 0:
            return min(configured_max, float(rated_power))
        return configured_max

    async def async_set_native_value(self, value: float) -> None:
        description = self.entity_description
        if (
            description.required_ems_mode is not None
            and self.coordinator.data.values.get("ems_mode")
            != description.required_ems_mode
        ):
            raise HomeAssistantError(
                "Set EMS mode to User mode before changing the charge/discharge "
                "power reference."
            )

        raw_value = round(value * description.raw_multiplier)
        if description.register_type == "u16":
            await self._async_write_u16(description.register_address, raw_value)
        elif description.register_type == "s16":
            await self._async_write_s16(description.register_address, raw_value)
        else:
            await self._async_write_s32(description.register_address, raw_value)
