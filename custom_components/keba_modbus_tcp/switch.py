"""Switch platform for the KEBA P30 Modbus TCP integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, REG_ENABLE_STATION
from .entity import KebaP30BaseEntity
from .modbus_hub import KebaModbusError, KebaP30ModbusHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the KEBA P30 charging station enable switch."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: KebaP30ModbusHub = data["hub"]
    async_add_entities([KebaP30EnableSwitch(entry, hub)])


class KebaP30EnableSwitch(KebaP30BaseEntity, RestoreEntity, SwitchEntity):
    """Enable/disable the KEBA P30 charging station (register 5014).

    This register is write-only - the device does not report back whether
    charging is currently enabled or disabled. The switch therefore uses
    'assumed state' and remembers the last commanded value across Home
    Assistant restarts. Turning this off will stop an active charging
    session.
    """

    _attr_translation_key = "charging_station_enabled"
    _attr_assumed_state = True
    _attr_icon = "mdi:ev-station"

    def __init__(self, entry: ConfigEntry, hub: KebaP30ModbusHub) -> None:
        KebaP30BaseEntity.__init__(self, entry)
        self._hub = hub
        self._attr_unique_id = f"{entry.entry_id}_charging_station_enabled"
        self._attr_is_on = True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_write(1)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_write(0)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def _async_write(self, value: int) -> None:
        try:
            await self._hub.async_write_uint16(REG_ENABLE_STATION, value)
        except KebaModbusError as err:
            _LOGGER.error(
                "Failed to set KEBA P30 charging station enable state to %s: %s",
                value,
                err,
            )
            raise
