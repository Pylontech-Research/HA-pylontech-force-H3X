"""Entity exposure profiles for Pylontech Force H3X."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from .const import (
    CONTROL_PROFILE_ADVANCED,
    CONTROL_PROFILE_BASIC,
    ENTITY_PROFILE_ENGINEERING,
    ENTITY_PROFILE_STANDARD,
    DOMAIN,
)

STANDARD_SENSOR_KEYS = frozenset(
    {
        "pv1_power",
        "pv2_power",
        "pv3_power",
        "grid_voltage_r",
        "grid_voltage_s",
        "grid_voltage_t",
        "grid_frequency",
        "battery_voltage",
        "battery_current",
        "inverter_ambient_temperature",
        "inverter_heatsink_temperature",
        "bms_total_voltage",
        "bms_current",
        "bms_temperature",
        "bms_cycles",
        "bms_cell_voltage_max",
        "bms_cell_voltage_min",
        "bms_cell_voltage_delta",
        "bms_cell_temperature_max",
        "bms_cell_temperature_min",
        "eps_power",
        "bms_charge_energy_today",
        "bms_discharge_energy_today",
    }
)

# Keep vendor-specific counters out of the normal HA device page.  This key was
# briefly promoted in v0.6.0, so handle it explicitly in case its persisted
# registry entry no longer carries the original diagnostic category.
ENGINEERING_SENSOR_KEYS = frozenset({"battery_charge_energy_from_ac"})

# These four entities aggregate the raw PCS/BMS fault bitfields and expose the
# decoded issue list as attributes.  The individual condition flags are useful
# for service engineers, but add little value to a normal HA device page.
CORE_BINARY_SENSOR_KEYS = frozenset(
    {
        "inverter_fault",
        "inverter_warning",
        "bms_protection",
        "bms_alarm",
    }
)

BASIC_CONTROL_KEYS = frozenset(
    {
        "ems_mode",
        "charge_discharge_power_reference",
        "charge_limit_soc",
        "eps_limit_soc_on_grid",
        "eps_limit_soc_off_grid",
        "eps_enabled",
    }
)

ENERGY_CONTROL_KEYS = frozenset(
    {
        "ems_mode",
        "charge_discharge_power_reference",
        "charge_limit_soc",
        "eps_limit_soc_on_grid",
        "eps_limit_soc_off_grid",
        "eps_enabled",
    }
)

CONTROL_DOMAINS = frozenset({"number", "select", "switch", "time"})


def profile_sensor_description(description: Any, profile: str) -> Any:
    """Apply the selected default visibility to a sensor description."""
    promote = description.key in STANDARD_SENSOR_KEYS and profile in {
        ENTITY_PROFILE_STANDARD,
        ENTITY_PROFILE_ENGINEERING,
    }
    enable_all = profile == ENTITY_PROFILE_ENGINEERING
    if not promote and not enable_all:
        return description
    return replace(
        description,
        entity_category=None if promote else description.entity_category,
        entity_registry_enabled_default=True,
    )


def profile_control_description(description: Any, profile: str) -> Any:
    """Enable control descriptions only after the user opts into a control tier."""
    enabled = (
        description.key in ENERGY_CONTROL_KEYS
        or description.key.startswith("period_")
        or profile == CONTROL_PROFILE_ADVANCED
        or (
            profile == CONTROL_PROFILE_BASIC
            and description.key in BASIC_CONTROL_KEYS
        )
    )
    return replace(description, entity_registry_enabled_default=enabled)


def _entity_key(unique_id: str, entry_unique_id: str | None) -> str | None:
    if not entry_unique_id:
        return None
    prefix = f"{entry_unique_id}_"
    return unique_id[len(prefix) :] if unique_id.startswith(prefix) else None


def apply_profiles_to_registry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    entity_profile: str,
    control_profile: str,
) -> None:
    """Apply an explicitly selected profile to existing registry entries."""
    registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entry.platform != DOMAIN:
            continue
        domain = entry.entity_id.split(".", 1)[0]
        key = _entity_key(entry.unique_id, config_entry.unique_id)
        if key is None:
            continue

        if domain == "sensor":
            if key in ENGINEERING_SENSOR_KEYS:
                enabled = entity_profile == ENTITY_PROFILE_ENGINEERING
            else:
                enabled = entity_profile == ENTITY_PROFILE_ENGINEERING or (
                    entity_profile == ENTITY_PROFILE_STANDARD
                    and key in STANDARD_SENSOR_KEYS
                )
            if (
                key not in STANDARD_SENSOR_KEYS
                and key not in ENGINEERING_SENSOR_KEYS
                and entry.entity_category is None
            ):
                continue
        elif domain == "binary_sensor":
            enabled = (
                key in CORE_BINARY_SENSOR_KEYS
                or entity_profile == ENTITY_PROFILE_ENGINEERING
            )
        elif domain in CONTROL_DOMAINS:
            enabled = control_profile == CONTROL_PROFILE_ADVANCED or (
                key in ENERGY_CONTROL_KEYS
                or key.startswith("period_")
                or (
                    control_profile == CONTROL_PROFILE_BASIC
                    and key in BASIC_CONTROL_KEYS
                )
            )
        else:
            continue

        if enabled:
            # Enabling a profile may restore entities disabled by this
            # integration, but must never undo a user's explicit choice.
            if entry.disabled_by == RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(entry.entity_id, disabled_by=None)
        elif entry.disabled_by != RegistryEntryDisabler.USER:
            registry.async_update_entity(
                entry.entity_id,
                disabled_by=RegistryEntryDisabler.INTEGRATION,
            )
