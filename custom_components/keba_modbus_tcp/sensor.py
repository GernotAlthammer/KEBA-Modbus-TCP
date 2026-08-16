from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricPotential,
)
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Setze alle Sensoren der KEBA Wallbox auf."""
    hub = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        KebaActivePowerSensor(hub, entry.entry_id),
        KebaTotalEnergySensor(hub, entry.entry_id),
        KebaChargingStateSensor(hub, entry.entry_id),
        KebaVoltageSensor(hub, entry.entry_id, "L1", 1040),
        KebaVoltageSensor(hub, entry.entry_id, "L2", 1042),
        KebaVoltageSensor(hub, entry.entry_id, "L3", 1044),
    ]
    
    async_add_entities(sensors)


class KebaActivePowerSensor(SensorEntity):
    """Sensor für die aktuelle Ladeleistung."""
    _attr_has_entity_name = True
    _attr_name = "Active Power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, hub, entry_id):
        self._hub = hub
        self._attr_unique_id = f"{entry_id}_active_power"

    async def async_update(self):
        # Register 1020: Active Power in mW
        val = await self._hub.read_uint32_register(1020)
        if val is not None:
            # Umrechnung von mW auf W
            self._attr_native_value = round(val / 1000.0, 2)


class KebaTotalEnergySensor(SensorEntity):
    """Sensor für den Gesamtenergieverbrauch."""
    _attr_has_entity_name = True
    _attr_name = "Total Energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, hub, entry_id):
        self._hub = hub
        self._attr_unique_id = f"{entry_id}_total_energy"

    async def async_update(self):
        # Register 1036: Total Energy (Spezifikation liefert oft 0.1 Wh Einheiten)
        val = await self._hub.read_uint32_register(1036)
        if val is not None:
            # Umrechnung von 0.1 Wh auf kWh (Teilung durch 10.000)
            self._attr_native_value = round(val / 10000.0, 2)


class KebaChargingStateSensor(SensorEntity):
    """Sensor für den aktuellen Status der Wallbox."""
    _attr_has_entity_name = True
    _attr_name = "Charging State"
    _attr_icon = "mdi:ev-station"

    def __init__(self, hub, entry_id):
        self._hub = hub
        self._attr_unique_id = f"{entry_id}_charging_state"

    async def async_update(self):
        # Register 1000: Charging State
        val = await self._hub.read_uint32_register(1000)
        if val is not None:
            # Modbus Werte in Klartext mappen
            states = {
                0: "Starting",
                1: "Not ready for charging",
                2: "Ready for charging",
                3: "Charging",
                4: "Error",
                5: "Authorization rejected"
            }
            self._attr_native_value = states.get(val, f"Unknown State ({val})")


class KebaVoltageSensor(SensorEntity):
    """Wiederverwendbarer Sensor für die Spannungen L1, L2, L3."""
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    def __init__(self, hub, entry_id, phase, register):
        self._hub = hub
        self._phase = phase
        self._register = register
        
        self._attr_name = f"Voltage {phase}"
        self._attr_unique_id = f"{entry_id}_voltage_{phase.lower()}"

    async def async_update(self):
        # Register variiert je nach Phase (1040, 1042, 1044)
        val = await self._hub.read_uint32_register(self._register)
        if val is not None:
            self._attr_native_value = val
