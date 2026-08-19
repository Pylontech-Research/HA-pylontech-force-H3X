# HA Core migration notes

The official Core integration and this HACS integration intentionally use the
same domain, `pylontech_fh3x`, so config-entry data and entity identifiers stay
stable when moving to Core.

Home Assistant loads a custom integration before a built-in integration with
the same domain. They therefore must not be installed in the same HA
configuration directory. To run both implementations against the same
hardware, use two isolated HA instances (or two containers) and never poll the
same Modbus endpoint concurrently.

Migration procedure:

1. Back up the HA instance.
2. Stop HA and remove/disable the HACS custom component.
3. Install the Core build with the published `pylontech-fh3x` dependency.
4. Start HA; existing host/port config-entry data is reused by the Core flow.
5. Verify the serial number, entity availability, energy statistics and control
   permissions before removing the backup.

The shared protocol package is kept in the sibling `pylontech_fh3x` repository.
The HACS manifest must not be changed to require it until version `0.1.0` is
published to PyPI; otherwise a clean HACS installation cannot resolve the
dependency.
