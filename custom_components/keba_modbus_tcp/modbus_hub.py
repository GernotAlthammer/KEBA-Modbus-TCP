"""Modbus TCP communication hub for KEBA P30 charging stations."""
from __future__ import annotations

import asyncio
import logging
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import DEFAULT_WORD_ORDER, MIN_WRITE_INTERVAL, WORD_ORDER_LOW_HIGH

_LOGGER = logging.getLogger(__name__)


class KebaModbusError(Exception):
    """Raised when a Modbus operation towards the KEBA wallbox fails."""


class KebaP30ModbusHub:
    """Thin async wrapper around pymodbus for the KEBA P30 Modbus TCP interface."""

    def __init__(
        self,
        host: str,
        port: int,
        unit_id: int,
        word_order: str = DEFAULT_WORD_ORDER,
    ) -> None:
        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._word_order = word_order
        self._client = AsyncModbusTcpClient(host=host, port=port)
        self._lock = asyncio.Lock()
        self._last_write_monotonic: float | None = None

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the configured port."""
        return self._port

    async def async_connect(self) -> bool:
        """Connect to the wallbox. Returns True if connected."""
        async with self._lock:
            if self._client.connected:
                return True
            await self._client.connect()
            return self._client.connected

    async def async_close(self) -> None:
        """Close the connection to the wallbox."""
        async with self._lock:
            self._client.close()

    async def _ensure_connected(self) -> None:
        if not self._client.connected:
            await self._client.connect()
        if not self._client.connected:
            raise KebaModbusError(
                f"Unable to connect to KEBA P30 at {self._host}:{self._port}"
            )

    async def async_read_uint32(self, address: int) -> int:
        """Read a single KEBA UINT32 value (2 Modbus holding registers)."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._read_holding_registers(address, 2)
            except ModbusException as err:
                raise KebaModbusError(
                    f"Modbus error reading register {address}: {err}"
                ) from err
            except OSError as err:
                raise KebaModbusError(
                    f"Connection error reading register {address} from "
                    f"{self._host}:{self._port}: {err}"
                ) from err

            if result is None or result.isError():
                raise KebaModbusError(
                    f"Error reading register {address} from "
                    f"{self._host}:{self._port}: {result}"
                )

            registers = result.registers
            if len(registers) != 2:
                raise KebaModbusError(
                    f"Unexpected register count ({len(registers)}) for "
                    f"address {address}, expected 2"
                )

            if self._word_order == WORD_ORDER_LOW_HIGH:
                return (registers[1] << 16) | registers[0]
            return (registers[0] << 16) | registers[1]

    async def async_write_uint16(self, address: int, value: int) -> None:
        """Write a single KEBA UINT16 register, respecting the >5s guidance."""
        async with self._lock:
            await self._ensure_connected()
            await self._respect_write_interval()
            try:
                result = await self._write_register(address, value)
            except ModbusException as err:
                raise KebaModbusError(
                    f"Modbus error writing register {address}: {err}"
                ) from err
            except OSError as err:
                raise KebaModbusError(
                    f"Connection error writing register {address} on "
                    f"{self._host}:{self._port}: {err}"
                ) from err

            self._last_write_monotonic = time.monotonic()

            if result is None or result.isError():
                raise KebaModbusError(
                    f"Error writing value {value} to register {address} on "
                    f"{self._host}:{self._port}: {result}"
                )

    async def _read_holding_registers(self, address: int, count: int):
        """Call read_holding_registers, tolerating pymodbus API differences."""
        try:
            return await self._client.read_holding_registers(
                address=address, count=count, slave=self._unit_id
            )
        except TypeError:
            try:
                return await self._client.read_holding_registers(
                    address=address, count=count, unit=self._unit_id
                )
            except TypeError:
                return await self._client.read_holding_registers(
                    address=address, count=count, device_id=self._unit_id
                )

    async def _write_register(self, address: int, value: int):
        """Call write_register, tolerating pymodbus API differences."""
        try:
            return await self._client.write_register(
                address=address, value=value, slave=self._unit_id
            )
        except TypeError:
            try:
                return await self._client.write_register(
                    address=address, value=value, unit=self._unit_id
                )
            except TypeError:
                return await self._client.write_register(
                    address=address, value=value, device_id=self._unit_id
                )

    async def _respect_write_interval(self) -> None:
        """Ensure at least MIN_WRITE_INTERVAL seconds pass between writes."""
        if self._last_write_monotonic is None:
            return
        elapsed = time.monotonic() - self._last_write_monotonic
        remaining = MIN_WRITE_INTERVAL - elapsed
        if remaining > 0:
            _LOGGER.debug(
                "Delaying Modbus write by %.2fs to respect KEBA's recommended "
                "5s minimum interval between write commands",
                remaining,
            )
            await asyncio.sleep(remaining)
