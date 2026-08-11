"""Constants for the Pylontech Force H3X integration."""

from datetime import timedelta

from .exposure import (
    CONTROL_PROFILE_ADVANCED,
    CONTROL_PROFILE_BASIC,
    CONTROL_PROFILE_DAILY,
)

DOMAIN = "pylontech_fh3x"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_DETAILED_BMS = "detailed_bms"
CONF_ENTITY_PROFILE = "entity_profile"
CONF_CONTROL_PROFILE = "control_profile"

ENTITY_PROFILE_COMPACT = "compact"
ENTITY_PROFILE_STANDARD = "standard"
ENTITY_PROFILE_ENGINEERING = "engineering"
ENTITY_PROFILES = (
    ENTITY_PROFILE_COMPACT,
    ENTITY_PROFILE_STANDARD,
    ENTITY_PROFILE_ENGINEERING,
)

CONTROL_PROFILE_READ_ONLY = CONTROL_PROFILE_DAILY
CONTROL_PROFILES = (
    CONTROL_PROFILE_READ_ONLY,
    CONTROL_PROFILE_BASIC,
    CONTROL_PROFILE_ADVANCED,
)

DEFAULT_NAME = "Pylontech Force H3X"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_TIMEOUT = 5
DEFAULT_DETAILED_BMS = False
# Match the default exposure of mature energy integrations: ordinary users get
# the system-level power, energy and health entities.  Per-string, per-phase,
# cell/module and engineering values remain available through the options flow.
DEFAULT_ENTITY_PROFILE = ENTITY_PROFILE_COMPACT
# Daily controls plus four common numeric settings are the recommended balance.
# Complete schedules and engineering controls remain explicitly opt-in.
DEFAULT_CONTROL_PROFILE = CONTROL_PROFILE_BASIC
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

PCS_DEVICE_ID = 2
BMS_DEVICE_ID = 1

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

MANUFACTURER = "Pylontech"
MODEL = "Force H3X"
