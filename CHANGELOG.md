# Changelog

## 0.6.0 - 2026-08-07

- Made the compact, read-only entity profile the recommended default.
- Reduced the normal device page to system energy, battery health/state and
  four aggregate PCS/BMS problem entities; detailed flags remain opt-in.
- Reduced the basic control tier to EMS, manual power, SOC and EPS. Schedules,
  peak shaving and engineering controls now require the advanced tier.
- Reapply exposure profiles during setup so existing implicit-default installs
  are cleaned up on upgrade without overriding user-disabled entities.
- Added cumulative-energy regression filtering to prevent a single torn
  Modbus Float32 read from corrupting Home Assistant long-term statistics.

## 0.4.2 - 2026-08-05

- Rebuilt all brand assets from the supplied upright Pylontech master artwork.
- Preserved the original logo aspect ratio and generated square icons with
  transparent side padding instead of stretching the mark.

## 0.4.1 - 2026-08-05

- Added the official Pylontech icon and wordmark as local Home Assistant brand
  assets, including standard and high-density variants.

## 0.4.0 - 2026-08-05

- Added compact, standard and engineering entity-detail profiles.
- Added read-only, basic and advanced control-exposure profiles that also
  update existing entity-registry entries when explicitly selected.
- Promoted useful PV, three-phase grid, battery, BMS and EPS values in the
  standard profile while keeping raw engineering points out of the main view.
- Improved schedule controls with localized native time, switch, enum and
  percentage-slider entities.
- Changed manual and schedule percentage controls to slider mode, added an EMS
  mode interlock, and constrained peak-shaving power from the reported PCS
  rating when available.

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

## 0.4.3

- Serialize control writes and force an immediate verified refresh so rapid
  schedule changes do not show stale values during the coordinator debounce
  window.
