# Pylontech Force H3X for Home Assistant

[![Validate](https://github.com/pylontech-sw/HA-pylontech-force-H3X/actions/workflows/validate.yml/badge.svg)](https://github.com/pylontech-sw/HA-pylontech-force-H3X/actions/workflows/validate.yml)
[![Tests](https://github.com/pylontech-sw/HA-pylontech-force-H3X/actions/workflows/tests.yml/badge.svg)](https://github.com/pylontech-sw/HA-pylontech-force-H3X/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Local Home Assistant integration for a Pylontech Force H3X residential energy system.

The integration communicates directly with the device over Modbus TCP. It uses one connection and distinguishes the two protocol endpoints by Modbus device ID:

- BMS: device ID `1`
- PCS: device ID `2`
- Default TCP port: `502`

No cloud account is required.

## Current scope

- UI-based setup and reconfiguration.
- One coordinated poll shared by every entity.
- PCS identity, operating state, PV1/PV2/PV3, grid, load and battery values.
- Everyday grid context: connection state, three-phase average voltage/current
  and frequency, plus battery capacity from PCS parallel totals or BMS nominal
  voltage/Ah for a non-parallel PCS.
- BMS SOC, SOH, cycles, temperatures, cell voltage limits and alarms.
- BMS lifetime home-load energy when the installed firmware supports the
  dedicated single/parallel-system counter.
- Energy sensors compatible with Home Assistant long-term statistics.
- Privacy-safe diagnostics download.
- English and Simplified Chinese translations.
- Automatic recovery through Home Assistant's `DataUpdateCoordinator` when the device is temporarily unavailable.
- Optional PCS controls for EMS mode, SOC limits, manual charge/discharge power,
  meter export limit, heat-pump output and four existing schedule periods.
- PCS three-phase, EPS/backup, meter, parallel-system and directional energy
  diagnostics when supported by the device firmware.
- Optional BMS single-pile, per-module and per-cell voltage/temperature data.

The recommended control profile exposes six daily controls and four common
numeric settings. Complete schedules and engineering controls remain opt-in.
Every command is serialized with polling, written to the PCS at device ID `2`,
read back for verification, and followed by a complete coordinator refresh.

The Integration options provide two independent visibility profiles:

- Entity detail: **Recommended**, **Extended monitoring** or **Engineering
  diagnostics**. Recommended is the default and exposes only system-level
  power, cumulative energy, SOC/SOH, operating state and four aggregate alarm
  entities. PV strings, phases, temperatures, cells and raw protocol values are
  opt-in.
- Control exposure: **Daily controls only**, **Daily controls and common
  settings**, or **Advanced controls and full schedules**. The common-settings
  tier is the default. All tiers show EMS, EPS and the four period enable
  switches. The default adds manual power and three SOC limits. Advanced adds
  complete period details, peak shaving, heat-pump and export settings.

Controls use native Home Assistant UI types. Operating modes and enable switches
appear in the device Controls section; numeric thresholds, time pickers and
weekday settings appear under Configuration. Each period enable switch includes
its current mode, power, time range and weekdays as state attributes.

## Controls and safety

The optional controls implement PCS protocol V1.36 registers also exposed by the
community `HA-pylontech-force-H3X` project, but use this integration's current
protocol decoder and connection layer:

- EMS mode: self-consumption, backup, off-grid, feed-in priority, user and PN
  customer modes.
- Charge/discharge power reference: `-100.0%` to `100.0%`. The integration only
  permits changing it while EMS mode is **User**.
- Charge limit SOC: `50%` to `100%`.
- On-grid EPS reserve SOC: `5%` to `100%`.
- Meter export power limit: `-20000 W` to `-1 W`.
- Heat-pump output.
- Schedule periods 1–4: enable, start/end time, charge/discharge mode, power and
  individual weekdays.

Weekday changes use a locked read-modify-write operation against the latest PCS
register value, so rapid changes do not overwrite other selected days.

Do not change a control unless its effect is understood and the range matches
the rated power and operating rules of your installation. Active schedule
periods must not overlap. The first hardware validation should be performed
while the system is supervised.

## Detailed battery diagnostics

Open the Integration options and enable **Detailed module and cell data** to read
the BMS `0x1400` single-pile region. This creates disabled diagnostic entities for
every module and cell reported by the BMS. Leave it disabled until normal PCS and
BMS polling has been validated on the real system.

The implemented and intentionally restricted register blocks are documented in
[`docs/LOCAL_POINT_MATRIX.md`](docs/LOCAL_POINT_MATRIX.md).

## Requirements

1. Home Assistant must be able to reach the FH3X IP address directly.
2. Modbus TCP must be enabled on the FH3X.
3. TCP port `502` must not be blocked between Home Assistant and the device.
4. Give the FH3X a DHCP reservation or static address so its IP does not change unexpectedly.

The battery protocol document lists `192.168.0.16` as the factory external-LAN address. Use the address currently assigned to your own device instead.

Do not expose Modbus TCP port `502` to the internet. Modbus TCP does not provide
transport encryption or authentication and should remain on a trusted local
network.

## Compatibility

The current release candidate has been loaded on Home Assistant OS/Green with
Home Assistant `2026.7.4`. The minimum Home Assistant version will be added to
`hacs.json` only after the compatibility matrix has been completed; an untested
minimum version is not declared.

Firmware capabilities vary. Unsupported extended PCS or BMS register blocks
remain unavailable instead of publishing false zero values. Single-PCS and
parallel-PCS systems use different documented capacity and lifetime-energy
sources.

## HACS installation

Until the repository is accepted into the HACS default catalog:

1. Open HACS.
2. Open **Custom repositories**.
3. Add `https://github.com/pylontech-sw/HA-pylontech-force-H3X` as an
   **Integration** repository.
4. Download **Pylontech Force H3X**.
5. Restart Home Assistant.
6. Open **Settings → Devices & services → Add integration** and select
   **Pylontech Force H3X**.

HACS installs only `custom_components/pylontech_fh3x`. Node.js, a custom
dashboard, and a cloud account are not required.

## Manual installation

1. Copy `custom_components/pylontech_fh3x` into Home Assistant's `/config/custom_components/` directory.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **Pylontech Force H3X**.
5. Enter the FH3X IP address and port `502`.

Manual setup validates the PCS serial number before creating the config entry.
Network discovery uses the FH3X SSDP `USN` to identify and deduplicate devices
without delaying the setup screen with a Modbus identity request.

## Energy Dashboard

Use lifetime `total_increasing` energy entities in **Settings → Dashboards →
Energy**:

- Solar production: **Solar energy**
- Grid consumption: **Grid import energy**
- Return to grid: **Grid export energy**
- Battery energy in: **Battery charge energy**
- Battery energy out: **Battery discharge energy**

Do not select instantaneous power entities measured in watts for an energy
source measured in kWh. **Home load energy** is a lifetime FH3X load counter
when supported by the installed firmware; the Energy Dashboard normally derives
home consumption from the configured solar, grid, and battery flows.

After changing an energy source, allow Home Assistant statistics to collect new
samples. Removing and re-adding an FH3X config entry does not automatically
delete old long-term statistics.

## Alarms and history

The device page exposes current **Inverter fault**, **Inverter warning**, **BMS
protection**, and **BMS alarm** entities. Their attributes contain readable
issues, stable issue IDs, raw status masks, and unknown bit positions.

Trigger, update, and recovery transitions are written to Home Assistant's
Logbook. Open **Logbook** from the Home Assistant sidebar and filter by the FH3X
alarm entity. History retention follows the user's Recorder configuration. A
communication timeout is treated as unknown data, not as alarm recovery.

## Upgrading and rollback

Before upgrading, download a Home Assistant backup and read the release notes.
Upgrade from the FH3X repository page in HACS, restart Home Assistant, and check
the integration and device logs.

To roll back, open the HACS repository menu, choose **Redownload**, select the
previous release, and restart Home Assistant. Config entries and entity unique
IDs are preserved across supported releases. Do not restore a Home Assistant
database solely to change the integration version.

## Troubleshooting

### Device is unavailable

- Verify that Home Assistant can reach the FH3X address and TCP port `502`.
- Confirm PCS device ID `2` and BMS device ID `1` are not changed by a gateway.
- Check that another Modbus client is not monopolizing a single-client gateway.
- Reload the integration after restoring the network; repeated failures become
  unavailable only after the configured resilience threshold.

### Discovery finds no device

FH3X discovery uses multicast `239.101.1.250:1900` from source port `1901` and
the compatibility broadcast path on port `10088`. Wi-Fi isolation, VLAN rules,
or multicast filtering can block it. Use manual IP setup instead of scanning
the entire network for open Modbus ports.

### A control returns to its previous value

The displayed final state comes from Modbus read-back. Check the Home Assistant
error message and device operating mode. In particular, **Charge/discharge
power reference** is writable only while EMS mode is **User**. Do not repeatedly
operate a live grid or battery control to reproduce an error.

### Energy statistics jump

Confirm that kWh energy entities, not W power entities, are configured. Download
diagnostics and inspect the raw lifetime counters before changing statistics.
The integration guards startup baselines and suspicious resets, but existing
incorrect Home Assistant statistics may require correction in Developer Tools.

## Privacy and support

Use the structured GitHub issue templates and attach the integration's
diagnostics download where useful. Check the file before uploading it. Do not
publish passwords, tokens, device serial numbers, public IP addresses, Home
Assistant backups, or private packet captures. Security problems must follow
[`SECURITY.md`](SECURITY.md).

## Power sign conventions

The values follow the FH3X PCS protocol:

- Grid power: positive = importing, negative = exporting.
- Battery power/current: positive = discharging, negative = charging.
- AC total power: positive = output, negative = input.
- Home load is derived as `PV + grid + battery`.

## Protocol sources

- `docs/F3XModbusProtocolV1.36_20260612.docx` — PCS protocol.
- `docs/ModBus-Protocol-Pylon-high-voltage-V1.67-20260721-debug-F3X.docx` — BMS protocol and FH3X device-ID mapping.

## Development checks

```bash
python3 -m compileall -q custom_components tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
```

Repository-wide contribution, testing, protocol-safety and AI-review rules are
documented in [`AGENTS.md`](AGENTS.md). Pull requests should retain every section
and checkbox from [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

When Ruff is available, also run:

```bash
ruff check custom_components tests scripts
ruff format --check custom_components tests scripts
```

Full Home Assistant config-flow and entity tests require a Home Assistant development environment.

The standalone tests also cover the control-register decoding and signed-value
handling. Real-device validation remains required before considering the write
path production-proven.

The release procedure and hardware evidence are tracked in
[`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution requirements.

## License

MIT
