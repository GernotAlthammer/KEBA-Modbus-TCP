from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KebaEnableSwitch(hub, entry.entry_id)])

class KebaEnableSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Enable Charging Station"

    def __init__(self, hub, entry_id):
        self._hub = hub
        self._attr_unique_id = f"{entry_id}_enable"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs):
        """Aktiviert die Ladestation."""
        # Register 5014: Enable/Disable (1 = Enable)
        await self._hub.write_uint16_register(5014, 1)
        self._attr_is_on = True

    async def async_turn_off(self, **kwargs):
        """Deaktiviert die Ladestation."""
        # Register 5014: Enable/Disable (0 = Disable)
        await self._hub.write_uint16_register(5014, 0)
        self._attr_is_on = False
