"""Persisted daily and monthly energy views derived from lifetime counters."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .protocol import FH3XValue

_STORAGE_VERSION = 1
_MAX_SAMPLE_GAP_SECONDS = 300
_MAX_UNCONFIRMED_CHANGE_KWH = 10

_COUNTERS = {
    "battery_charge_energy": "battery_charge_energy",
    "battery_discharge_energy": "battery_discharge_energy",
    "pv_generation_energy": "pv_generation_energy",
    "third_party_pv_generation_energy": "third_party_pv_generation_energy",
    "inverter_generation_energy": "inverter_generation_energy",
    "inverter_consumption_energy": "inverter_consumption_energy",
    "grid_import_energy": "grid_import_energy",
    "grid_export_energy": "grid_export_energy",
}


def _finite_number(value: FH3XValue | None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


class PeriodEnergyTracker:
    """Maintain persisted period baselines for product daily/monthly entities."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, _STORAGE_VERSION, f"{DOMAIN}.periods.{entry_id}")
        self._state: dict[str, Any] | None = None
        self._last_sample: datetime | None = None

    async def async_update(self, values: dict[str, FH3XValue]) -> None:
        """Add period values to the current snapshot and persist baselines."""
        if self._state is None:
            loaded = await self._store.async_load()
            self._state = loaded if isinstance(loaded, dict) else {}

        now = dt_util.now()
        day_id = now.date().isoformat()
        month_id = now.strftime("%Y-%m")
        self._rotate_period("day", day_id)
        self._rotate_period("month", month_id)

        self._update_inverter_consumption(values, now)
        for source, target in _COUNTERS.items():
            current = _finite_number(values.get(source))
            if current is None:
                continue
            current = self._stabilize_counter(source, current)
            for period in ("day", "month"):
                period_state = self._state[period]
                baseline = _finite_number(period_state["baseline"].get(source))
                if baseline is None or current < baseline:
                    period_state["baseline"][source] = current
                    period_state["values"][source] = 0.0
                else:
                    period_state["values"][source] = round(current - baseline, 3)
                prefix = "daily" if period == "day" else "monthly"
                values[f"{prefix}_{target}"] = period_state["values"][source]

        self._last_sample = now
        await self._store.async_save(self._state)

    def _stabilize_counter(self, source: str, current: float) -> float:
        """Reject one-off cumulative counter regressions or huge jumps."""
        assert self._state is not None
        last_values = self._state.get("last_counters")
        reset_candidates = self._state.get("reset_candidates")
        increase_candidates = self._state.get("increase_candidates")
        if not isinstance(last_values, dict):
            last_values = {}
            self._state["last_counters"] = last_values
        if not isinstance(reset_candidates, dict):
            reset_candidates = {}
            self._state["reset_candidates"] = reset_candidates
        if not isinstance(increase_candidates, dict):
            increase_candidates = {}
            self._state["increase_candidates"] = increase_candidates
        previous = _finite_number(last_values.get(source))
        if previous is None:
            last_values[source] = current
            return current

        if current < previous:
            candidate = _finite_number(reset_candidates.get(source))
            if (
                candidate is not None
                and current >= candidate
                and current - candidate <= _MAX_UNCONFIRMED_CHANGE_KWH
            ):
                last_values[source] = current
                reset_candidates.pop(source, None)
                return current
            reset_candidates[source] = current
            return previous

        reset_candidates.pop(source, None)
        if current - previous > _MAX_UNCONFIRMED_CHANGE_KWH:
            candidate = _finite_number(increase_candidates.get(source))
            if (
                candidate is not None
                and current >= candidate
                and current - candidate <= _MAX_UNCONFIRMED_CHANGE_KWH
            ):
                last_values[source] = current
                increase_candidates.pop(source, None)
                return current
            increase_candidates[source] = current
            return previous

        increase_candidates.pop(source, None)
        last_values[source] = current
        return current

    def _rotate_period(self, period: str, identifier: str) -> None:
        assert self._state is not None
        current = self._state.get(period)
        if (
            not isinstance(current, dict)
            or current.get("id") != identifier
            or not isinstance(current.get("baseline"), dict)
            or not isinstance(current.get("values"), dict)
        ):
            self._state[period] = {
                "id": identifier,
                "baseline": {},
                "values": {},
            }

    def _update_inverter_consumption(
        self, values: dict[str, FH3XValue], now: datetime
    ) -> None:
        """Integrate negative PCS AC power with a bounded sample interval."""
        assert self._state is not None
        power = _finite_number(values.get("ac_total_power"))
        if power is None:
            return
        previous_time = self._state.get("last_power_time")
        previous_total = (
            _finite_number(self._state.get("inverter_consumption_total")) or 0
        )
        if previous_time is not None and self._last_sample is not None:
            elapsed = (now - self._last_sample).total_seconds()
            if 0 < elapsed <= _MAX_SAMPLE_GAP_SECONDS and power < 0:
                previous_total += -power * elapsed / 3_600_000
        self._state["last_power_time"] = now.isoformat()
        self._state["inverter_consumption_total"] = round(previous_total, 6)
        values["inverter_consumption_energy"] = round(previous_total, 3)
