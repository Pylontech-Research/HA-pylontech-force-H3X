"""Base entity for Pylontech Force H3X."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FH3XError
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import FH3XCoordinator


class FH3XCoordinatorEntity(CoordinatorEntity[FH3XCoordinator]):
    """Base for entities backed by the shared FH3X coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FH3XCoordinator,
        key: str,
        *,
        require_direct_value: bool = True,
        value_key: str | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._fh3x_key = value_key or key
        self._require_direct_value = require_direct_value
        identity = coordinator.data.identity
        self._attr_unique_id = f"{identity.serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identity.serial)},
            name=identity.model or MODEL,
            manufacturer=identity.manufacturer or MANUFACTURER,
            model=identity.model or MODEL,
            serial_number=identity.serial,
            sw_version=identity.software_version,
        )

    @property
    def available(self) -> bool:
        """Return whether the coordinator has this entity's current value."""
        return super().available and (
            not self._require_direct_value
            or self._fh3x_key in self.coordinator.data.values
        )

    async def _async_write_u16(self, address: int, value: int) -> None:
        try:
            await self.coordinator.async_write_u16(address, value)
        except FH3XError as err:
            raise HomeAssistantError(f"FH3X rejected the setting: {err}") from err

    async def _async_write_s16(self, address: int, value: int) -> None:
        try:
            await self.coordinator.async_write_s16(address, value)
        except FH3XError as err:
            raise HomeAssistantError(f"FH3X rejected the setting: {err}") from err

    async def _async_write_s32(self, address: int, value: int) -> None:
        try:
            await self.coordinator.async_write_s32(address, value)
        except FH3XError as err:
            raise HomeAssistantError(f"FH3X rejected the setting: {err}") from err
