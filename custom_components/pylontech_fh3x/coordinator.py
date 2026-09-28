"""Data update coordinator for Pylontech Force H3X."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .alarm_history import AlarmEventTracker
from .api import FH3XError, FH3XModbusClient
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_CONSECUTIVE_POLL_FAILURES,
)
from .period_stats import PeriodEnergyTracker
from .product import normalize_product_values
from .protocol import FH3XSnapshot
from .resilience import PollFailureState

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
        self._alarm_events: AlarmEventTracker | None = None
        self._period_stats = PeriodEnergyTracker(hass, entry.entry_id)
        self.poll_failure_state = PollFailureState(
            failure_threshold=MAX_CONSECUTIVE_POLL_FAILURES
        )
        # Keep a control write and its read-back refresh together.  The
        # coordinator's normal request refresh is debounced for 10 seconds;
        # without this lock, rapid UI changes can overlap and a stale refresh
        # can briefly put the previous schedule value back on screen.
        self._write_lock = asyncio.Lock()
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self._alarm_events = AlarmEventTracker(
            hass, entry.data.get("serial", "FH3X"), entry.title or "FH3X"
        )

    async def _async_update_data(self) -> FH3XSnapshot:
        try:
            snapshot = await self.client.async_read_snapshot()
        except FH3XError as err:
            preserve_snapshot = self.poll_failure_state.record_failure(
                has_snapshot=self.data is not None
            )
            if preserve_snapshot:
                _LOGGER.warning(
                    "FH3X poll failed (%s/%s); preserving the last snapshot: %s",
                    self.poll_failure_state.consecutive_failures,
                    self.poll_failure_state.failure_threshold,
                    err,
                )
                return self.data
            raise UpdateFailed(f"Unable to update FH3X data: {err}") from err
        previous_failures = self.poll_failure_state.record_success()
        if previous_failures:
            _LOGGER.info(
                "FH3X communication recovered after %s failed poll(s)",
                previous_failures,
            )
        # The shared protocol client provides stable legacy keys and raw
        # snapshots.  Normalize the product registration names at the
        # integration boundary so existing entity IDs remain untouched.
        values = normalize_product_values(snapshot.values, snapshot.identity)
        await self._period_stats.async_update(values)
        snapshot = replace(snapshot, values=values)
        if self._alarm_events is not None:
            self._alarm_events.process(snapshot)
        return snapshot

    async def async_write_u16(self, address: int, value: int) -> None:
        """Write a U16 control value and refresh all entities."""
        async with self._write_lock:
            await self.client.async_write_u16(address, value)
            # Bypass DataUpdateCoordinator's 10-second request debouncer so
            # select/number/switch entities reflect the verified value now.
            await self.async_refresh()

    async def async_write_s16(self, address: int, value: int) -> None:
        """Write an S16 control value and refresh all entities."""
        async with self._write_lock:
            await self.client.async_write_s16(address, value)
            await self.async_refresh()

    async def async_write_s32(self, address: int, value: int) -> None:
        """Write an S32 control value and refresh all entities."""
        async with self._write_lock:
            await self.client.async_write_s32(address, value)
            await self.async_refresh()

    async def async_update_u16_bit(
        self, address: int, bit_index: int, enabled: bool
    ) -> None:
        """Update one bit from the latest device value and refresh all entities."""
        async with self._write_lock:
            await self.client.async_update_u16_bit(address, bit_index, enabled)
            await self.async_refresh()
