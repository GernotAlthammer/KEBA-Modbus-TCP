import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_HOST

class KebaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KEBA P30."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=f"KEBA P30 ({user_input[CONF_HOST]})", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
