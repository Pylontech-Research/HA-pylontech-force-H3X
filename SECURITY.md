# Security policy

## Supported versions

Security fixes are provided for the latest published release. Users should
upgrade through HACS before reporting a problem that only occurs on an older
version.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use
[GitHub private vulnerability reporting](https://github.com/pylontech-sw/HA-pylontech-force-H3X/security/advisories/new)
and include:

- the integration and Home Assistant versions;
- the affected FH3X capability;
- reproduction steps that do not expose a live system to unsafe writes;
- the expected impact; and
- logs or diagnostics with addresses, credentials, and serial numbers removed.

Do not include passwords, tokens, Home Assistant backups, or unredacted packet
captures. A maintainer will acknowledge the report, assess the affected
versions, and coordinate a fix and disclosure when appropriate.

## Local-network and control model

The integration communicates with Modbus TCP port `502` on the local network.
Modbus TCP does not provide transport encryption or authentication. Keep the
FH3X and Home Assistant on a trusted network and do not expose port `502` to the
internet.

FH3X controls can change battery, grid, EPS, and schedule behavior. Only enable
advanced controls when their operating effect and installation limits are
understood. The integration does not treat an unavailable value as zero and
verifies writable settings by reading the device state back.
