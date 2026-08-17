"""Helper functions to decode KEBA P30 Modbus register values."""
from __future__ import annotations

from typing import Any

from .const import (
    AUTHORIZATION_MAP,
    CABLE_SOCKET_MAP,
    DEVICE_SERIES_MAP,
    ENERGY_METER_MAP,
    PRODUCT_TYPE_MAP,
    SUPPORTED_CURRENT_MAP,
)


def decode_firmware_version(raw: int) -> str:
    """Decode the KEBA firmware UINT32 value into a 'major.minor.patch' string.

    Per the KEBA guide: convert the decimal register value to hex and read
    the version from the hex digits, e.g. 50990336 -> hex 0x030A0D00 ->
    major=0x03, minor=0x0A, patch=0x0D -> "3.10.13".

    Note: KEBA's own worked example in the manual states this results in
    "3.10.14" with the annotation "0D=14". That does not match standard hex
    conversion (0x0D is 13, not 14) and looks like a typo in KEBA's guide.
    This implementation uses the mathematically correct conversion.
    """
    major = (raw >> 24) & 0xFF
    minor = (raw >> 16) & 0xFF
    patch = (raw >> 8) & 0xFF
    return f"{major}.{minor}.{patch}"


def decode_product_type(raw: int) -> dict[str, Any]:
    """Decode the "Product type and features" UINT32 register (1016).

    The decimal value, read as a 6 digit string, encodes 6 separate fields,
    one digit each: product type, cable/socket, supported current, device
    series, energy meter type and authorization (RFID).
    """
    digits = str(raw).zfill(6)[-6:]
    product_type_digit = int(digits[0])
    cable_socket_digit = int(digits[1])
    supported_current_digit = int(digits[2])
    device_series_digit = int(digits[3])
    energy_meter_digit = int(digits[4])
    authorization_digit = int(digits[5])

    return {
        "product_type": PRODUCT_TYPE_MAP.get(product_type_digit, "unknown"),
        "cable_or_socket": CABLE_SOCKET_MAP.get(cable_socket_digit, "unknown"),
        "supported_current_a": SUPPORTED_CURRENT_MAP.get(supported_current_digit),
        "device_series": DEVICE_SERIES_MAP.get(device_series_digit, "unknown"),
        "energy_meter": ENERGY_METER_MAP.get(energy_meter_digit, "unknown"),
        "authorization": AUTHORIZATION_MAP.get(authorization_digit, "unknown"),
    }


def decode_error_group(raw: int) -> int | None:
    """Return the error group (upper 16 bit word) of the KEBA error code.

    Example from the KEBA guide: decimal 262144 -> hex 0x40000 -> group 4.
    """
    if raw == 0:
        return None
    return raw >> 16


def decode_rfid_uid(raw: int) -> str:
    """Return the RFID UID (first 4 bytes) as an uppercase hex string."""
    return f"{raw:08X}"
