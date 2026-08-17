"""Number platform for the KEBA P30 Modbus TCP integration.

All entities in this platform write to write-only KEBA Modbus registers.
The wallbox does not report back the currently configured value for these
registers, so each entity remembers the last value it sent (persisted
across Home Assistant restarts via RestoreEntity).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    REG_FAILSAFE_CURRENT,
    REG_FAILSAFE_TIMEOUT,
    REG_SET_CHARGING_CURRENT,
    REG_SET_ENERGY,
)
from .entity import KebaP30BaseEntity
from .modbus_hub import KebaModbusError, KebaP30ModbusHub

_LOGGER = logging.getLogger(__name__)


def _to_register_charging_current(value: float) -> int:
    """Set charging current (register 5004), valid range 6000-63000 mA."""
    return int(round(value * 1000))


def _to_register_energy_limit(value: float) -> int:
    """Set energy (register 5010), unit is 10 Wh, value here is kWh."""
    return int(round(value * 100))


def _to_register_failsafe_current(value: float) -> int:
    """Failsafe current (register 5016): 0 (disable) or 6000-32000 mA."""
    if value == 0:
        return 0
    if value < 6:
        _LOGGER.warning(
            "KEBA P30 failsafe current must be 0 or between 6 and 32 A; "
            "clamping %.1f A to 6 A",
            value,
        )
        value = 6
    return int(round(value * 1000))


def _to_register_failsafe_timeout(value: float) -> int:
    """Failsafe timeout (register 5018): 0 (disable) or 10-600 seconds."""
    if value == 0:
        return 0
    if value < 10:
        _LOGGER.warning(
            "KEBA P30 failsafe timeout must be 0 or between 10 and 600s; "
            "clamping %.0f s to 10 s",
            value,
        )
        value = 10
    return int(round(value))


@dataclass(frozen=True, kw_only=True)
class KebaP30NumberDescription(NumberEntityDescription):
    """Describes a KEBA P30 writeable number register."""

    register: int
    to_register: Callable[[float], int]
    default_value: float = 0


NUMBER_DESCRIPTIONS: tuple[KebaP30NumberDescription, ...] = (
    KebaP30NumberDescription(
        key="set_charging_current",
        translation_key="set_charging_current",
        icon="mdi:current-ac",
        register=REG_SET_CHARGING_CURRENT,
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=6,
        native_max_value=63,
        native_step=1,
        mode=NumberMode.SLIDER,
        to_register=_to_register_charging_current,
        default_value=6,
    ),
    KebaP30NumberDescription(
        key="set_energy_limit",
        translation_key="set_energy_limit",
        icon="mdi:battery-charging-100",
        register=REG_SET_ENERGY,
        device_class=NumberDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        native_min_value=0,
        native_max_value=655.35,
        native_step=0.01,
        mode=NumberMode.BOX,
        to_register=_to_register_energy_limit,
        default_value=0,
    ),
    KebaP30NumberDescription(
        key="failsafe_current",
        translation_key="failsafe_current",
        icon="mdi:shield-alert-outline",
        register=REG_FAILSAFE_CURRENT,
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=0,
        native_max_value=32,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        to_register=_to_register_failsafe_current,
        default_value=0,
    ),
    KebaP30NumberDescription(
        key="failsafe_timeout",
        translation_key="failsafe_timeout",
        icon="mdi:timer-alert-outline",
        register=REG_FAILSAFE_TIMEOUT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=0,
        native_max_value=600,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        to_register=_to_register_failsafe_timeout,
        default_value=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up KEBA P30 number entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: KebaP30ModbusHub = data["hub"]

    async_add_entities(
        KebaP30Number(entry, hub, description) for description in NUMBER_DESCRIPTIONS
    )


class KebaP30Number(KebaP30BaseEntity, RestoreEntity, NumberEntity):
    """A writeable KEBA P30 Modbus register exposed as a number entity."""

    entity_description: KebaP30NumberDescription

    def __init__(
        self,
        entry: ConfigEntry,
        hub: KebaP30ModbusHub,
        description: KebaP30NumberDescription,
    ) -> None:
        KebaP30BaseEntity.__init__(self, entry)
        self.entity_description = description
        self._hub = hub
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_native_value = description.default_value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            "unknown",
            "unavailable",
        ):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                _LOGGER.debug(
                    "Could not restore last state for %s: %s",
                    self.entity_id,
                    last_state.state,
                )

    async def async_set_native_value(self, value: float) -> None:
        register_value = self.entity_description.to_register(value)
        try:
            await self._hub.async_write_uint16(
                self.entity_description.register, register_value
            )
        except KebaModbusError as err:
            _LOGGER.error(
                "Failed to write %s to KEBA P30 register %s: %s",
                register_value,
                self.entity_description.register,
                err,
            )
            raise
        self._attr_native_value = value
        self.async_write_ha_state()
