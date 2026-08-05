"""Data update coordinator for Pylontech Force H3X."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FH3XError, FH3XModbusClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .protocol import FH3XSnapshot

_LOGGER = logging.getLogger(__name__)


class FH3XCoordinator(DataUpdateCoordinator[FH3XSnapshot]):
    """Coordinate a single poll shared by every FH3X entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: FH3XModbusClient,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )

    async def _async_update_data(self) -> FH3XSnapshot:
        try:
            return await self.client.async_read_snapshot()
        except FH3XError as err:
            raise UpdateFailed(f"Unable to update FH3X data: {err}") from err

    async def async_write_u16(self, address: int, value: int) -> None:
        """Write a U16 control value and refresh all entities."""
        await self.client.async_write_u16(address, value)
        await self.async_request_refresh()

    async def async_write_s16(self, address: int, value: int) -> None:
        """Write an S16 control value and refresh all entities."""
        await self.client.async_write_s16(address, value)
        await self.async_request_refresh()

    async def async_write_s32(self, address: int, value: int) -> None:
        """Write an S32 control value and refresh all entities."""
        await self.client.async_write_s32(address, value)
        await self.async_request_refresh()
