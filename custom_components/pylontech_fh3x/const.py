"""Constants for the Pylontech Force H3X integration."""

from datetime import timedelta

DOMAIN = "pylontech_fh3x"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_DETAILED_BMS = "detailed_bms"

DEFAULT_NAME = "Pylontech Force H3X"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_TIMEOUT = 5
DEFAULT_DETAILED_BMS = False
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

PCS_DEVICE_ID = 2
BMS_DEVICE_ID = 1

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

MANUFACTURER = "Pylontech"
MODEL = "Force H3X"
