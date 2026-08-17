"""Binary sensor platform for the KEBA P30 Modbus TCP integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import KebaP30DynamicCoordinator
from .entity import KebaP30Entity


@dataclass(frozen=True, kw_only=True)
class KebaP30BinarySensorDescription(BinarySensorEntityDescription):
    """Describes a KEBA P30 binary sensor derived from register data."""

    is_on_fn: Callable[[dict[str, int]], bool]


BINARY_SENSORS: tuple[KebaP30BinarySensorDescription, ...] = (
    KebaP30BinarySensorDescription(
        key="vehicle_connected",
        translation_key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        # Cable state 5 = plugged into vehicle (unlocked),
        # 7 = plugged into vehicle and locked (charging).
        is_on_fn=lambda d: d["cable_state"] >= 5,
    ),
    KebaP30BinarySensorDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        is_on_fn=lambda d: d["charging_state"] == 3,
    ),
    KebaP30BinarySensorDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda d: d["charging_state"] == 4 or d["error_code"] != 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up KEBA P30 binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    dynamic_coordinator: KebaP30DynamicCoordinator = data["dynamic_coordinator"]

    async_add_entities(
        KebaP30BinarySensor(dynamic_coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class KebaP30BinarySensor(KebaP30Entity, BinarySensorEntity):
    """Representation of a KEBA P30 binary sensor derived from Modbus data."""

    entity_description: KebaP30BinarySensorDescription

    def __init__(
        self,
        coordinator: KebaP30DynamicCoordinator,
        entry: ConfigEntry,
        description: KebaP30BinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self.coordinator.data)
