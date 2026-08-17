"""Constants for the KEBA P30 Modbus TCP integration.

All register addresses and value tables in this file are taken from the
official "KeContact P30 Charging Station Modbus TCP Programmers Guide
V 1.03" published by KEBA AG.
"""
from __future__ import annotations

DOMAIN = "keba_modbus_tcp"

MANUFACTURER = "KEBA"
MODEL = "KeContact P30"

DEFAULT_NAME = "KEBA P30"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 255  # Fixed by the KEBA Modbus TCP specification

# --- Config / options keys -------------------------------------------------

CONF_UNIT_ID = "unit_id"
CONF_FAST_SCAN_INTERVAL = "fast_scan_interval"
CONF_SLOW_SCAN_INTERVAL = "slow_scan_interval"
CONF_FIRMWARE_REGISTER = "firmware_register"
CONF_WORD_ORDER = "word_order"

# KEBA recommends >0.5s for reading registers that change often, and higher
# intervals for registers that rarely change. Writing should happen no more
# often than every >5s "to avoid stressing the charging station".
DEFAULT_FAST_SCAN_INTERVAL = 10  # seconds - dynamic data (state, currents, power, ...)
DEFAULT_SLOW_SCAN_INTERVAL = 300  # seconds - static data (serial, product type, ...)
MIN_WRITE_INTERVAL = 5.0  # seconds, see KEBA guide chapter 2 "Overview"

# The firmware version register moved between Modbus TCP spec revisions:
# - KeContact P30 x-series, Modbus TCP spec v1.11 (older): register 1013
# - Current Modbus TCP Programmers Guide v1.03: register 1018
FIRMWARE_REGISTER_NEW = 1018
FIRMWARE_REGISTER_LEGACY = 1013

# Word order of the 32 bit values returned as two 16 bit Modbus registers.
# The KEBA guide does not explicitly document the word order. "high_low"
# (first register = high word) is the common convention and matches all
# worked examples in the guide. If registers ever read back as
# implausible/huge numbers on your device, switch this in the integration
# options.
WORD_ORDER_HIGH_LOW = "high_low"
WORD_ORDER_LOW_HIGH = "low_high"
DEFAULT_WORD_ORDER = WORD_ORDER_HIGH_LOW

# --- Readable registers (UINT32 = 2 Modbus words each) ---------------------

REG_CHARGING_STATE = 1000
REG_CABLE_STATE = 1004
REG_ERROR_CODE = 1006
REG_CURRENT_L1 = 1008
REG_CURRENT_L2 = 1010
REG_CURRENT_L3 = 1012
REG_SERIAL_NUMBER = 1014
REG_PRODUCT_TYPE = 1016
REG_ACTIVE_POWER = 1020
REG_TOTAL_ENERGY = 1036
REG_VOLTAGE_L1 = 1040
REG_VOLTAGE_L2 = 1042
REG_VOLTAGE_L3 = 1044
REG_POWER_FACTOR = 1046
REG_MAX_CHARGING_CURRENT = 1100
REG_MAX_SUPPORTED_CURRENT = 1110
REG_RFID_TAG = 1500
REG_CHARGED_ENERGY = 1502

# --- Writeable registers (UINT16 = 1 Modbus word each) ----------------------

REG_SET_CHARGING_CURRENT = 5004  # 6000-63000 mA
REG_SET_ENERGY = 5010  # in 10 Wh steps
REG_UNLOCK_PLUG = 5012  # write 0 to unlock
REG_ENABLE_STATION = 5014  # 0 = disable, 1 = enable
REG_FAILSAFE_CURRENT = 5016  # 0 or 6000-32000 mA
REG_FAILSAFE_TIMEOUT = 5018  # 0 or 10-600 s
REG_FAILSAFE_PERSIST = 5020  # write 1 to persist failsafe settings

# --- Value mappings ----------------------------------------------------------

CHARGING_STATE_MAP: dict[int, str] = {
    0: "startup",
    1: "not_ready",
    2: "ready",
    3: "charging",
    4: "error",
    5: "suspended",
}

CABLE_STATE_MAP: dict[int, str] = {
    0: "unplugged",
    1: "plugged_station",
    3: "locked_station",
    5: "plugged_vehicle",
    7: "locked_charging",
}

# "Product type and features" register (1016): the decimal value, read as a
# 6 digit string, encodes 6 separate fields - one digit each.
PRODUCT_TYPE_MAP: dict[int, str] = {3: "KC-P30"}
CABLE_SOCKET_MAP: dict[int, str] = {0: "socket", 1: "cable"}
SUPPORTED_CURRENT_MAP: dict[int, int] = {1: 13, 2: 16, 3: 20, 4: 32}
DEVICE_SERIES_MAP: dict[int, str] = {0: "x-series", 1: "c-series"}
ENERGY_METER_MAP: dict[int, str] = {
    1: "standard_uncalibrated",
    2: "calibratable_mid",
    3: "calibratable_national",
}
AUTHORIZATION_MAP: dict[int, str] = {0: "none", 1: "rfid"}
