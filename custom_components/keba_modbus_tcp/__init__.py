from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CONF_HOST
from .hub import KebaHub

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KEBA P30 from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    host = entry.data[CONF_HOST]
    hub = KebaHub(hass, host)
    
    await hub.connect()
    hass.data[DOMAIN][entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.disconnect()
    return unload_ok
  
