# Pylontech Force H3X for Home Assistant

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

## Manual installation

1. Copy `custom_components/pylontech_fh3x` into Home Assistant's `/config/custom_components/` directory.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **Pylontech Force H3X**.
5. Enter the FH3X IP address and port `502`.

Home Assistant validates the PCS serial number before creating the config entry, so the same device cannot accidentally be configured twice.

## HACS development installation

Until this repository is published and released, add it to HACS as a custom repository with category **Integration**, then download and restart Home Assistant.

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
python3 -m compileall -q custom_components tests
python3 -m unittest discover -s tests -v
```

Repository-wide contribution, testing, protocol-safety and AI-review rules are
documented in [`AGENTS.md`](AGENTS.md). Pull requests should retain every section
and checkbox from [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

When Ruff is available, also run:

```bash
ruff check custom_components tests
ruff format --check custom_components tests
```

Full Home Assistant config-flow and entity tests require a Home Assistant development environment.

The standalone tests also cover the control-register decoding and signed-value
handling. Real-device validation remains required before considering the write
path production-proven.

## License

MIT
