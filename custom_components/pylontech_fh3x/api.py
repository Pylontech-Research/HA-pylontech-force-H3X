"""Asynchronous Modbus TCP client for Pylontech Force H3X."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    BMS_DEVICE_ID,
    DEFAULT_DEVICE_SWITCH_DELAY,
    DEFAULT_READ_RETRIES,
    DEFAULT_READ_RETRY_DELAY,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_TIMEOUT,
    PCS_DEVICE_ID,
)
from .protocol import (
    BMS_CELL_TEMPERATURE_OFFSET,
    BMS_CELL_VOLTAGE_OFFSET,
    BMS_DEVICE_INFO_ADDRESS,
    BMS_DEVICE_INFO_COUNT,
    BMS_LOAD_ENERGY_ADDRESS,
    BMS_LOAD_ENERGY_COUNT,
    BMS_MODULE_TEMPERATURE_OFFSET,
    BMS_MODULE_VOLTAGE_OFFSET,
    BMS_PARALLEL_LOAD_ENERGY_ADDRESS,
    BMS_PILE_ADDRESS,
    BMS_PILE_HEADER_COUNT,
    BMS_SYSTEM_ADDRESS,
    BMS_SYSTEM_COUNT,
    PCS_ACTIVE_POWER_CONTROL_ADDRESS,
    PCS_ACTIVE_POWER_CONTROL_COUNT,
    PCS_DEVICE_INFO_EXT_ADDRESS,
    PCS_DEVICE_INFO_EXT_COUNT,
    PCS_ENERGY_MANAGEMENT_ADDRESS,
    PCS_ENERGY_MANAGEMENT_COUNT,
    PCS_IDENTITY_ADDRESS,
    PCS_IDENTITY_COUNT,
    PCS_INTERNAL_CONTROL_ADDRESS,
    PCS_INTERNAL_CONTROL_COUNT,
    PCS_MONITOR_ADDRESS,
    PCS_MONITOR_COUNT,
    PCS_MONITOR_EXT_ADDRESS,
    PCS_MONITOR_EXT_COUNT,
    PCS_PEAK_SHAVING_ADDRESS,
    PCS_PEAK_SHAVING_COUNT,
    FH3XIdentity,
    FH3XSnapshot,
    FH3XValue,
    TotalIncreasingGuard,
    decode_active_power_controls,
    decode_bms,
    decode_bms_detail_values,
    decode_bms_device_info,
    decode_bms_load_energy,
    decode_bms_pile_header,
    decode_device_info_ext,
    decode_energy_management_controls,
    decode_identity,
    decode_internal_controls,
    decode_pcs,
    decode_pcs_monitor_ext,
    decode_peak_shaving_controls,
    update_u16_bit,
)

_LOGGER = logging.getLogger(__name__)


class FH3XError(Exception):
    """Base FH3X client exception."""


class FH3XConnectionError(FH3XError):
    """Raised when the FH3X cannot be reached."""


class FH3XProtocolError(FH3XError):
    """Raised when the FH3X returns an invalid Modbus response."""


class FH3XModbusClient:
    """Manage one serialized Modbus TCP connection to an FH3X."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        detailed_bms: bool = False,
        request_interval: float = DEFAULT_REQUEST_INTERVAL,
        device_switch_delay: float = DEFAULT_DEVICE_SWITCH_DELAY,
        read_retries: int = DEFAULT_READ_RETRIES,
        read_retry_delay: float = DEFAULT_READ_RETRY_DELAY,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.detailed_bms = detailed_bms
        self.request_interval = request_interval
        self.device_switch_delay = device_switch_delay
        self.read_retries = read_retries
        self.read_retry_delay = read_retry_delay
        self._client = AsyncModbusTcpClient(
            host=host,
            port=port,
            timeout=timeout,
            # A retry on the same socket can consume another response carrying
            # the wrong FH3X unit ID. Reconnect explicitly below instead.
            retries=0,
        )
        self._lock = asyncio.Lock()
        self._identity: FH3XIdentity | None = None
        self._device_values: dict[str, FH3XValue] = {}
        self._device_info_attempted = False
        self._load_energy_values: dict[str, FH3XValue] = {}
        self._load_energy_failures = 0
        self._total_increasing_guard = TotalIncreasingGuard()
        self._last_device_id: int | None = None
        self._last_request_completed_at = 0.0

    def _close_transport(self) -> None:
        """Close the socket and reset request-pacing state."""
        self._client.close()
        self._last_device_id = None
        self._last_request_completed_at = 0.0

    async def _async_pace_request(self, device_id: int) -> None:
        """Give the FH3X gateway time to switch between PCS and BMS units."""
        if self._last_device_id is None:
            return
        required_delay = (
            self.device_switch_delay
            if self._last_device_id != device_id
            else self.request_interval
        )
        elapsed = asyncio.get_running_loop().time() - self._last_request_completed_at
        if (remaining := required_delay - elapsed) > 0:
            await asyncio.sleep(remaining)

    async def _async_ensure_connected(self) -> None:
        if self._client.connected:
            return
        try:
            async with asyncio.timeout(self.timeout):
                connected = await self._client.connect()
        except (TimeoutError, OSError, ModbusException) as err:
            raise FH3XConnectionError(
                f"Unable to connect to FH3X at {self.host}:{self.port}"
            ) from err
        if not connected:
            raise FH3XConnectionError(
                f"Unable to connect to FH3X at {self.host}:{self.port}"
            )

    async def _async_read_registers(
        self,
        address: int,
        count: int,
        device_id: int,
        *,
        allow_input_fallback: bool = True,
    ) -> list[int]:
        async def _read_holding():
            return await self._client.read_holding_registers(
                address,
                count=count,
                device_id=device_id,
            )

        async def _read_input():
            return await self._client.read_input_registers(
                address,
                count=count,
                device_id=device_id,
            )

        response = None
        for attempt in range(self.read_retries + 1):
            await self._async_ensure_connected()
            await self._async_pace_request(device_id)
            try:
                async with asyncio.timeout(self.timeout):
                    response = await _read_holding()
                    if response.isError() and allow_input_fallback:
                        response = await _read_input()
            except (TimeoutError, OSError, ModbusException) as err:
                self._close_transport()
                if attempt < self.read_retries:
                    _LOGGER.warning(
                        "Transient Modbus read failure for device %s, address %s; "
                        "reconnecting and retrying",
                        device_id,
                        address,
                    )
                    await asyncio.sleep(self.read_retry_delay)
                    continue
                raise FH3XConnectionError(
                    f"Error reading device {device_id}, address {address}"
                ) from err
            finally:
                if self._client.connected:
                    self._last_device_id = device_id
                    self._last_request_completed_at = asyncio.get_running_loop().time()
            break

        if response is None:
            raise FH3XConnectionError(
                f"Error reading device {device_id}, address {address}"
            )
        if response.isError():
            raise FH3XProtocolError(
                f"Modbus exception reading device {device_id}, address {address}: "
                f"{response}"
            )
        if not hasattr(response, "registers"):
            self._close_transport()
            raise FH3XProtocolError(
                f"Invalid Modbus response reading device {device_id}, address "
                f"{address}: {response}"
            )
        registers = list(response.registers)
        if len(registers) != count:
            self._close_transport()
            raise FH3XProtocolError(
                f"Short Modbus response from device {device_id}, address {address}: "
                f"received {len(registers)}, expected {count}"
            )
        return registers

    async def _async_read_register_block(
        self,
        address: int,
        count: int,
        device_id: int,
        *,
        chunk_size: int = 120,
    ) -> list[int]:
        """Read a large continuous block using Modbus-safe chunks."""
        registers: list[int] = []
        while len(registers) < count:
            offset = len(registers)
            chunk_count = min(chunk_size, count - offset)
            registers.extend(
                await self._async_read_registers(
                    address + offset,
                    chunk_count,
                    device_id,
                )
            )
        return registers

    async def _async_read_optional_controls(self) -> dict[str, FH3XValue]:
        """Read supported writeable PCS state without breaking core telemetry."""
        values: dict[str, FH3XValue] = {}
        blocks = (
            (
                PCS_ACTIVE_POWER_CONTROL_ADDRESS,
                PCS_ACTIVE_POWER_CONTROL_COUNT,
                decode_active_power_controls,
            ),
            (
                PCS_INTERNAL_CONTROL_ADDRESS,
                PCS_INTERNAL_CONTROL_COUNT,
                decode_internal_controls,
            ),
            (
                PCS_ENERGY_MANAGEMENT_ADDRESS,
                PCS_ENERGY_MANAGEMENT_COUNT,
                decode_energy_management_controls,
            ),
            (
                PCS_PEAK_SHAVING_ADDRESS,
                PCS_PEAK_SHAVING_COUNT,
                decode_peak_shaving_controls,
            ),
        )
        for address, count, decoder in blocks:
            try:
                registers = await self._async_read_registers(
                    address,
                    count,
                    PCS_DEVICE_ID,
                    allow_input_fallback=False,
                )
            except FH3XError as err:
                _LOGGER.debug(
                    "FH3X control block at %s is unavailable: %s", address, err
                )
                continue
            values.update(decoder(registers))
        return values

    async def _async_read_optional_monitor_ext(self) -> dict[str, FH3XValue]:
        """Read newer PCS monitor fields when supported by the firmware."""
        try:
            registers = await self._async_read_registers(
                PCS_MONITOR_EXT_ADDRESS,
                PCS_MONITOR_EXT_COUNT,
                PCS_DEVICE_ID,
            )
        except FH3XError as err:
            _LOGGER.debug("FH3X extended monitor block is unavailable: %s", err)
            return {}
        values = decode_pcs_monitor_ext(registers)
        capacity = values.get("battery_capacity")
        if isinstance(capacity, int | float) and capacity > 0:
            self._device_values["battery_capacity"] = capacity
        else:
            # A zero from an unavailable extended register must not replace a
            # previously confirmed static capacity or become a fake value.
            values.pop("battery_capacity", None)
        return values

    async def _async_read_optional_load_energy(self) -> dict[str, FH3XValue]:
        """Read and stabilize the BMS lifetime home-load energy counter."""
        parallel_count = self._device_values.get("pcs_parallel_machine_count", 1)
        address = (
            BMS_PARALLEL_LOAD_ENERGY_ADDRESS
            if isinstance(parallel_count, int | float) and parallel_count > 1
            else BMS_LOAD_ENERGY_ADDRESS
        )
        try:
            registers = await self._async_read_registers(
                address,
                BMS_LOAD_ENERGY_COUNT,
                BMS_DEVICE_ID,
            )
        except FH3XError as err:
            self._load_energy_failures += 1
            _LOGGER.debug(
                "FH3X BMS load energy at %s is unavailable (%s/3): %s",
                address,
                self._load_energy_failures,
                err,
            )
            if self._load_energy_failures < 3:
                return dict(self._load_energy_values)
            return {}

        values = decode_bms_load_energy(registers)
        self._load_energy_values = values
        self._load_energy_failures = 0
        return dict(values)

    async def _async_read_detailed_bms(
        self, bms_values: dict[str, FH3XValue]
    ) -> dict[str, FH3XValue]:
        """Read optional single-pile, module and cell diagnostics."""
        if not self.detailed_bms:
            return {}
        values: dict[str, FH3XValue] = {}

        async def _optional_block(address: int, count: int) -> list[int]:
            if not count:
                return []
            try:
                return await self._async_read_register_block(
                    address,
                    count,
                    BMS_DEVICE_ID,
                )
            except FH3XError as err:
                _LOGGER.debug(
                    "FH3X detailed BMS block at %s is unavailable: %s",
                    address,
                    err,
                )
                return []

        try:
            header_registers = await self._async_read_registers(
                BMS_PILE_ADDRESS,
                BMS_PILE_HEADER_COUNT,
                BMS_DEVICE_ID,
            )
            values.update(decode_bms_pile_header(header_registers))
            module_count = min(int(bms_values.get("bms_module_count", 0)), 75)
            cell_count = min(int(bms_values.get("bms_cell_count", 0)), 450)

            module_voltages = await _optional_block(
                BMS_PILE_ADDRESS + BMS_MODULE_VOLTAGE_OFFSET,
                module_count,
            )
            module_temperatures = await _optional_block(
                BMS_PILE_ADDRESS + BMS_MODULE_TEMPERATURE_OFFSET,
                module_count,
            )
            cell_voltages = await _optional_block(
                BMS_PILE_ADDRESS + BMS_CELL_VOLTAGE_OFFSET,
                cell_count,
            )
            cell_temperatures = await _optional_block(
                BMS_PILE_ADDRESS + BMS_CELL_TEMPERATURE_OFFSET,
                cell_count,
            )
            values.update(
                decode_bms_detail_values(
                    module_voltages,
                    module_temperatures,
                    cell_voltages,
                    cell_temperatures,
                )
            )
            return values
        except FH3XError as err:
            _LOGGER.warning("Unable to read detailed FH3X BMS data: %s", err)
            return values

    async def _async_write_and_verify(
        self,
        address: int,
        registers: list[int],
        device_id: int,
    ) -> None:
        """Write one or more holding registers and verify the stored value."""
        await self._async_ensure_connected()
        await self._async_pace_request(device_id)
        try:
            async with asyncio.timeout(self.timeout):
                if len(registers) == 1:
                    response = await self._client.write_register(
                        address,
                        registers[0],
                        device_id=device_id,
                    )
                else:
                    response = await self._client.write_registers(
                        address,
                        registers,
                        device_id=device_id,
                    )
        except (TimeoutError, OSError, ModbusException) as err:
            self._close_transport()
            raise FH3XConnectionError(
                f"Error writing device {device_id}, address {address}"
            ) from err
        finally:
            if self._client.connected:
                self._last_device_id = device_id
                self._last_request_completed_at = asyncio.get_running_loop().time()

        if response.isError():
            raise FH3XProtocolError(
                f"Modbus exception writing device {device_id}, address {address}: "
                f"{response}"
            )

        readback = await self._async_read_registers(
            address,
            len(registers),
            device_id,
            allow_input_fallback=False,
        )
        if readback != registers:
            raise FH3XProtocolError(
                f"Write verification failed for device {device_id}, address "
                f"{address}: wrote {registers}, read {readback}"
            )

    async def async_read_identity(self) -> FH3XIdentity:
        """Read and cache the stable PCS identity."""
        async with self._lock:
            await self._async_ensure_connected()
            registers = await self._async_read_registers(
                PCS_IDENTITY_ADDRESS,
                PCS_IDENTITY_COUNT,
                PCS_DEVICE_ID,
            )
            identity = decode_identity(registers)
            if not identity.serial:
                identity = self._identity_with_address_fallback(identity)
            self._identity = identity
            return identity

    def _identity_with_address_fallback(self, identity: FH3XIdentity) -> FH3XIdentity:
        """Create a stable identity when firmware leaves identity registers empty."""
        fallback_serial = f"modbus-{self.host}:{self.port}"
        _LOGGER.warning(
            "FH3X at %s:%s returned an empty PCS serial number; using %s as "
            "the local identity",
            self.host,
            self.port,
            fallback_serial,
        )
        return replace(identity, serial=fallback_serial)

    async def async_read_snapshot(self) -> FH3XSnapshot:
        """Read all current PCS and BMS data in one serialized poll."""
        async with self._lock:
            await self._async_ensure_connected()

            if self._identity is None:
                identity_registers = await self._async_read_registers(
                    PCS_IDENTITY_ADDRESS,
                    PCS_IDENTITY_COUNT,
                    PCS_DEVICE_ID,
                )
                self._identity = decode_identity(identity_registers)
                if not self._identity.serial:
                    self._identity = self._identity_with_address_fallback(
                        self._identity
                    )
            read_device_info = not self._device_info_attempted
            if read_device_info:
                try:
                    device_registers = await self._async_read_registers(
                        PCS_DEVICE_INFO_EXT_ADDRESS,
                        PCS_DEVICE_INFO_EXT_COUNT,
                        PCS_DEVICE_ID,
                    )
                except FH3XError as err:
                    _LOGGER.debug(
                        "FH3X extended device information is unavailable: %s", err
                    )
                else:
                    self._device_values = decode_device_info_ext(device_registers)

            # Keep every normal PCS request together before switching the
            # gateway to BMS unit 1. Older ordering changed unit IDs three
            # times per poll and triggered intermittent cross-unit responses.
            pcs_registers = await self._async_read_registers(
                PCS_MONITOR_ADDRESS,
                PCS_MONITOR_COUNT,
                PCS_DEVICE_ID,
            )
            monitor_ext_values = await self._async_read_optional_monitor_ext()
            control_values = await self._async_read_optional_controls()

            if read_device_info:
                try:
                    bms_device_registers = await self._async_read_registers(
                        BMS_DEVICE_INFO_ADDRESS,
                        BMS_DEVICE_INFO_COUNT,
                        BMS_DEVICE_ID,
                    )
                except FH3XError as err:
                    _LOGGER.debug("FH3X BMS device information is unavailable: %s", err)
                else:
                    self._device_values.update(
                        decode_bms_device_info(bms_device_registers)
                    )
                self._device_info_attempted = True

            bms_registers = await self._async_read_registers(
                BMS_SYSTEM_ADDRESS,
                BMS_SYSTEM_COUNT,
                BMS_DEVICE_ID,
            )
            bms_values = decode_bms(bms_registers)
            load_energy_values = await self._async_read_optional_load_energy()
            detailed_bms_values = await self._async_read_detailed_bms(bms_values)

        values = decode_pcs(pcs_registers)
        values.update(self._device_values)
        values.update(monitor_ext_values)
        values.update(bms_values)
        values.update(load_energy_values)
        values.update(detailed_bms_values)
        values.update(control_values)
        self._total_increasing_guard.apply(values)
        return FH3XSnapshot(
            identity=self._identity,
            values=values,
            pcs_registers=tuple(pcs_registers),
            bms_registers=tuple(bms_registers),
        )

    async def async_write_u16(
        self, address: int, value: int, device_id: int = PCS_DEVICE_ID
    ) -> None:
        """Write and verify an unsigned 16-bit holding register."""
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"U16 value out of range: {value}")
        async with self._lock:
            await self._async_write_and_verify(address, [value], device_id)

    async def async_write_s16(
        self, address: int, value: int, device_id: int = PCS_DEVICE_ID
    ) -> None:
        """Write and verify a signed 16-bit holding register."""
        if not -0x8000 <= value <= 0x7FFF:
            raise ValueError(f"S16 value out of range: {value}")
        async with self._lock:
            await self._async_write_and_verify(address, [value & 0xFFFF], device_id)

    async def async_write_s32(
        self, address: int, value: int, device_id: int = PCS_DEVICE_ID
    ) -> None:
        """Write and verify a signed 32-bit holding register."""
        if not -0x80000000 <= value <= 0x7FFFFFFF:
            raise ValueError(f"S32 value out of range: {value}")
        encoded = value & 0xFFFFFFFF
        registers = [(encoded >> 16) & 0xFFFF, encoded & 0xFFFF]
        async with self._lock:
            await self._async_write_and_verify(address, registers, device_id)

    async def async_update_u16_bit(
        self,
        address: int,
        bit_index: int,
        enabled: bool,
        device_id: int = PCS_DEVICE_ID,
    ) -> None:
        """Read, update and verify one U16 bit without losing concurrent changes."""
        async with self._lock:
            current = (
                await self._async_read_registers(
                    address,
                    1,
                    device_id,
                    allow_input_fallback=False,
                )
            )[0]
            updated = update_u16_bit(current, bit_index, enabled)
            if updated != current:
                await self._async_write_and_verify(address, [updated], device_id)

    async def async_close(self) -> None:
        """Close the underlying connection."""
        async with self._lock:
            self._close_transport()
            _LOGGER.debug("Closed Modbus connection to %s:%s", self.host, self.port)
