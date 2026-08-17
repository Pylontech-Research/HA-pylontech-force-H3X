# FH3X Repository Instructions

This repository contains the Home Assistant custom integration for the
Pylontech Force H3X. These instructions apply to the whole repository.

## Scope and compatibility

- Keep the integration installable as a HACS custom integration until a
  separate Home Assistant Core contribution branch is created.
- Target the Python version configured in `pyproject.toml`. Do not adopt
  Home Assistant Core `dev`-only syntax while released Home Assistant versions
  supported by this repository still use an older Python runtime.
- Preserve existing entity unique IDs, config-entry unique IDs, Modbus
  addresses, PCS device ID `2`, and BMS device ID `1`. A change to any of these
  requires an explicit migration and regression tests.
- Do not reintroduce or register the experimental FH3X frontend panel unless a
  user explicitly requests that product direction.

## Git and pull requests

- After a pull request is opened, do not amend, squash, or rebase commits that
  have already been pushed. Add follow-up commits so reviewers can see what
  changed.
- Use `.github/PULL_REQUEST_TEMPLATE.md` and keep every section and unchecked
  checkbox in the pull request body.
- Keep commits focused. Separate protocol, entity-model, discovery, control,
  and release-engineering changes when they can be reviewed independently.
- Do not commit credentials, Home Assistant backups, packet captures containing
  private network details, generated browser output, caches, or protocol
  documents without confirmed redistribution rights.

## Development checks

Use `python3` from the active development environment.

Run the standalone checks before committing:

```bash
python3 -m compileall -q custom_components tests
python3 -m unittest discover -s tests -v
```

When Ruff is available, also run:

```bash
ruff check custom_components tests
ruff format --check custom_components tests
```

When modifying `strings.json`, keep `translations/en.json` and
`translations/zh-Hans.json` synchronized and exercise every changed config-flow
branch.

Changes intended for Home Assistant Core must additionally be tested inside a
current Core development environment with its prescribed `uv`, `pytest`,
translation-generation, Hassfest, and pre-commit commands. Passing the local
standalone tests is not a substitute for Core's test suite.

## Tests

- Add regression tests for every protocol offset, signed value, bit mask,
  cumulative-energy guard, discovery transition, and writable control change.
- Give test function parameters concrete types where the test framework passes
  parameters. Avoid `Any` when a useful concrete type is available.
- Avoid branching inside tests. Prefer separate cases, table-driven tests, or
  `subTest`; use `pytest.mark.parametrize` on a future Core branch.
- Reuse constants for repeated entity IDs, register addresses, and captured
  protocol values.
- Tests for writable controls must cover the encoded write, serialized access,
  read-back verification, failure behavior, and final refreshed state.
- Never treat a simulator-only result as real-device validation. Record the
  device model, firmware, topology, and safe test conditions for hardware
  checks.

## Python and Home Assistant practices

- Prefer concrete types and direct dictionary access when validation guarantees
  that a key exists. Use `.get()` only when absence is part of the data model.
- Keep `try` blocks as small as possible and catch only expected exceptions.
- Raise Home Assistant-facing exceptions with a clear failure reason; do not
  silently restore an optimistic UI value after a failed device write.
- Keep comments concise and explain non-obvious constraints or reasons, not the
  code immediately below them.
- Do not add divider comments such as `# --- Sensors ---`.
- Use `ConfigEntry.runtime_data` for live clients and coordinators, and close
  transports during config-entry unload.
- Use native Home Assistant device classes, state classes, entity categories,
  translations, and disabled-by-default behavior where applicable.
- If service actions are added later and they change configuration or have
  security implications, register them as administrator-only actions. Do not
  add a service action when a native entity control is sufficient.
- Use Gold or Platinum Integration Quality Scale integrations as the primary
  examples for new Home Assistant patterns. Tesla Powerwall may be used as a
  product-domain reference, but not as the sole code-quality baseline.

## Protocol and control safety

- The protocol documents are the source of truth for register meaning, width,
  signedness, scaling, and device address. Capture the exact section and offset
  interpretation in tests.
- Do not expose an unverified writable register. Document its allowed range,
  unit, sign convention, operating-mode interlock, and real-device validation.
- Keep polling, writes, read-back verification, and immediate refresh
  serialized through the existing coordinator/client locking model.
- A communication timeout is not a device state and must not be interpreted as
  an alarm recovery, disabled control, zero power, or zero cumulative energy.

## Release discipline

- Keep the manifest version, changelog entry, Git tag, and GitHub Release
  version aligned.
- Validate a clean install, upgrade, restart, unload, and rollback before a
  public release.
- HACS release work must pass HACS validation and Hassfest without ignored
  failures.

## AI-assisted contributions

- A human must review, understand, and be able to explain every generated
  change before it is submitted upstream.
- Do not autonomously open issues or pull requests, publish releases, or post
  comments on behalf of the user.
- Before any external submission, present the final diff, test evidence, known
  limitations, and hardware-validation status to the user for approval.
