# FH3X local point matrix

This matrix defines the scope of the Home Assistant Integration. It is based on
PCS protocol V1.36 and BMS protocol V1.67. Account, site, provisioning, cloud and
OTA features are intentionally excluded.

## Coverage

| Area | Device ID | Register block | Integration status | Home Assistant exposure |
|---|---:|---:|---|---|
| PCS identity | 2 | 30010–30040 | Implemented | Device registry identity and firmware |
| PCS extended identity | 2 | 30036–30078 | Optional, implemented | Rating, safety type, parallel mode/count, AFCI version |
| PCS live monitor | 2 | 30100–30198 | Implemented | PV, AC, grid, battery, EPS, energy, three-phase and diagnostic values |
| PCS grid substate | 2 | 30160 | Implemented | Grid-connected state; unknown enum values remain unavailable |
| PCS extended monitor | 2 | 30600–30669 | Optional, implemented | Backup/EPS phases, parallel-system totals, meter and flow energy; 30649 provides capacity only when multiple PCS units are reported |
| Active power control | 2 | 40400–40402 | Implemented | Mode readback and export-limit control |
| Internal heat-pump control | 2 | 40848 | Implemented | Advanced Controls switch |
| EMS and four periods | 2 | 40901–40931 | Implemented | EMS/EPS and period enable switches are daily Controls; full period details are Advanced Configuration |
| Peak shaving | 2 | 40973–40975 | Implemented | Advanced Controls switch plus Advanced Configuration limits |
| BMS equipment information | 1 | 0x1000–0x101E | Optional, implemented | BMS type/model/version and parallel information |
| BMS aggregate system | 1 | 0x1100–0x114E | Implemented | SOC/SOH, limits, energy, extrema, channels, flags and alarms |
| BMS lifetime load energy | 1 | 0x1A91–0x1A92 / 0x1AD1–0x1AD2 | Optional, implemented | Single/parallel offsets 0x0691/0x06D1 under the 0x1400 pile base; unavailable after three failed reads |
| BMS single-pile header | 1 | 0x1400–0x145F | Optional, implemented | Pile identity and summary when detailed BMS is enabled |
| BMS nominal capacity | 1 | 0x143A–0x143B | Optional, implemented | Non-PCS-parallel capacity from nominal voltage × Ah × BMS pile count |
| BMS module arrays | 1 | 0x1460+, 0x14B0+ | Optional, implemented | Per-module voltage and temperature, disabled by default |
| BMS cell arrays | 1 | 0x1500+, 0x1800+ | Optional, implemented | Per-cell voltage and temperature, disabled by default |

## Deliberately restricted local registers

These are local Modbus functions but are not exposed as normal Home Assistant
controls because an incorrect command can stop the system, open a relay, erase
statistics or alter grid-compliance parameters:

- BMS sleep/wake, forced charge/discharge and relay commands at `0x1090–0x1095`.
- BMS statistics/SOC recalibration at `0x1096–0x1098`.
- PCS emergency stop, restart, AFCI clear and GLS reset commands.
- Grid protection, safety certification and factory calibration parameters.
- BMS alarm/protection thresholds and factory configuration at `0x1200–0x12FF`.
- File-record and fault-waveform transfer commands.

They can be added later as explicitly named Home Assistant actions with strict
confirmation, capability checks and real-hardware tests. They must not appear as
ordinary switches.

## Excluded non-local product features

- Bluetooth/Wi-Fi provisioning and credentials.
- Pylontech account, site and installer management.
- Cloud-only revenue, tariff, weather and carbon calculations.
- Firmware upload and OTA state machines.
- Cloud storage credentials, server selection and telemetry-upload internals.

## Detailed BMS option

Detailed module/cell polling is off by default. Enable it in the Integration
options only when the aggregate BMS data works reliably. The Integration reads
the module and cell counts first, caps them to the protocol maximum, splits large
reads into Modbus-safe chunks and registers all generated entities as disabled
diagnostics.

Figma-to-protocol parity remains a separate acceptance step. The Figma source
must be exported or made available through the Figma API before every visible App
label can be checked against this matrix.

## Address semantics audit

The address map was re-audited against PCS V1.36 and BMS V1.67 after the load
energy offset correction. The rules are deliberately different between the
protocols:

- PCS tables use absolute decimal register addresses. All implemented identity,
  monitor and control blocks therefore use the numbers printed in the PCS table.
- BMS equipment information (`0x1000` section) and aggregate system information
  (`0x1100` section) also use absolute hexadecimal addresses.
- Every address printed in BMS section 3.6.1 is an offset from the pile base
  `0x1400`. Implemented addresses resolve as follows:

| BMS section 3.6.1 value | Document offset | Actual Modbus address |
|---|---:|---:|
| Single-pile header | `0x0000–0x005F` | `0x1400–0x145F` |
| Nominal voltage and capacity | `0x003A–0x003B` | `0x143A–0x143B` |
| Module voltages | `0x0060–0x00AA` | `0x1460–0x14AA` |
| Module temperatures | `0x00B0–0x00FA` | `0x14B0–0x14FA` |
| Cell voltages | `0x0100–0x02C1` | `0x1500–0x16C1` |
| Cell temperatures | `0x0400–0x05C1` | `0x1800–0x19C1` |
| Single-system load energy | `0x0691–0x0692` | `0x1A91–0x1A92` |
| Parallel-system load energy | `0x06D1–0x06D2` | `0x1AD1–0x1AD2` |

Automated tests pin every implemented block's inclusive end address and every
implemented BMS section 3.6.1 offset. This prevents a future offset from being
mistaken for an absolute address again.
