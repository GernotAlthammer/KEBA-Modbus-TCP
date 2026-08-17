# KEBA P30 Modbus TCP – Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/GernotAlthammer/KEBA-Modbus-TCP/actions/workflows/validate.yml/badge.svg)](https://github.com/GernotAlthammer/KEBA-Modbus-TCP/actions/workflows/validate.yml)

A [HACS](https://hacs.xyz/) custom integration for Home Assistant that talks
to a **KEBA KeContact P30** (x-series and c-series) EV charging station over
its **Modbus TCP** interface. It reads all documented registers and exposes
sensors, binary sensors, a switch, numbers and buttons so the wallbox can be
fully monitored and controlled (e.g. by an energy manager, PV surplus
charging automation, or the KEBA failsafe function).

> **Unofficial community project.** This integration is not developed,
> endorsed, or supported by KEBA AG. It is based on the publicly available
> *"KeContact P30 Charging Station Modbus TCP Programmers Guide V 1.03"*.
> Use at your own risk – always keep an eye on your installation, especially
> when automating charging current or enabling/disabling the station.

## Features

- Config flow (UI setup, no YAML needed)
- Two independent polling intervals, as recommended by KEBA: a fast one for
  frequently changing data (charging state, currents, power, voltages, ...)
  and a slow one for static data (serial number, product type, firmware,
  max. current)
- Automatic pacing of write commands to respect KEBA's recommended minimum
  interval of 5 seconds between writes
- Sensors, binary sensors, numbers, a switch and buttons for everything the
  Modbus TCP interface exposes
- Failsafe configuration (current, timeout, persist) for a safe fallback if
  your Home Assistant/network connection drops
- Configurable word order and firmware register address, in case your
  device/firmware behaves differently than assumed (see
  [Known limitations](#known-limitations--troubleshooting))

## Requirements

- **KeContact P30 c-series** with firmware **3.10.16** or higher, **or**
  **KeContact P30 x-series** with software **1.11** or higher
- Modbus TCP enabled on the wallbox, and **not** used together with the UDP
  interface at the same time
- The wallbox reachable via LAN/IP from your Home Assistant instance
  (TCP port 502)
- Home Assistant with [HACS](https://hacs.xyz/) installed

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the three-dot menu (top right) → **Custom repositories**.
3. Add `https://github.com/GernotAlthammer/KEBA-Modbus-TCP` with category
   **Integration**.
4. Find **KEBA P30 Modbus TCP** in HACS and install it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** and search for
   **KEBA P30 Modbus TCP**.

### Manual installation

1. Copy `custom_components/keba_modbus_tcp` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for
   **KEBA P30 Modbus TCP**.

## Configuration

All configuration is done through the UI:

| Field | Description | Default |
|---|---|---|
| Name | Friendly name for the device | KEBA P30 |
| IP address / hostname | Address of the wallbox | – |
| Port | Modbus TCP port | 502 |
| Unit ID | Modbus slave/unit ID | 255 (fixed by KEBA spec) |

After setup, you can fine-tune behaviour under **Configure** on the
integration:

| Option | Description | Default |
|---|---|---|
| Fast update interval | Poll interval for dynamic data (seconds) | 10 |
| Slow update interval | Poll interval for static data (seconds) | 300 |
| Firmware version register | `1018` (current spec) or `1013` (older x-series spec v1.11) | 1018 |
| Word order | `high_low` (default) or `low_high` – only change if values look wrong | high_low |

## Entities

### Sensors

| Entity | KEBA register | Unit |
|---|---|---|
| Charging state | 1000 | enum: starting up / not ready / ready / charging / error / suspended |
| Cable state | 1004 | enum |
| Error code | 1006 | – (hex + error group as attributes) |
| Current phase 1/2/3 | 1008/1010/1012 | A |
| Active power | 1020 | W |
| Total energy | 1036 | kWh |
| Voltage phase 1/2/3 *(disabled by default)* | 1040/1042/1044 | V |
| Power factor *(disabled by default)* | 1046 | % |
| Charged energy (session) | 1502 | kWh |
| RFID tag UID *(disabled by default)* | 1500 | – |
| Serial number | 1014 | – |
| Firmware version | 1018 / 1013 | – |
| Product type (+ decoded attributes) | 1016 | – |
| Max charging current | 1100 | A |
| Max supported current (hardware) | 1110 | A |

### Binary sensors

- **Vehicle connected** – derived from cable state
- **Charging** – derived from charging state
- **Problem** – derived from charging state / error code

### Number entities (write-only registers)

| Entity | KEBA register | Range |
|---|---|---|
| Charging current limit | 5004 | 6–63 A |
| Energy limit (current session) | 5010 | 0–655.35 kWh, 0.01 kWh steps |
| Failsafe current | 5016 | 0 or 6–32 A |
| Failsafe timeout | 5018 | 0 or 10–600 s |

### Switch

- **Charging station enabled** (register 5014). This register cannot be
  read back from the device, so the switch uses an *assumed state* that is
  remembered across restarts.

### Buttons

- **Unlock plug** (register 5012) – only works while the station is in a
  suspended state, and only after any active charging session has been
  stopped.
- **Persist failsafe settings** (register 5020)

## About the KEBA failsafe function

The failsafe function defines a fallback behaviour in case the connection
between Home Assistant and the wallbox is interrupted:

- Setting **only** the failsafe current does **not** activate failsafe
  charging.
- Failsafe charging is activated by sending a **failsafe timeout** value
  greater than 0.
- To make the failsafe settings survive a wallbox reboot, press
  **Persist failsafe settings** after configuring current and timeout.
- To deactivate failsafe again, set the timeout back to `0` (and, if it was
  persisted, press "Persist failsafe settings" again while timeout is `0`).

## Known limitations / troubleshooting

- **Word order of 32 bit values:** the KEBA guide does not explicitly state
  the byte/word order of the UINT32 values returned across two Modbus
  registers. This integration defaults to "high word first", which matches
  every worked example in the official guide. If sensor values look wildly
  implausible on your device/gateway, try switching **Word order** to
  `low_high` in the integration options.
- **Register addressing:** the KEBA guide notes that "depending on the used
  implementation, +1 might have to be added" to the documented register
  numbers. This integration passes the register numbers from the guide
  (e.g. 1000, 5004, ...) directly to `pymodbus`, which uses zero-based
  addressing on the wire — this matches all worked examples in the guide.
  If you are bridging through another Modbus gateway/tool that expects
  one-based addressing, adjust there rather than in this integration.
- **Error codes:** the guide only documents how to derive the *error group*
  (upper 16 bit word) from the error code, using one example (group 4). The
  full list of KEBA error codes/groups is not publicly documented, so this
  integration only exposes the raw code, its hex representation and the
  derived group number as attributes on the "Error code" sensor.
- **Firmware version example in the KEBA guide:** the official example
  converts `50990336` to hex `30A0D00` and states this means version
  `3.10.14` (annotated "0D=14"). Mathematically, `0x0D` is `13`, not `14` –
  this looks like a typo in KEBA's manual. This integration performs the
  standard hex conversion and would report `3.10.13` for that example.
- Built strictly from the register map described in the official Modbus TCP
  Programmers Guide V1.03; it has **not** been verified against real KEBA
  P30 hardware by the integration's author in this initial release. Please
  [open an issue](https://github.com/GernotAlthammer/KEBA-Modbus-TCP/issues)
  if you run into problems on real hardware.

## Contributing

Issues and pull requests are welcome at
[github.com/GernotAlthammer/KEBA-Modbus-TCP](https://github.com/GernotAlthammer/KEBA-Modbus-TCP).

## Credits

Register map, value ranges and behaviour are based on KEBA AG's official
*"KeContact P30 Charging Station Modbus TCP Programmers Guide V 1.03"*.
KEBA, KeContact and P30 are trademarks of KEBA AG.

## License

[MIT](LICENSE)
