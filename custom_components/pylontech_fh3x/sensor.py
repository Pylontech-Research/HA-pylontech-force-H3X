"""Sensor platform for Pylontech Force H3X."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FH3XConfigEntry
from .const import CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE
from .entity import FH3XCoordinatorEntity
from .profiles import profile_sensor_description
from .protocol import FH3XValue


@dataclass(frozen=True, kw_only=True)
class FH3XSensorEntityDescription(SensorEntityDescription):
    """Describe an FH3X sensor."""

    suggested_display_precision: int | None = None


SENSOR_DESCRIPTIONS: tuple[FH3XSensorEntityDescription, ...] = (
    FH3XSensorEntityDescription(
        key="pv_total_power",
        translation_key="pv_total_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FH3XSensorEntityDescription(
        key="load_power",
        translation_key="load_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FH3XSensorEntityDescription(
        key="grid_power",
        translation_key="grid_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FH3XSensorEntityDescription(
        key="battery_power",
        translation_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FH3XSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FH3XSensorEntityDescription(
        key="inverter_state",
        translation_key="inverter_state",
        device_class=SensorDeviceClass.ENUM,
        options=("waiting", "normal", "fault", "unknown"),
    ),
    FH3XSensorEntityDescription(
        key="battery_state",
        translation_key="battery_state",
        device_class=SensorDeviceClass.ENUM,
        options=(
            "sleeping",
            "charging",
            "discharging",
            "idle",
            "standby",
            "running",
            "fault",
            "offline",
            "unknown",
        ),
    ),
    FH3XSensorEntityDescription(
        key="pv_total_energy",
        translation_key="pv_total_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    FH3XSensorEntityDescription(
        key="grid_import_energy",
        translation_key="grid_import_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    FH3XSensorEntityDescription(
        key="grid_export_energy",
        translation_key="grid_export_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    FH3XSensorEntityDescription(
        key="battery_charge_energy",
        translation_key="battery_charge_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    FH3XSensorEntityDescription(
        key="battery_discharge_energy",
        translation_key="battery_discharge_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    FH3XSensorEntityDescription(
        key="bms_soh",
        translation_key="bms_soh",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FH3XSensorEntityDescription(
        key="bms_cycles",
        translation_key="bms_cycles",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FH3XSensorEntityDescription(
        key="bms_remaining_energy",
        translation_key="bms_remaining_energy",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
)


def _diagnostic_sensor(
    key: str,
    translation_key: str,
    device_class: SensorDeviceClass,
    unit: str,
    precision: int = 1,
) -> FH3XSensorEntityDescription:
    return FH3XSensorEntityDescription(
        key=key,
        translation_key=translation_key,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        suggested_display_precision=precision,
    )


DIAGNOSTIC_SENSOR_DESCRIPTIONS = (
    _diagnostic_sensor(
        "pv1_voltage",
        "pv1_voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "pv1_current",
        "pv1_current",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
    ),
    _diagnostic_sensor(
        "pv1_power", "pv1_power", SensorDeviceClass.POWER, UnitOfPower.WATT, 0
    ),
    _diagnostic_sensor(
        "pv2_voltage",
        "pv2_voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "pv2_current",
        "pv2_current",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
    ),
    _diagnostic_sensor(
        "pv2_power", "pv2_power", SensorDeviceClass.POWER, UnitOfPower.WATT, 0
    ),
    _diagnostic_sensor(
        "pv3_voltage",
        "pv3_voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "pv3_current",
        "pv3_current",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
    ),
    _diagnostic_sensor(
        "pv3_power", "pv3_power", SensorDeviceClass.POWER, UnitOfPower.WATT, 0
    ),
    _diagnostic_sensor(
        "grid_voltage_r",
        "grid_voltage_r",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "grid_voltage_s",
        "grid_voltage_s",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "grid_voltage_t",
        "grid_voltage_t",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "grid_frequency",
        "grid_frequency",
        SensorDeviceClass.FREQUENCY,
        UnitOfFrequency.HERTZ,
        2,
    ),
    _diagnostic_sensor(
        "battery_voltage",
        "battery_voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "battery_current",
        "battery_current",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
    ),
    _diagnostic_sensor(
        "inverter_ambient_temperature",
        "inverter_ambient_temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _diagnostic_sensor(
        "inverter_heatsink_temperature",
        "inverter_heatsink_temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _diagnostic_sensor(
        "bms_total_voltage",
        "bms_total_voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _diagnostic_sensor(
        "bms_current",
        "bms_current",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
        2,
    ),
    _diagnostic_sensor(
        "bms_temperature",
        "bms_temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _diagnostic_sensor(
        "bms_cell_voltage_max",
        "bms_cell_voltage_max",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
        3,
    ),
    _diagnostic_sensor(
        "bms_cell_voltage_min",
        "bms_cell_voltage_min",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
        3,
    ),
    FH3XSensorEntityDescription(
        key="bms_cell_voltage_delta",
        translation_key="bms_cell_voltage_delta",
        native_unit_of_measurement="mV",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    _diagnostic_sensor(
        "bms_cell_temperature_max",
        "bms_cell_temperature_max",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _diagnostic_sensor(
        "bms_cell_temperature_min",
        "bms_cell_temperature_min",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
)


def _engineering_sensor(
    key: str,
    name: str,
    device_class: SensorDeviceClass | None = None,
    unit: str | None = None,
    *,
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
    precision: int | None = None,
) -> FH3XSensorEntityDescription:
    return FH3XSensorEntityDescription(
        key=key,
        name=name,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=state_class,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        suggested_display_precision=precision,
    )


ENGINEERING_SENSOR_DESCRIPTIONS = (
    _engineering_sensor(
        "eps_power", "EPS power", SensorDeviceClass.POWER, UnitOfPower.WATT
    ),
    _engineering_sensor(
        "eps_voltage",
        "EPS voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _engineering_sensor(
        "eps_frequency",
        "EPS frequency",
        SensorDeviceClass.FREQUENCY,
        UnitOfFrequency.HERTZ,
        precision=2,
    ),
    _engineering_sensor(
        "eps_output_energy",
        "EPS output energy",
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=2,
    ),
    _engineering_sensor(
        "battery_charge_energy_from_ac",
        "Battery charge energy from AC",
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=2,
    ),
    _engineering_sensor(
        "bms_charge_energy_today",
        "BMS charge energy today",
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=2,
    ),
    _engineering_sensor(
        "bms_discharge_energy_today",
        "BMS discharge energy today",
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=2,
    ),
    _engineering_sensor(
        "bms_max_charge_voltage",
        "BMS maximum charge voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _engineering_sensor(
        "bms_max_charge_current",
        "BMS maximum charge current",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
        precision=2,
    ),
    _engineering_sensor(
        "bms_min_discharge_voltage",
        "BMS minimum discharge voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    _engineering_sensor(
        "bms_max_discharge_current",
        "BMS maximum discharge current",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
        precision=2,
    ),
    *(
        _engineering_sensor(
            f"grid_current_{phase}",
            f"Grid {phase.upper()} current",
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
        )
        for phase in ("r", "s", "t")
    ),
    *(
        _engineering_sensor(
            f"grid_power_{phase}",
            f"Grid {phase.upper()} power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
        )
        for phase in ("r", "s", "t")
    ),
    *(
        _engineering_sensor(
            f"ct_current_{phase}",
            f"CT {phase.upper()} current",
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
        )
        for phase in ("r", "s", "t")
    ),
    *(
        _engineering_sensor(
            f"backup_voltage_{phase}",
            f"Backup {phase.upper()} voltage",
            SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT,
        )
        for phase in ("r", "s", "t")
    ),
    *(
        _engineering_sensor(
            f"backup_current_{phase}",
            f"Backup {phase.upper()} current",
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
        )
        for phase in ("r", "s", "t")
    ),
    *(
        _engineering_sensor(
            f"backup_power_{phase}",
            f"Backup {phase.upper()} power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
        )
        for phase in ("r", "s", "t")
    ),
    *(
        _engineering_sensor(
            f"ac_output_power_{phase}",
            f"AC output {phase.upper()} power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
        )
        for phase in ("r", "s", "t")
    ),
    _engineering_sensor("bms_module_count", "BMS module count", state_class=None),
    _engineering_sensor("bms_cell_count", "BMS cell count", state_class=None),
    _engineering_sensor(
        "bms_cell_voltage_max_channel", "Maximum cell voltage channel", state_class=None
    ),
    _engineering_sensor(
        "bms_cell_voltage_min_channel", "Minimum cell voltage channel", state_class=None
    ),
    _engineering_sensor(
        "bms_cell_temperature_max_channel",
        "Maximum cell temperature channel",
        state_class=None,
    ),
    _engineering_sensor(
        "bms_cell_temperature_min_channel",
        "Minimum cell temperature channel",
        state_class=None,
    ),
    _engineering_sensor(
        "bms_module_voltage_max",
        "Maximum module voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
        precision=2,
    ),
    _engineering_sensor(
        "bms_module_voltage_min",
        "Minimum module voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
        precision=2,
    ),
    _engineering_sensor(
        "bms_module_temperature_max",
        "Maximum module temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _engineering_sensor(
        "bms_module_temperature_min",
        "Minimum module temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _engineering_sensor(
        "bms_module_pcb_temperature_max",
        "Maximum module PCB temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _engineering_sensor(
        "bms_module_pcb_temperature_min",
        "Minimum module PCB temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _engineering_sensor(
        "bms_terminal_temperature_max",
        "Maximum terminal temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _engineering_sensor(
        "bms_terminal_temperature_min",
        "Minimum terminal temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _engineering_sensor(
        "bms_insulation_resistance", "BMS insulation resistance", unit="kΩ"
    ),
    _engineering_sensor("bms_error_code_1", "BMS error code 1", state_class=None),
    _engineering_sensor("bms_error_code_2", "BMS error code 2", state_class=None),
    _engineering_sensor("fault_bits", "PCS fault bitfield", state_class=None),
    _engineering_sensor("warning_bits", "PCS warning bitfield", state_class=None),
    _engineering_sensor(
        "fault_bits_extended", "PCS extended fault bitfield", state_class=None
    ),
    _engineering_sensor(
        "warning_bits_extended", "PCS extended warning bitfield", state_class=None
    ),
    _engineering_sensor(
        "pcs_max_output_power",
        "PCS maximum output power",
        SensorDeviceClass.POWER,
        UnitOfPower.WATT,
    ),
    _engineering_sensor(
        "pcs_apparent_power_rating", "PCS apparent power rating", unit="VA"
    ),
    _engineering_sensor("pcs_safety_type", "PCS safety type", state_class=None),
    _engineering_sensor("pcs_parallel_mode", "PCS parallel mode", state_class=None),
    _engineering_sensor(
        "pcs_parallel_machine_count", "PCS parallel machine count", state_class=None
    ),
    _engineering_sensor("bms_manufacturer", "BMS manufacturer", state_class=None),
    _engineering_sensor("bms_device_type", "BMS device type", state_class=None),
    _engineering_sensor("bms_product_model", "BMS product model", state_class=None),
    _engineering_sensor("bms_main_version", "BMS main version", state_class=None),
    _engineering_sensor("bms_hmi_version", "BMS HMI version", state_class=None),
    _engineering_sensor(
        "bms_configured_parallel_piles",
        "BMS configured parallel piles",
        state_class=None,
    ),
    _engineering_sensor(
        "bms_local_parallel_address",
        "BMS local parallel address",
        state_class=None,
    ),
    _engineering_sensor(
        "parallel_pv_power",
        "Parallel system PV power",
        SensorDeviceClass.POWER,
        UnitOfPower.WATT,
    ),
    _engineering_sensor(
        "parallel_battery_power",
        "Parallel system battery power",
        SensorDeviceClass.POWER,
        UnitOfPower.WATT,
    ),
    _engineering_sensor(
        "parallel_pcs_rated_power",
        "Parallel system PCS rated power",
        SensorDeviceClass.POWER,
        UnitOfPower.WATT,
    ),
)


SCHEDULE_SENSOR_DESCRIPTIONS = tuple(
    _engineering_sensor(
        f"period_{period}_weekdays",
        f"Schedule period {period} weekdays",
        state_class=None,
    )
    for period in range(1, 5)
)


def _detailed_bms_descriptions(values: Mapping[str, FH3XValue]):
    descriptions = []
    for key in sorted(values):
        if (
            key.startswith("bms_module_")
            and key.endswith("_voltage")
            and key[11:13].isdigit()
        ):
            number = int(key[11:13])
            descriptions.append(
                _engineering_sensor(
                    key,
                    f"BMS module {number} voltage",
                    SensorDeviceClass.VOLTAGE,
                    UnitOfElectricPotential.VOLT,
                    precision=2,
                )
            )
        elif (
            key.startswith("bms_module_")
            and key.endswith("_temperature")
            and key[11:13].isdigit()
        ):
            number = int(key[11:13])
            descriptions.append(
                _engineering_sensor(
                    key,
                    f"BMS module {number} temperature",
                    SensorDeviceClass.TEMPERATURE,
                    UnitOfTemperature.CELSIUS,
                )
            )
        elif (
            key.startswith("bms_cell_")
            and key.endswith("_voltage")
            and key[9:12].isdigit()
        ):
            number = int(key[9:12])
            descriptions.append(
                _engineering_sensor(
                    key,
                    f"BMS cell {number} voltage",
                    SensorDeviceClass.VOLTAGE,
                    UnitOfElectricPotential.VOLT,
                    precision=3,
                )
            )
        elif (
            key.startswith("bms_cell_")
            and key.endswith("_temperature")
            and key[9:12].isdigit()
        ):
            number = int(key[9:12])
            descriptions.append(
                _engineering_sensor(
                    key,
                    f"BMS cell {number} temperature",
                    SensorDeviceClass.TEMPERATURE,
                    UnitOfTemperature.CELSIUS,
                )
            )
    return tuple(descriptions)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FH3XConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FH3X sensors."""
    coordinator = entry.runtime_data.coordinator
    profile = entry.options.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
    descriptions = tuple(
        profile_sensor_description(description, profile)
        for description in (
            SENSOR_DESCRIPTIONS
            + DIAGNOSTIC_SENSOR_DESCRIPTIONS
            + ENGINEERING_SENSOR_DESCRIPTIONS
            + SCHEDULE_SENSOR_DESCRIPTIONS
        )
    )
    async_add_entities(
        FH3XSensor(coordinator, description) for description in descriptions
    )

    known_detail_keys: set[str] = set()

    def _add_new_detail_entities() -> None:
        new_descriptions = tuple(
            profile_sensor_description(description, profile)
            for description in _detailed_bms_descriptions(coordinator.data.values)
            if description.key not in known_detail_keys
        )
        if not new_descriptions:
            return
        known_detail_keys.update(description.key for description in new_descriptions)
        async_add_entities(
            FH3XSensor(coordinator, description) for description in new_descriptions
        )

    _add_new_detail_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_detail_entities))


class FH3XSensor(FH3XCoordinatorEntity, SensorEntity):
    """Representation of one decoded FH3X value."""

    entity_description: FH3XSensorEntityDescription

    def __init__(
        self, coordinator: Any, description: FH3XSensorEntityDescription
    ) -> None:
        """Initialize a sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the latest decoded value."""
        return self.coordinator.data.values.get(self.entity_description.key)
