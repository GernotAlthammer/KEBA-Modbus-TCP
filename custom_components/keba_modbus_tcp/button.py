"""Button platform for the KEBA P30 Modbus TCP integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, REG_FAILSAFE_PERSIST, REG_UNLOCK_PLUG
from .entity import KebaP30BaseEntity
from .modbus_hub import KebaModbusError, KebaP30ModbusHub

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class KebaP30ButtonDescription(ButtonEntityDescription):
    """Describes a KEBA P30 command exposed as a button entity."""

    register: int
    value: int


BUTTON_DESCRIPTIONS: tuple[KebaP30ButtonDescription, ...] = (
    KebaP30ButtonDescription(
        key="unlock_plug",
        translation_key="unlock_plug",
        icon="mdi:lock-open-variant",
        # Only possible while the charging station is in suspended state,
        # see chapter 4.3 of the KEBA Modbus TCP Programmers Guide.
        register=REG_UNLOCK_PLUG,
        value=0,
    ),
    KebaP30ButtonDescription(
        key="persist_failsafe_settings",
        translation_key="persist_failsafe_settings",
        icon="mdi:content-save-cog-outline",
        entity_category=EntityCategory.CONFIG,
        register=REG_FAILSAFE_PERSIST,
        value=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up KEBA P30 button entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: KebaP30ModbusHub = data["hub"]

    async_add_entities(
        KebaP30Button(entry, hub, description) for description in BUTTON_DESCRIPTIONS
    )


class KebaP30Button(KebaP30BaseEntity, ButtonEntity):
    """A KEBA P30 write-only command exposed as a button entity."""

    entity_description: KebaP30ButtonDescription

    def __init__(
        self,
        entry: ConfigEntry,
        hub: KebaP30ModbusHub,
        description: KebaP30ButtonDescription,
    ) -> None:
        KebaP30BaseEntity.__init__(self, entry)
        self.entity_description = description
        self._hub = hub
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    async def async_press(self) -> None:
        try:
            await self._hub.async_write_uint16(
                self.entity_description.register, self.entity_description.value
            )
        except KebaModbusError as err:
            _LOGGER.error(
                "Failed to press KEBA P30 button '%s': %s",
                self.entity_description.key,
                err,
            )
            raise
