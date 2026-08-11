"""Binary sensor platform for Pylontech Force H3X."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FH3XConfigEntry
from .entity import FH3XCoordinatorEntity
from .protocol import FH3XValue


@dataclass(frozen=True, kw_only=True)
class FH3XBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe an FH3X problem sensor."""

    is_on_fn: Callable[[Mapping[str, FH3XValue]], bool | None]
    available_fn: Callable[[Mapping[str, FH3XValue]], bool] | None = None
    attributes_fn: Callable[[Mapping[str, FH3XValue]], Mapping[str, Any]] | None = None


PCS_FAULTS = {
    0: "MCU fault",
    1: "Current sensor fault",
    2: "GFCI device fault",
    3: "Relay fault",
    4: "PV voltage high",
    5: "Isolation fault",
    6: "GFCI fault",
    7: "Overtemperature",
    8: "Grid missing",
    9: "Grid overvoltage",
    10: "Grid overfrequency",
    11: "DC injection current high",
    12: "Flash fault",
    13: "Main/voice MCU communication fault",
    14: "Bus voltage high",
    15: "Bus voltage low",
    16: "DRM S9 fault",
    17: "DRM S0 fault",
    18: "PE connection missing",
    19: "Bus voltage imbalance",
    20: "BMS communication failure",
    21: "CT not connected",
    22: "CT reverse connection",
    23: "Battery not connected",
    24: "Backup load overvoltage",
    25: "DC arc fault",
    26: "AFCI self-test fault",
    27: "Parallel address assignment fault",
    28: "Battery precharge circuit fault",
    29: "Battery protection GPIO fault",
    30: "Shutdown circuit fault",
    31: "Battery relay fault",
    32: "Meter communication fault",
    34: "Parallel slave CAN communication loss",
    35: "Parallel slave received master fault",
    36: "Parallel slave synchronization loss",
    39: "Parallel software version mismatch",
    40: "Battery voltage exceeds limit",
    42: "Parallel grid phase-order mismatch",
    43: "EPS voltage exceeds limit",
    44: "Grid phase fault",
}

PCS_WARNINGS = {
    0: "PV1 overcurrent",
    1: "PV2 overcurrent",
    2: "PV3 overcurrent",
    4: "PV1 undervoltage",
    5: "PV2 undervoltage",
    6: "PV3 undervoltage",
    8: "Bus overvoltage",
    9: "Bus undervoltage",
    10: "Inverter overcurrent",
    11: "Anti-islanding protection",
    12: "Grid peak overvoltage",
    13: "Firmware update active",
    14: "PE connection missing",
    15: "Grid voltage consistency warning",
    16: "Fan abnormal",
    17: "Backup load overload",
    18: "SPD failure",
    28: "Battery overcurrent",
    35: "First grid-connection parameters error",
    37: "Bus boost anomaly",
    38: "EPS instantaneous overcurrent",
}

BMS_PROTECTIONS = {
    0: "Cell undervoltage protection",
    1: "Cell overvoltage protection",
    2: "Pile undervoltage protection",
    3: "Pile overvoltage protection",
    4: "Charge low-temperature protection",
    5: "Charge high-temperature protection",
    6: "Discharge low-temperature protection",
    7: "Discharge high-temperature protection",
    8: "Charge overcurrent protection",
    9: "Discharge overcurrent protection",
    10: "Short-circuit protection",
    11: "Terminal temperature protection",
    12: "Module PCB overtemperature protection",
    13: "Module undervoltage protection",
    14: "Module overvoltage protection",
    15: "Secondary cell undervoltage protection",
}

BMS_ALARMS_1 = {
    0: "Cell low-voltage alarm",
    1: "Cell high-voltage alarm",
    2: "Pile low-voltage alarm",
    3: "Pile high-voltage alarm",
    4: "Charge low-temperature alarm",
    5: "Charge high-temperature alarm",
    6: "Discharge low-temperature alarm",
    7: "Discharge high-temperature alarm",
    8: "Charge overcurrent alarm",
    9: "Discharge overcurrent alarm",
    10: "Leakage current alarm",
    11: "BMS overtemperature alarm",
    12: "Module PCB high-temperature alarm",
    13: "Module low-voltage alarm",
    14: "Module high-voltage alarm",
    15: "Terminal temperature alarm",
}

BMS_ALARMS_2 = {
    0: "Cell-voltage imbalance alarm",
    1: "Cell-temperature imbalance alarm",
    2: "BMS communication lost alarm",
    3: "BMS disconnected alarm",
    4: "Abnormal system-use alarm",
    5: "LED communication timeout",
}


def _bit_names(bits: int, names: Mapping[int, str]) -> list[str]:
    return [name for bit, name in names.items() if bits & (1 << bit)]


def _pcs_fault_attributes(data: Mapping[str, FH3XValue]) -> Mapping[str, Any]:
    bits = int(data.get("fault_bits", 0)) | (
        int(data.get("fault_bits_extended", 0)) << 32
    )
    return {
        "active_issues": _bit_names(bits, PCS_FAULTS),
        "fault_code": data.get("fault_code", 0),
    }


def _pcs_warning_attributes(data: Mapping[str, FH3XValue]) -> Mapping[str, Any]:
    bits = int(data.get("warning_bits", 0)) | (
        int(data.get("warning_bits_extended", 0)) << 32
    )
    return {
        "active_issues": _bit_names(bits, PCS_WARNINGS),
        "warning_code": data.get("warning_code", 0),
    }


def _bms_protection_attributes(data: Mapping[str, FH3XValue]) -> Mapping[str, Any]:
    return {
        "active_issues": _bit_names(
            int(data.get("bms_protection_status", 0)), BMS_PROTECTIONS
        ),
        "error_code_1": data.get("bms_error_code_1", 0),
        "error_code_2": data.get("bms_error_code_2", 0),
    }


def _bms_alarm_attributes(data: Mapping[str, FH3XValue]) -> Mapping[str, Any]:
    return {
        "active_issues": _bit_names(
            int(data.get("bms_alarm_status_1", 0)), BMS_ALARMS_1
        )
        + _bit_names(int(data.get("bms_alarm_status_2", 0)), BMS_ALARMS_2)
    }


def _grid_connected(data: Mapping[str, FH3XValue]) -> bool | None:
    mode = data.get("grid_operating_mode")
    if mode == "grid_tied":
        return True
    if mode == "backup":
        return False
    return None


def _grid_connection_attributes(
    data: Mapping[str, FH3XValue],
) -> Mapping[str, Any]:
    return {"operating_mode": data.get("grid_operating_mode", "unknown")}


BINARY_SENSOR_DESCRIPTIONS = (
    FH3XBinarySensorEntityDescription(
        key="grid_connected",
        translation_key="grid_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=_grid_connected,
        available_fn=lambda data: data.get("grid_operating_mode")
        in {"grid_tied", "backup"},
        attributes_fn=_grid_connection_attributes,
    ),
    FH3XBinarySensorEntityDescription(
        key="inverter_fault",
        translation_key="inverter_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(
            data.get("fault_code")
            or data.get("fault_bits")
            or data.get("fault_bits_extended")
        ),
        attributes_fn=_pcs_fault_attributes,
    ),
    FH3XBinarySensorEntityDescription(
        key="inverter_warning",
        translation_key="inverter_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(
            data.get("warning_code")
            or data.get("warning_bits")
            or data.get("warning_bits_extended")
        ),
        attributes_fn=_pcs_warning_attributes,
    ),
    FH3XBinarySensorEntityDescription(
        key="bms_protection",
        translation_key="bms_protection",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(
            data.get("bms_protection_status")
            or data.get("bms_error_code_1")
            or data.get("bms_error_code_2")
        ),
        attributes_fn=_bms_protection_attributes,
    ),
    FH3XBinarySensorEntityDescription(
        key="bms_alarm",
        translation_key="bms_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(
            data.get("bms_alarm_status_1") or data.get("bms_alarm_status_2")
        ),
        attributes_fn=_bms_alarm_attributes,
    ),
    FH3XBinarySensorEntityDescription(
        key="battery_charge_forbidden",
        translation_key="battery_charge_forbidden",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: bool(
            data.get("bms_charge_forbidden") or data.get("charge_forbidden_mask")
        ),
    ),
    FH3XBinarySensorEntityDescription(
        key="battery_discharge_forbidden",
        translation_key="battery_discharge_forbidden",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: bool(
            data.get("bms_discharge_forbidden") or data.get("discharge_forbidden_mask")
        ),
    ),
    FH3XBinarySensorEntityDescription(
        key="battery_force_charge_requested",
        translation_key="battery_force_charge_requested",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: bool(
            data.get("bms_force_charge_requested") or data.get("forced_charge_request")
        ),
    ),
    FH3XBinarySensorEntityDescription(
        key="battery_balance_charge_requested",
        translation_key="battery_balance_charge_requested",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: bool(data.get("bms_balance_charge_requested")),
    ),
    FH3XBinarySensorEntityDescription(
        key="battery_low_soc",
        translation_key="battery_low_soc",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: bool(data.get("bms_low_soc")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FH3X binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        FH3XBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class FH3XBinarySensor(FH3XCoordinatorEntity, BinarySensorEntity):
    """Represent an FH3X fault or warning state."""

    entity_description: FH3XBinarySensorEntityDescription

    def __init__(self, coordinator, description) -> None:
        """Initialize a binary sensor."""
        super().__init__(coordinator, description.key, require_direct_value=False)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return whether the PCS reported a meaningful state."""
        return super().available and (
            self.entity_description.available_fn is None
            or self.entity_description.available_fn(self.coordinator.data.values)
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the problem is active."""
        return self.entity_description.is_on_fn(self.coordinator.data.values)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return decoded active issue names and raw status context."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data.values)
