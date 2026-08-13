import { ENTITY_IDS, type EntityKey } from "../ha/entities";
import type { AlarmItem, EnergyFlowSnapshot, EntityState, Hass } from "../ha/types";

const now = () => Date.now();

export function findEntity(hass: Hass, key: EntityKey): EntityState | undefined {
  const direct = ENTITY_IDS[key].map((id) => hass.states[id]).find(Boolean);
  if (direct) return direct;
  // Entity IDs are generated from the device serial (for example
  // ``sensor.fh3x6khy1pau_bms_alarm``), so the static demo IDs above cannot
  // be the only lookup strategy for a real installation.
  const suffixes = ENTITY_IDS[key].map((id) =>
    id.replace(/^[^.]+\./, "").replace(/^force_h3x_/, ""),
  );
  return Object.entries(hass.states).find(([id]) => {
    const objectId = id.replace(/^[^.]+\./, "");
    return suffixes.some((suffix) => objectId === suffix || objectId.endsWith(`_${suffix}`));
  })?.[1];
}

export function numberState(hass: Hass, key: EntityKey): number | null {
  const entity = findEntity(hass, key);
  if (!entity || ["unknown", "unavailable"].includes(entity.state)) return null;
  const value = Number(entity.state);
  return Number.isFinite(value) ? value : null;
}

function ageMs(entity?: EntityState): number {
  const stamp = entity?.last_updated ?? entity?.last_changed;
  return stamp ? Math.max(0, now() - Date.parse(stamp)) : Number.POSITIVE_INFINITY;
}

export function flowSnapshot(hass: Hass, scanIntervalSeconds = 10): EnergyFlowSnapshot {
  const pv = Math.max(0, numberState(hass, "pvPower") ?? 0);
  const load = Math.max(0, numberState(hass, "loadPower") ?? 0);
  const grid = numberState(hass, "gridPower") ?? 0;
  const battery = numberState(hass, "batteryPower") ?? 0;
  const timestamps = ["pvPower", "loadPower", "gridPower", "batteryPower"].map((key) =>
    ageMs(findEntity(hass, key as EntityKey)),
  );
  const oldest = Math.max(...timestamps);
  const threshold = scanIntervalSeconds * 1000;
  const availability: EnergyFlowSnapshot["availability"] =
    oldest > threshold * 3
      ? "offline"
      : oldest > threshold * 1.5
        ? "stale"
        : "online";

  return {
    timestamp: new Date().toISOString(),
    pvPowerW: pv,
    loadPowerW: load,
    gridPowerW: grid,
    gridImportW: Math.max(0, grid),
    gridExportW: Math.max(0, -grid),
    batteryPowerW: battery,
    batteryChargeW: Math.max(0, -battery),
    batteryDischargeW: Math.max(0, battery),
    batterySoc: numberState(hass, "batterySoc"),
    inverterState: findEntity(hass, "inverterState")?.state ?? "unknown",
    batteryState: findEntity(hass, "batteryState")?.state ?? "unknown",
    availability,
  };
}

function issues(entity?: EntityState): string[] {
  const value = entity?.attributes.active_issues;
  return Array.isArray(value) ? value.map(String) : [];
}

export function alarmItems(hass: Hass): AlarmItem[] {
  const defs: Array<[EntityKey, string, string]> = [
    ["inverterFault", "逆变器故障", "fault_code"],
    ["inverterWarning", "逆变器警告", "warning_code"],
    ["bmsProtection", "BMS 保护", "error_code_1"],
    ["bmsAlarm", "BMS 告警", ""],
  ];
  return defs.map(([key, label, codeKey]) => {
    const entity = findEntity(hass, key);
    const state = (entity?.state ?? "unknown") as AlarmItem["state"];
    return {
      id: ENTITY_IDS[key][0],
      label,
      state,
      issues: issues(entity),
      issueIds: Array.isArray(entity?.attributes.active_issue_ids)
        ? entity.attributes.active_issue_ids.map(String)
        : [],
      rawStatus1: typeof entity?.attributes.raw_status_1 === "number" ? entity.attributes.raw_status_1 : undefined,
      rawStatus2: typeof entity?.attributes.raw_status_2 === "number" ? entity.attributes.raw_status_2 : undefined,
      code: codeKey ? (entity?.attributes[codeKey] as string | number | undefined) : undefined,
    };
  });
}

export function formatPower(value: number, compact = false): string {
  const abs = Math.abs(value);
  if (compact && abs >= 1000) return `${(value / 1000).toFixed(1)} kW`;
  return `${Math.round(value).toLocaleString("zh-CN")} W`;
}

export function formatEnergy(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value.toFixed(1)} kWh`;
}
