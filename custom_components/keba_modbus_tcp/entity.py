"""Base entity classes for the KEBA P30 Modbus TCP integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL


class KebaP30DeviceMixin:
    """Provides shared KEBA P30 device information."""

    _attr_has_entity_name = True

    def _init_device_info(self, entry: ConfigEntry) -> None:
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
        )


class KebaP30Entity(KebaP30DeviceMixin, CoordinatorEntity):
    """Base class for coordinator-backed (read-only) KEBA P30 entities."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._init_device_info(entry)


class KebaP30BaseEntity(KebaP30DeviceMixin, Entity):
    """Base class for standalone (write-only / stateful) KEBA P30 entities."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._init_device_info(entry)
