"""The KEBA P30 Modbus TCP integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_FAST_SCAN_INTERVAL,
    CONF_FIRMWARE_REGISTER,
    CONF_SLOW_SCAN_INTERVAL,
    CONF_UNIT_ID,
    CONF_WORD_ORDER,
    DEFAULT_FAST_SCAN_INTERVAL,
    DEFAULT_SLOW_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DEFAULT_WORD_ORDER,
    DOMAIN,
    FIRMWARE_REGISTER_NEW,
)
from .coordinator import KebaP30DynamicCoordinator, KebaP30StaticCoordinator
from .modbus_hub import KebaModbusError, KebaP30ModbusHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KEBA P30 Modbus TCP from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    unit_id = entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)

    fast_interval = entry.options.get(
        CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL
    )
    slow_interval = entry.options.get(
        CONF_SLOW_SCAN_INTERVAL, DEFAULT_SLOW_SCAN_INTERVAL
    )
    firmware_register = entry.options.get(
        CONF_FIRMWARE_REGISTER, FIRMWARE_REGISTER_NEW
    )
    word_order = entry.options.get(CONF_WORD_ORDER, DEFAULT_WORD_ORDER)

    hub = KebaP30ModbusHub(host, port, unit_id, word_order=word_order)

    try:
        connected = await hub.async_connect()
    except KebaModbusError as err:
        raise ConfigEntryNotReady(str(err)) from err

    if not connected:
        raise ConfigEntryNotReady(
            f"Could not connect to KEBA P30 wallbox at {host}:{port}"
        )

    dynamic_coordinator = KebaP30DynamicCoordinator(hass, hub, fast_interval)
    static_coordinator = KebaP30StaticCoordinator(
        hass, hub, slow_interval, firmware_register
    )

    await dynamic_coordinator.async_config_entry_first_refresh()
    await static_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub,
        "dynamic_coordinator": dynamic_coordinator,
        "static_coordinator": static_coordinator,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["hub"].async_close()
    return unload_ok
