# Changelog

## 0.3.1 - 2026-08-05

- Allowed setup against FH3X firmware or gateways that return an empty PCS
  identity block, using the Modbus endpoint as a stable local fallback identity.
- Kept connection and Modbus response validation in place; only the empty serial
  number check is relaxed.

## 0.3.0 - 2026-08-05

- Expanded PCS monitoring to include AC, EPS, three-phase, backup, meter,
  parallel-system and directional energy-flow data.
- Added extended PCS and BMS device information.
- Expanded BMS aggregate decoding with charge/discharge limits, extrema
  channels, energy totals, module/cell counts, flags, errors, PCB/terminal
  temperatures and insulation state.
- Added optional single-pile, per-module and per-cell BMS polling from the
  `0x1400` detail region, split into Modbus-safe chunks.
- Added full read/write support for all four EMS period definitions: enable,
  start/end, charge/discharge mode, power and individual weekdays.
- Added EPS and peak-shaving controls using PCS protocol V1.36 ranges.
- Added local point coverage matrix and explicitly excluded provisioning,
  account, site, cloud and OTA functions.

## 0.2.0 - 2026-08-05

- Added optional EMS mode, charge/discharge power, SOC, export-limit, heat-pump
  and four schedule-period controls from PCS protocol V1.36.
- Added three compact control-state reads instead of the community project's 23
  fragmented polling operations.
- Added serialized U16, S16 and S32 writes with immediate register readback and
  full coordinator refresh.
- Made every writable entity disabled by default until explicitly enabled by the
  user.
- Added the EMS User-mode safety check for manual charge/discharge power.
- Added English and Simplified Chinese control names and EMS mode states.
- Added protocol tests for signed control values and schedule states.

## 0.1.0 - 2026-08-05

- Replaced the experimental dashboard-card project with an official-style Home Assistant Integration architecture.
- Added UI config flow, reconfiguration and polling options.
- Added a serialized asynchronous Modbus TCP client using BMS device ID 1 and PCS device ID 2.
- Added coordinated PCS and BMS polling with offline recovery.
- Added solar, grid, load, battery, energy, engineering and alarm entities.
- Added diagnostics and English/Simplified Chinese translations.
- Kept the initial release read-only until control registers are verified on real hardware.
