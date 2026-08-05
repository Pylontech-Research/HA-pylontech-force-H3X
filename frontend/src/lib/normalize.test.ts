import { describe, expect, it } from "vitest";
import { flowSnapshot } from "./normalize";
import type { Hass } from "../ha/types";

function hass(values: Record<string, string>, age = new Date().toISOString()): Hass {
  return { states: Object.fromEntries(Object.entries(values).map(([entity_id, state]) => [entity_id, { entity_id, state, attributes: {}, last_updated: age }])), callService: async () => undefined };
}

describe("FH3X energy normalization", () => {
  it("keeps protocol signs and derives directional flows", () => {
    const snapshot = flowSnapshot(hass({
      "sensor.force_h3x_solar_power": "4200",
      "sensor.force_h3x_load_power": "1800",
      "sensor.force_h3x_grid_power": "600",
      "sensor.force_h3x_battery_power": "-900",
      "sensor.force_h3x_battery_soc": "72.4",
    }));
    expect(snapshot.gridImportW).toBe(600);
    expect(snapshot.gridExportW).toBe(0);
    expect(snapshot.batteryChargeW).toBe(900);
    expect(snapshot.batteryDischargeW).toBe(0);
    expect(snapshot.batterySoc).toBe(72.4);
    expect(snapshot.availability).toBe("online");
  });

  it("marks stale and offline data using the polling window", () => {
    const old = new Date(Date.now() - 16000).toISOString();
    const snapshot = flowSnapshot(hass({
      "sensor.force_h3x_solar_power": "0",
      "sensor.force_h3x_load_power": "0",
      "sensor.force_h3x_grid_power": "0",
      "sensor.force_h3x_battery_power": "0",
    }, old), 10);
    expect(snapshot.availability).toBe("stale");
    const veryOld = new Date(Date.now() - 31000).toISOString();
    expect(flowSnapshot(hass({
      "sensor.force_h3x_solar_power": "0",
      "sensor.force_h3x_load_power": "0",
      "sensor.force_h3x_grid_power": "0",
      "sensor.force_h3x_battery_power": "0",
    }, veryOld), 10).availability).toBe("offline");
  });
});
