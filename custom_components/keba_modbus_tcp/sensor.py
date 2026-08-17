"""Sensor platform for the KEBA P30 Modbus TCP integration."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import CABLE_STATE_MAP, CHARGING_STATE_MAP, DOMAIN
from .coordinator import KebaP30DynamicCoordinator, KebaP30StaticCoordinator
from .entity import KebaP30Entity
from .util import (
    decode_error_group,
    decode_firmware_version,
    decode_product_type,
    decode_rfid_uid,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class KebaP30SensorDescription(SensorEntityDescription):
    """Describes a KEBA P30 sensor entity."""

    value_fn: Callable[[dict[str, int]], StateType]
    attrs_fn: Callable[[dict[str, int]], dict[str, Any]] | None = None


def _charging_state_value(data: dict[str, int]) -> StateType:
    state = CHARGING_STATE_MAP.get(data["charging_state"])
    if state is None:
        _LOGGER.debug("Unknown KEBA charging state value: %s", data["charging_state"])
    return state


def _cable_state_value(data: dict[str, int]) -> StateType:
    state = CABLE_STATE_MAP.get(data["cable_state"])
    if state is None:
        _LOGGER.debug("Unknown KEBA cable state value: %s", data["cable_state"])
    return state


DYNAMIC_SENSORS: tuple[KebaP30SensorDescription, ...] = (
    KebaP30SensorDescription(
        key="charging_state",
        translation_key="charging_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(CHARGING_STATE_MAP.values()),
        value_fn=_charging_state_value,
    ),
    KebaP30SensorDescription(
        key="cable_state",
        translation_key="cable_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(CABLE_STATE_MAP.values()),
        value_fn=_cable_state_value,
    ),
    KebaP30SensorDescription(
        key="error_code",
        translation_key="error_code",
        value_fn=lambda d: d["error_code"],
        attrs_fn=lambda d: {
            "error_code_hex": f"0x{d['error_code']:X}",
            "error_group": decode_error_group(d["error_code"]),
        },
    ),
    KebaP30SensorDescription(
        key="current_l1",
        translation_key="current_l1",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d["current_l1"] / 1000,
    ),
    KebaP30SensorDescription(
        key="current_l2",
        translation_key="current_l2",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d["current_l2"] / 1000,
    ),
    KebaP30SensorDescription(
        key="current_l3",
        translation_key="current_l3",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d["current_l3"] / 1000,
    ),
    KebaP30SensorDescription(
        key="active_power",
        translation_key="active_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d["active_power"] / 1000,
    ),
    KebaP30SensorDescription(
        key="total_energy",
        translation_key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda d: d["total_energy"] / 1000,
    ),
    KebaP30SensorDescription(
        key="voltage_l1",
        translation_key="voltage_l1",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d["voltage_l1"],
    ),
    KebaP30SensorDescription(
        key="voltage_l2",
        translation_key="voltage_l2",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d["voltage_l2"],
    ),
    KebaP30SensorDescription(
        key="voltage_l3",
        translation_key="voltage_l3",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d["voltage_l3"],
    ),
    KebaP30SensorDescription(
        key="power_factor",
        translation_key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d["power_factor"] / 10,
    ),
    KebaP30SensorDescription(
        key="charged_energy",
        translation_key="charged_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda d: d["charged_energy"] / 1000,
    ),
    KebaP30SensorDescription(
        key="rfid_tag",
        translation_key="rfid_tag",
        icon="mdi:card-account-details",
        entity_registry_enabled_default=False,
        value_fn=lambda d: decode_rfid_uid(d["rfid_tag"]) if d["rfid_tag"] else None,
    ),
)

STATIC_SENSORS: tuple[KebaP30SensorDescription, ...] = (
    KebaP30SensorDescription(
        key="serial_number",
        translation_key="serial_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: str(d["serial_number"]),
    ),
    KebaP30SensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: decode_firmware_version(d["firmware_version"]),
    ),
    KebaP30SensorDescription(
        key="product_type",
        translation_key="product_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: decode_product_type(d["product_type"])["product_type"],
        attrs_fn=lambda d: decode_product_type(d["product_type"]),
    ),
    KebaP30SensorDescription(
        key="max_charging_current",
        translation_key="max_charging_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d["max_charging_current"] / 1000,
    ),
    KebaP30SensorDescription(
        key="max_supported_current",
        translation_key="max_supported_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d["max_supported_current"] / 1000,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up KEBA P30 sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    dynamic_coordinator: KebaP30DynamicCoordinator = data["dynamic_coordinator"]
    static_coordinator: KebaP30StaticCoordinator = data["static_coordinator"]

    entities: list[SensorEntity] = [
        KebaP30Sensor(dynamic_coordinator, entry, description)
        for description in DYNAMIC_SENSORS
    ]
    entities.extend(
        KebaP30Sensor(static_coordinator, entry, description)
        for description in STATIC_SENSORS
    )
    async_add_entities(entities)


class KebaP30Sensor(KebaP30Entity, SensorEntity):
    """Representation of a KEBA P30 Modbus sensor."""

    entity_description: KebaP30SensorDescription

    def __init__(
        self,
        coordinator: KebaP30DynamicCoordinator | KebaP30StaticCoordinator,
        entry: ConfigEntry,
        description: KebaP30SensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
