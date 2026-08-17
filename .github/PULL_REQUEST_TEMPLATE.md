## Summary

Describe the user-visible problem and the resulting behavior. Keep this section
focused on what changed and why it is needed.

## Change type

- [ ] Protocol or data decoding
- [ ] Sensor or entity model
- [ ] Control or Modbus write path
- [ ] Discovery or config flow
- [ ] Reliability, diagnostics, or alarms
- [ ] Documentation, tests, or release engineering

## Compatibility and safety

- [ ] Existing entity unique IDs and config-entry unique IDs are unchanged, or a migration is included and tested.
- [ ] PCS device ID `2`, BMS device ID `1`, and existing Modbus addresses are unchanged, or the protocol source and migration are documented.
- [ ] New or changed writable controls have range, unit, sign, interlock, read-back, and failure tests.
- [ ] No credentials, private network data, backups, generated artifacts, or unlicensed protocol documents are included.
- [ ] `strings.json` and maintained translations are synchronized when user-facing text changes.
- [ ] `README.md` and `CHANGELOG.md` are updated when behavior or release contents change.

## Test evidence

List the exact commands and results. Do not write only “tests pass.”

```text
python3 -m compileall -q custom_components tests
python3 -m unittest discover -s tests -v
```

- [ ] Standalone compile and unit tests pass.
- [ ] Ruff checks pass when Ruff is available.
- [ ] Config-flow and unload/reload behavior were exercised when applicable.
- [ ] Home Assistant Core/Hassfest tests were run when this targets Core.

## Device validation

State which environment was used:

- Simulator and scenario:
- Real FH3X model/topology:
- PCS firmware:
- BMS firmware:
- Validation duration and result:

- [ ] The change does not require real-device validation.
- [ ] Real-device validation is complete.
- [ ] Real-device validation is still required and is called out as a limitation.

## Reviewer notes

Identify protocol assumptions, intentionally unsupported cases, follow-up work,
and any part that deserves extra review.
