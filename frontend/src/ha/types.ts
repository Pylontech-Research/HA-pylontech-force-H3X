export type EntityState = {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
  last_changed?: string;
  last_updated?: string;
};

export type HassConnection = {
  subscribeEvents: (
    callback: (event: { data?: { entity_id?: string } }) => void,
    eventType: string,
  ) => Promise<() => void>;
};

export type Hass = {
  states: Record<string, EntityState>;
  callService: (
    domain: string,
    service: string,
    data: Record<string, unknown>,
  ) => Promise<unknown>;
  callWS?: (message: Record<string, unknown>) => Promise<unknown>;
  connection?: HassConnection;
  themes?: { darkMode?: boolean };
};

export type EnergyFlowSnapshot = {
  timestamp: string;
  pvPowerW: number;
  loadPowerW: number;
  gridPowerW: number;
  gridImportW: number;
  gridExportW: number;
  batteryPowerW: number;
  batteryChargeW: number;
  batteryDischargeW: number;
  batterySoc: number | null;
  inverterState: string;
  batteryState: string;
  availability: "online" | "stale" | "offline";
};

export type AlarmItem = {
  id: string;
  label: string;
  state: "on" | "off" | "unavailable" | "unknown";
  issues: string[];
  code?: string | number;
};
