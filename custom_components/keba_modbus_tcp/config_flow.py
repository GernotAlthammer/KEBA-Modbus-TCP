"""Config flow for the KEBA P30 Modbus TCP integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_FAST_SCAN_INTERVAL,
    CONF_FIRMWARE_REGISTER,
    CONF_SLOW_SCAN_INTERVAL,
    CONF_UNIT_ID,
    CONF_WORD_ORDER,
    DEFAULT_FAST_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SLOW_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DEFAULT_WORD_ORDER,
    DOMAIN,
    FIRMWARE_REGISTER_LEGACY,
    FIRMWARE_REGISTER_NEW,
    REG_SERIAL_NUMBER,
    WORD_ORDER_HIGH_LOW,
    WORD_ORDER_LOW_HIGH,
)
from .modbus_hub import KebaModbusError, KebaP30ModbusHub

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.Coerce(int),
    }
)


class CannotConnect(Exception):
    """Error to indicate we cannot connect to the wallbox."""


async def _async_validate_input(data: dict[str, Any]) -> dict[str, Any]:
    """Validate that we can actually talk to the wallbox and fetch its serial."""
    hub = KebaP30ModbusHub(data[CONF_HOST], data[CONF_PORT], data[CONF_UNIT_ID])
    try:
        if not await hub.async_connect():
            raise CannotConnect("Could not open a Modbus TCP connection")
        serial = await hub.async_read_uint32(REG_SERIAL_NUMBER)
    except KebaModbusError as err:
        raise CannotConnect(str(err)) from err
    finally:
        await hub.async_close()
    return {"serial_number": str(serial)}


class KebaP30ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KEBA P30 Modbus TCP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await _async_validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during KEBA P30 setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: user_input[CONF_HOST]}
                )
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> KebaP30OptionsFlow:
        """Return the options flow for this integration."""
        return KebaP30OptionsFlow(config_entry)


class KebaP30OptionsFlow(config_entries.OptionsFlow):
    """Handle options for KEBA P30 Modbus TCP."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_FAST_SCAN_INTERVAL,
                    default=options.get(
                        CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
                vol.Optional(
                    CONF_SLOW_SCAN_INTERVAL,
                    default=options.get(
                        CONF_SLOW_SCAN_INTERVAL, DEFAULT_SLOW_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
                vol.Optional(
                    CONF_FIRMWARE_REGISTER,
                    default=options.get(
                        CONF_FIRMWARE_REGISTER, FIRMWARE_REGISTER_NEW
                    ),
                ): vol.In(
                    {
                        FIRMWARE_REGISTER_NEW: "1018 (current Modbus TCP spec v1.03)",
                        FIRMWARE_REGISTER_LEGACY: "1013 (x-series, spec v1.11)",
                    }
                ),
                vol.Optional(
                    CONF_WORD_ORDER,
                    default=options.get(CONF_WORD_ORDER, DEFAULT_WORD_ORDER),
                ): vol.In(
                    {
                        WORD_ORDER_HIGH_LOW: "High word first (default)",
                        WORD_ORDER_LOW_HIGH: "Low word first (only if values look wrong)",
                    }
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
