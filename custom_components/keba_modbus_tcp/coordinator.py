"""Data update coordinators for the KEBA P30 Modbus TCP integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    REG_ACTIVE_POWER,
    REG_CABLE_STATE,
    REG_CHARGED_ENERGY,
    REG_CHARGING_STATE,
    REG_CURRENT_L1,
    REG_CURRENT_L2,
    REG_CURRENT_L3,
    REG_ERROR_CODE,
    REG_MAX_CHARGING_CURRENT,
    REG_MAX_SUPPORTED_CURRENT,
    REG_POWER_FACTOR,
    REG_PRODUCT_TYPE,
    REG_RFID_TAG,
    REG_SERIAL_NUMBER,
    REG_TOTAL_ENERGY,
    REG_VOLTAGE_L1,
    REG_VOLTAGE_L2,
    REG_VOLTAGE_L3,
)
from .modbus_hub import KebaModbusError, KebaP30ModbusHub

_LOGGER = logging.getLogger(__name__)

# Registers that change often (charging state, currents, power, voltages...)
DYNAMIC_REGISTERS: dict[str, int] = {
    "charging_state": REG_CHARGING_STATE,
    "cable_state": REG_CABLE_STATE,
    "error_code": REG_ERROR_CODE,
    "current_l1": REG_CURRENT_L1,
    "current_l2": REG_CURRENT_L2,
    "current_l3": REG_CURRENT_L3,
    "active_power": REG_ACTIVE_POWER,
    "total_energy": REG_TOTAL_ENERGY,
    "voltage_l1": REG_VOLTAGE_L1,
    "voltage_l2": REG_VOLTAGE_L2,
    "voltage_l3": REG_VOLTAGE_L3,
    "power_factor": REG_POWER_FACTOR,
    "rfid_tag": REG_RFID_TAG,
    "charged_energy": REG_CHARGED_ENERGY,
}


class KebaP30DynamicCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Coordinator polling the frequently changing KEBA P30 registers."""

    def __init__(
        self, hass: HomeAssistant, hub: KebaP30ModbusHub, update_interval: int
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="KEBA P30 dynamic data",
            update_interval=timedelta(seconds=update_interval),
        )
        self.hub = hub

    async def _async_update_data(self) -> dict[str, int]:
        data: dict[str, int] = {}
        try:
            for key, address in DYNAMIC_REGISTERS.items():
                data[key] = await self.hub.async_read_uint32(address)
        except KebaModbusError as err:
            raise UpdateFailed(str(err)) from err
        return data


class KebaP30StaticCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Coordinator polling rarely changing KEBA P30 registers."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub: KebaP30ModbusHub,
        update_interval: int,
        firmware_register: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="KEBA P30 static data",
            update_interval=timedelta(seconds=update_interval),
        )
        self.hub = hub
        self._firmware_register = firmware_register

    async def _async_update_data(self) -> dict[str, int]:
        registers = {
            "serial_number": REG_SERIAL_NUMBER,
            "product_type": REG_PRODUCT_TYPE,
            "firmware_version": self._firmware_register,
            "max_charging_current": REG_MAX_CHARGING_CURRENT,
            "max_supported_current": REG_MAX_SUPPORTED_CURRENT,
        }
        data: dict[str, int] = {}
        try:
            for key, address in registers.items():
                data[key] = await self.hub.async_read_uint32(address)
        except KebaModbusError as err:
            raise UpdateFailed(str(err)) from err
        return data
