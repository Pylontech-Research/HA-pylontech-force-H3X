# Changelog

## 0.6.25 - 2026-08-13

- Complete long-running discovery with `async_show_progress_done` before
  transitioning to device selection or recovery, preventing HA's progress
  state-machine error and blank config-flow screens.

## 0.6.24 - 2026-08-12

- Show a native Home Assistant config-flow progress screen during the
  long-running multi-device discovery window instead of leaving the frontend
  blank while late devices are collected.
- Resume automatically into device selection, confirmation, or recovery after
  the scan task completes.

## 0.6.23 - 2026-08-12

- Extend FH3X discovery to a 15-second total window for slow second devices.
- Keep up to three M-SEARCH attempts while collecting late responses.
- Report duplicate USNs from different IPs and keep the latest address.
- Add recovery and manual-add paths when discovery finds only configured devices.

## 0.6.22 - 2026-08-12

- Use FH3X SSDP USN as the stable discovery and config-flow deduplication key.
- Deduplicate the same device across multicast, broadcast, and DHCP address
  changes, updating an existing entry's host when the IP moves.
- Fall back to the source IP only when a response has no USN.

## 0.6.21 - 2026-08-12

- Do not block SSDP discovery confirmation on a Modbus identity read.
- Use the discovered USN/IP as a temporary setup identity; normal device
  polling continues to read the authoritative PCS identity after setup.
- Keep Modbus validation for manual address entry.

## 0.6.20 - 2026-08-12

- Limit FH3X discovery to three M-SEARCH attempts with a full response window
  between attempts instead of sending once per second.
- Stop sending after a valid FH3X response and keep listening briefly for
  additional devices.
- Add the missing discovery-validation recovery step and retry Modbus identity
  validation once before offering rescan or manual setup.

## 0.6.19 - 2026-08-12

- Repeat FH3X M-SEARCH requests throughout the discovery window so a single
  lost UDP packet does not cause a false discovery failure.
- Bind the broadcast listener to the wildcard address, keeping discovery
  working after Ethernet/Wi-Fi address changes.
- Keep retry socket errors isolated and close all discovery transports safely.

## 0.6.18 - 2026-08-12

- Accept FH3X discovery responses received from another private subnet and
  continue to verify the candidate through its Modbus serial number.
- Use the verified alternate source port `1901` and a multicast hop limit of
  two, avoiding a conflict with Home Assistant's standard SSDP listener.

## 0.6.17 - 2026-08-12

- Discover FH3X devices when the integration is added using the product's
  custom multicast address and UDP broadcast compatibility path.
- Validate every discovered candidate over Modbus TCP before it can be added,
  with multi-device selection and a manual-address fallback.
- Update the saved host when a configured device is rediscovered at a new IP,
  while keeping the Modbus serial number as the authoritative unique ID.

## 0.6.12 - 2026-08-11

- Group PCS and BMS requests to minimize Modbus unit-ID switching, and pace
  consecutive requests for gateways that need a short turnaround interval.
- Reconnect and retry once after transient transport failures or mismatched
  unit-ID responses instead of reusing a contaminated TCP connection.
- Allow slower FH3X responses up to eight seconds, wait for late responses to
  clear before reconnecting, and apply unit-switch pacing to control writes.
- Preserve the last valid snapshot for the first two failed polls and mark the
  device unavailable only after three consecutive failures.
- Add communication resilience state to downloaded diagnostics.

## 0.6.11 - 2026-08-11

- Store the selected English entity label in Home Assistant's supported
  display-name field so the frontend updates immediately. Existing user-set
  names remain untouched.

## 0.6.10 - 2026-08-11

- Deferred the final English entity-name migration until Home Assistant has
  finished persisting platform metadata, preventing system-language defaults
  from overwriting the selected English names during setup.

## 0.6.9 - 2026-08-11

- Standardized FH3X entity names on the integration's English translations,
  including schedule-period placeholders, while preserving user-renamed
  entities, entity IDs, history and automation references.
- Applied the naming policy both before network setup for existing/offline
  devices and after platform setup for newly created entities.

## 0.6.8 - 2026-08-11

- Renamed the Simplified Chinese EPS control to "应急输出 (EPS)" and migrated
  its persisted default name. Together with "工作模式 (EMS)", this keeps EMS
  first under both Chinese and English frontend sorting rules.

## 0.6.7 - 2026-08-11

- Renamed the Simplified Chinese EMS control to "工作模式 (EMS)" so Home
  Assistant's locale-aware device-page sorting keeps it ahead of schedule and
  EPS controls. The entity unique ID and Modbus register remain unchanged.
- Migrated the previously persisted Simplified Chinese default name without
  changing user-renamed entities or names created under other system locales.

## 0.6.6 - 2026-08-11

- Reorganized writable entities using Home Assistant's Controls and
  Configuration sections: EMS, EPS and four schedule enables are daily
  controls; common SOC/manual-power settings remain default configuration.
- Moved complete schedule details, peak shaving, heat-pump and export settings
  behind the advanced control profile, reducing the default Configuration
  section from 52 entities to 4.
- Added period configuration summaries to the four schedule enable switches.
- Changed weekday writes to a locked device read-modify-write operation so
  rapid changes preserve other selected days.
- Kept existing profile values, entity unique IDs and Modbus addresses intact.

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
