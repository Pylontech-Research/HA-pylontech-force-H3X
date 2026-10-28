# Pylontech Force H3X for Home Assistant

[![Validate](https://github.com/Pylontech-Research/HA-pylontech-force-H3X/actions/workflows/validate.yml/badge.svg)](https://github.com/Pylontech-Research/HA-pylontech-force-H3X/actions/workflows/validate.yml)
[![Tests](https://github.com/Pylontech-Research/HA-pylontech-force-H3X/actions/workflows/tests.yml/badge.svg)](https://github.com/Pylontech-Research/HA-pylontech-force-H3X/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A custom Home Assistant integration for local access to Pylontech Force H3X systems over Modbus TCP. No Pylontech cloud account is required.

## What this integration provides

- Set up and manage the integration from the Home Assistant Interface.
- Monitor solar, home-load, grid and battery power, battery SOC, SOH, operating status and current system alert.
- Use supported cumulative energy sensors with the Home Assistant Energy Dashboard and long-term statistics.
- Enable additional PV input, phase, temperature, battery-module and cell readings when supported by the installed system and firmware.
- Download diagnostics with the device IP address and serial number redacted.
- Resume data updates automatically after temporary communication interruptions.

Some readings depend on the installed model, firmware and system configuration.

## Advanced options

### Device Controls

The FH3X operating mode is read-only and can not be changed in Home Assistant.

Writable controls have not yet been validated on real hardware and are not supported for normal use. They should remain disabled until validation has been completed for the installed model, firmware and system configuration.

The optional heat-pump entity provides a start/stop command only. It does not report or confirm the heat-pump's actual operating state.

### Detailed battery diagnostics

Optional module- and cell-level battery readings can be enabled from the integration options. Depending on the installed system and firmware, these may include:

- Module voltage and temperature
- Cell voltage and temperature

These diagnostic readings are read-only and do not change any device settings. Enable them only when detailed battery information is needed. Unsupported readings remain unavailable.

## Before you start

- Connect the Force H3X to a local network that is accessible from Home Assistant.
- Modbus TCP is disabled by default. It must be enabled on the Force H3X by the installer or a user with the required access before adding the integration.
- Home Assistant must be able to reach the Force H3X IP address and its configured Modbus TCP port. The default port is 502.
- A DHCP reservation or static IP address is recommended so the Force H3X address does not change unexpectedly.

The integration has been tested with Home Assistant Green 2026.7.4.

Some optional readings may be unavailable depending on the installed model, firmware and system configuration. This can include detailed PV, phase, battery-module and cell information.

Keep the Modbus TCP connection on a trusted private network. Do not forward its port through your router or expose it directly to the internet because the connection used by this integration is not encrypted and has no login protection.

## Installation

### HACS Installation (recommended)

1. Open HACS and search for Pylontech Force H3X.
2. If the integration is not listed, open the three-dot menu, select Custom repositories, and add `https://github.com/Pylontech-Research/HA-pylontech-force-H3X` as an Integration repository.
3. Open Pylontech Force H3X, select Download, and restart Home Assistant when prompted.
4. Go to Settings → Devices & services → Add integration and select Pylontech Force H3X.

If the system is not discovered automatically, enter its local IP address and configured Modbus TCP port. The default port is 502.

### Manual Installation (optional)

1. Download this repository as a ZIP archive.
2. Copy `custom_components/pylontech_fh3x` to `/config/custom_components/pylontech_fh3x`.
3. Confirm that `/config/custom_components/pylontech_fh3x/manifest.json` exists.
4. Restart Home Assistant.
5. Go to Settings → Devices & services → Add integration and select Pylontech Force H3X.

## Energy Dashboard

Go to Settings → Dashboards → Energy and select the following entities:

- Solar production: Solar Energy
- Grid Consumption: Grid import energy
- Return to grid: Grid export energy
- Battery energy in: Battery charge energy
- Battery energy out: Battery discharge energy
- Battery state of charge (optional): Battery level

Use entities measured in kWh for energy fields. If Home Assistant provides a separate live-power field, use the corresponding W or kW entity only in that field.

Home Assistant calculates home consumption from the configured solar, grid and battery energy flows. Home load energy is therefore not required as an additional Energy Dashboard source.

After completing the configuration, allow time for Home Assistant to collect the first statistics samples.

For live power values:

- Positive Grid power means importing from the grid.
- Negative Grid power means exporting to the grid.
- Positive Battery power means the battery is discharging.
- Negative Battery power means the battery is charging.
- Home load power is calculated from solar, grid and battery power. It may differ slightly from a dedicated load meter.

## Alarms

The device page provides the following alarm entities:

- Inverter fault
- Inverter warning
- BMS protection
- BMS alarm

Open an alarm entity to view the currently reported issues.

BMS protection indicates an active battery protection condition. It is not a setting and does not mean that a protection function has been manually enabled.

A communication interruption does not clear an active alarm. After repeated communication failures, the alarm entities become unavailable until communication is restored.

## Troubleshooting

### Device is unavailable

- Confirm that the FH3X is powered and connected to the local network.
- Confirm that Modbus TCP has been enabled on the FH3X.
- Check that the configured IP address is correct.
- Check the configured Modbus TCP port. The default port is 502.
- If the FH3X IP address has changed, select Reconfigure from the integration menu and enter the new address.

The integration normally reconnects automatically after a temporary network interruption. Reload the integration only if communication does not recover.

### Discovery finds no device

Confirm that Home Assistant and the FH3X can communicate over the same local network.

Guest-network isolation, VLAN rules, Wi-Fi client isolation, or multicast filtering may prevent automatic discovery.

If the device is not discovered, add the integration manually using the FH3X local IP address and configured Modbus TCP port.

### Energy data is missing

- Confirm that the Energy Dashboard uses the kWh entities listed above.
- Confirm that the selected entities are available and reporting numeric values.
- Allow time for Home Assistant to collect the first statistics samples.

Do not replace cumulative energy entities with similarly named instantaneous power entities.

### Energy data changes unexpectedly

First check the current values reported by the integration. Do not edit Home Assistant statistics until the source reading has been confirmed as incorrect.

If the problem continues, download the integration diagnostics and report the issue.

## Compatibility

The integration has been loaded on Home Assistant OS/Green with Home Assistant `2026.7.4`. The minimum Home Assistant version will be added to `hacs.json` only after the compatibility matrix has been completed; an untested minimum version is not declared.

## Privacy and support

Use the structured GitHub issue templates and attach the integration's diagnostics download where useful. Check the file before uploading it. Do not publish passwords, tokens, device serial numbers, public IP addresses, Home Assistant backups, or private packet captures. Security problems must follow [`SECURITY.md`](SECURITY.md).

## Protocol sources

The implementation is based on the manufacturer PCS V1.36 and BMS V1.67 protocol specifications. Those documents are not distributed in this public repository. Obtain authorized copies through the manufacturer, and do not attach restricted protocol documents to issues or pull requests.

## Development checks

```bash
python3 -m compileall -q custom_components tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
```

Repository-wide contribution, testing, protocol-safety and AI-review rules are documented in [`AGENTS.md`](AGENTS.md). Pull requests should retain every section and checkbox from [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

When Ruff is available, also run:

```bash
ruff check custom_components tests scripts
ruff format --check custom_components tests scripts
```

Full Home Assistant config-flow and entity tests require a Home Assistant development environment.

The standalone tests also cover the control-register decoding and signed-value handling. Real-device validation remains required before considering the write path production-proven.

The release procedure and hardware evidence are tracked in [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution requirements.

## License

Released under the MIT License.
