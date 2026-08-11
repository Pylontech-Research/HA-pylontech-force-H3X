"""Asynchronous Modbus TCP client for Pylontech Force H3X."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import BMS_DEVICE_ID, DEFAULT_TIMEOUT, PCS_DEVICE_ID
from .protocol import (
    BMS_CELL_TEMPERATURE_OFFSET,
    BMS_CELL_VOLTAGE_OFFSET,
    BMS_DEVICE_INFO_ADDRESS,
    BMS_DEVICE_INFO_COUNT,
    BMS_MODULE_TEMPERATURE_OFFSET,
    BMS_MODULE_VOLTAGE_OFFSET,
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
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.detailed_bms = detailed_bms
        self._client = AsyncModbusTcpClient(
            host=host,
            port=port,
            timeout=timeout,
            retries=1,
        )
        self._lock = asyncio.Lock()
        self._identity: FH3XIdentity | None = None
        self._device_values: dict[str, FH3XValue] = {}
        self._total_increasing_guard = TotalIncreasingGuard()

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

        try:
            async with asyncio.timeout(self.timeout):
                response = await _read_holding()
                if response.isError() and allow_input_fallback:
                    response = await _read_input()
        except (TimeoutError, OSError, ModbusException) as err:
            self._client.close()
            raise FH3XConnectionError(
                f"Error reading device {device_id}, address {address}"
            ) from err

        if response.isError() or not hasattr(response, "registers"):
            raise FH3XProtocolError(
                f"Modbus exception reading device {device_id}, address {address}: "
                f"{response}"
            )
        registers = list(response.registers)
        if len(registers) != count:
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
        return decode_pcs_monitor_ext(registers)

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
            self._client.close()
            raise FH3XConnectionError(
                f"Error writing device {device_id}, address {address}"
            ) from err

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

            pcs_registers = await self._async_read_registers(
                PCS_MONITOR_ADDRESS,
                PCS_MONITOR_COUNT,
                PCS_DEVICE_ID,
            )
            bms_registers = await self._async_read_registers(
                BMS_SYSTEM_ADDRESS,
                BMS_SYSTEM_COUNT,
                BMS_DEVICE_ID,
            )

            monitor_ext_values = await self._async_read_optional_monitor_ext()
            control_values = await self._async_read_optional_controls()
            bms_values = decode_bms(bms_registers)
            detailed_bms_values = await self._async_read_detailed_bms(bms_values)

        values = decode_pcs(pcs_registers)
        values.update(self._device_values)
        values.update(monitor_ext_values)
        values.update(bms_values)
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
            self._client.close()
            _LOGGER.debug("Closed Modbus connection to %s:%s", self.host, self.port)
