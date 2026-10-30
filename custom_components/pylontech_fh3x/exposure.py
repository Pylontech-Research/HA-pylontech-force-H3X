"""Pure control-exposure policy for Pylontech Force H3X."""

from __future__ import annotations

CONTROL_PROFILE_DAILY = "read_only"
CONTROL_PROFILE_BASIC = "basic"
CONTROL_PROFILE_ADVANCED = "advanced"

DAILY_CONTROL_KEYS = frozenset(
    {
        "ems_mode",
        "eps_enabled",
        "period_1_enabled",
        "period_2_enabled",
        "period_3_enabled",
        "period_4_enabled",
    }
)

BASIC_CONFIG_KEYS = frozenset(
    {
        "charge_discharge_power_reference",
        "charge_limit_soc",
        "eps_limit_soc_on_grid",
        "eps_limit_soc_off_grid",
        "grid_import_power_limit",
        "meter_export_power_max",
    }
)

ADVANCED_CONTROL_KEYS = frozenset(
    {
        "heat_pump_enabled",
        "peak_shaving_enabled",
    }
)

_SCHEDULE_DAYS = (
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
)

SCHEDULE_CONFIG_KEYS = frozenset(
    key
    for period in range(1, 5)
    for key in (
        f"period_{period}_mode",
        f"period_{period}_power",
        f"period_{period}_start",
        f"period_{period}_end",
        *(f"period_{period}_{day}" for day in _SCHEDULE_DAYS),
    )
)

ADVANCED_CONFIG_KEYS = (
    frozenset(
        {
            "peak_shaving_safety_soc",
            "peak_shaving_meter_power_limit",
        }
    )
    | SCHEDULE_CONFIG_KEYS
)

ALL_WRITABLE_KEYS = (
    DAILY_CONTROL_KEYS
    | BASIC_CONFIG_KEYS
    | ADVANCED_CONTROL_KEYS
    | ADVANCED_CONFIG_KEYS
)


def control_enabled(key: str, profile: str) -> bool:
    """Return whether a writable entity is enabled for an exposure profile."""
    if key in DAILY_CONTROL_KEYS:
        return True
    if key in BASIC_CONFIG_KEYS:
        return profile in {CONTROL_PROFILE_BASIC, CONTROL_PROFILE_ADVANCED}
    return profile == CONTROL_PROFILE_ADVANCED


def is_primary_control(key: str) -> bool:
    """Return whether the entity belongs in Home Assistant's Controls section."""
    return key in DAILY_CONTROL_KEYS or key in ADVANCED_CONTROL_KEYS
