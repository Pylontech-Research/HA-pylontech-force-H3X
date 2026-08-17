# Contributing

Contributions are welcome for reproducible FH3X and Home Assistant use cases.
Read [`AGENTS.md`](AGENTS.md) before changing protocol, discovery, entities, or
writable controls.

## Development checks

Run:

```bash
python3 -m compileall -q custom_components tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
ruff check custom_components tests scripts
ruff format --check custom_components tests scripts
```

HACS validation and Hassfest must also pass on the pull request.

## Protocol changes

Every register change must document the source document version, absolute
address or offset interpretation, device ID, width, signedness, scale, and
unit. Add a regression test using a captured or synthetic register block.

Do not expose a writable register until its allowed range, sign convention,
operating-mode interlock, read-back result, and safe real-device test have been
reviewed. A simulator result is not real-device validation.

## Compatibility

Do not change entity unique IDs, config-entry unique IDs, PCS device ID `2`, or
BMS device ID `1` without an explicit migration and regression tests. Preserve
user-disabled entities when changing visibility profiles.

## Diagnostics and reports

Use the issue templates. Remove passwords, tokens, IP addresses, device serial
numbers, backups, and private packet captures before attaching diagnostics.

## Pull requests

Keep commits focused and retain every section of the pull request template.
Include exact test commands, simulator coverage, real-device model and
firmware, known limitations, and whether hardware validation remains pending.
