# FH3X Energy Console

The React/Vite source for the local Home Assistant panel at `/fh3x`.

```bash
npm install
npm run test
npm run build
```

`npm run build` writes the browser bundle directly to
`custom_components/pylontech_fh3x/frontend/`. Home Assistant serves that
directory through the custom integration; Green does not run Node.js.

The panel reads the existing FH3X entities and calls their existing HA
services. It does not open a second Modbus connection. Power direction is
kept consistent with the integration: positive grid power is import,
negative grid power is export; positive battery power is discharge and
negative battery power is charge.
