from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfElectricCurrent
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KebaSetCurrentNumber(hub, entry.entry_id)])

class KebaSetCurrentNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Max Charging Current"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.MILLIAMPERE
    _attr_native_min_value = 6000
    _attr_native_max_value = 63000
    _attr_native_step = 1000

    def __init__(self, hub, entry_id):
        self._hub = hub
        self._attr_unique_id = f"{entry_id}_set_current"
        self._attr_native_value = 6000 # Default fallback

    async def async_set_native_value(self, value: float) -> None:
        """Setze den maximalen Ladestrom."""
        # Register 5004: Set charging current
        await self._hub.write_uint16_register(5004, int(value))
        self._attr_native_value = value
