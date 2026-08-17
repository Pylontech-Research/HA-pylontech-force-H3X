# Release checklist

Complete this checklist for every public HACS release. Store test evidence in
the release notes or linked pull request; do not commit credentials, backups,
private addresses, or unredacted serial numbers.

## Version and source

- [ ] `manifest.json`, `CHANGELOG.md`, Git tag, and GitHub Release use the same version.
- [ ] The working tree is clean and the release commit is on `main`.
- [ ] HACS Action, Hassfest, Tests, and repository validation pass without ignored checks.
- [ ] Local brand assets pass current Home Assistant requirements; if the HACS
      default-catalog validator still requires `home-assistant/brands`, its PR is merged.
- [ ] No restricted protocol documents are distributed, and all included brand
      assets have confirmed public redistribution rights.
- [ ] No cache, database, log, packet capture, credential, or generated browser artifact is tracked.

## Compatibility

- [ ] Current Home Assistant Stable is tested.
- [ ] The previous supported Home Assistant release is tested.
- [ ] The oldest declared Home Assistant version is tested.
- [ ] The resulting minimum version is recorded in `hacs.json` and README.
- [ ] The required `pymodbus` version installs on every supported Home Assistant Python runtime.

Record:

```text
Home Assistant versions:
Python versions:
HACS version:
Installation type:
```

## Automated tests

- [ ] Python compilation passes.
- [ ] Unit and regression tests pass.
- [ ] Ruff lint and format checks pass.
- [ ] Manual setup success and failure paths pass.
- [ ] Single-device, multi-device, slow-response, duplicate-USN, and no-response discovery paths pass.
- [ ] Setup failure closes the Modbus client.
- [ ] Config-entry reload and unload close transports.
- [ ] Diagnostics redact host and serial values.
- [ ] Translation keys remain synchronized.

## Green and HACS installation

- [ ] A clean HACS custom-repository installation succeeds.
- [ ] Home Assistant restarts and loads the integration without errors.
- [ ] An existing manual installation upgrades through HACS without losing entity IDs.
- [ ] Reload, uninstall, reinstall, and rollback are tested.
- [ ] Automatic discovery and manual IP setup are tested.
- [ ] Device IP address changes and multiple devices are tested where available.
- [ ] The system runs for at least 24 hours without recurring unavailability or connection leaks.

## Energy and alarms

- [ ] Solar, grid import/export, and battery charge/discharge statistics remain monotonic.
- [ ] Startup and integration reload do not create lifetime-energy jumps.
- [ ] Energy Dashboard mappings use kWh entities rather than W entities.
- [ ] Alarm trigger, changed bitmask, recovery, unknown bit, restart, and communication-loss behavior pass.
- [ ] Logbook and live alarm attributes agree.

## Writable controls

- [ ] The real FH3X model, topology, PCS firmware, and BMS firmware are recorded.
- [ ] EMS, EPS, SOC limits, and schedule periods are read back successfully.
- [ ] Rapid schedule changes preserve the final device state.
- [ ] Weekday bitmask updates do not erase other weekdays.
- [ ] Unsupported registers remain unavailable instead of publishing zero or off.
- [ ] No unverified register is enabled by the release.

Record:

```text
FH3X model/topology:
PCS firmware:
BMS firmware:
Simulator coverage:
Real-device controls tested:
Validation duration:
Known limitations:
```

## Publication

- [ ] The final diff, test evidence, known limitations, and hardware status receive human approval.
- [ ] A full GitHub Release is created after all required Actions pass.
- [ ] The release is neither a draft nor a pre-release.
- [ ] The released version is installed once more through HACS.
- [ ] The HACS default-catalog pull request is submitted from an editable personal-account fork.
