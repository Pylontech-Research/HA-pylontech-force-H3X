import { useEffect, useMemo, useState } from "react";
import { flowSnapshot } from "../lib/normalize";
import type { EnergyFlowSnapshot, Hass } from "./types";

export function useHassTick(hass?: Hass): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!hass?.connection) return;
    let active = true;
    let unsubscribe: (() => void) | undefined;
    void hass.connection.subscribeEvents(() => {
      if (active) setTick((value) => value + 1);
    }, "state_changed").then((stop) => {
      unsubscribe = stop;
    });
    return () => {
      active = false;
      unsubscribe?.();
    };
  }, [hass]);
  return tick;
}

export function useEnergyFlow(hass?: Hass): EnergyFlowSnapshot {
  const tick = useHassTick(hass);
  return useMemo(() => {
    void tick;
    return hass
      ? flowSnapshot(hass)
      : {
          timestamp: new Date().toISOString(),
          pvPowerW: 0,
          loadPowerW: 0,
          gridPowerW: 0,
          gridImportW: 0,
          gridExportW: 0,
          batteryPowerW: 0,
          batteryChargeW: 0,
          batteryDischargeW: 0,
          batterySoc: null,
          inverterState: "unknown",
          batteryState: "unknown",
          availability: "offline",
        };
  }, [hass, tick]);
}

export async function selectOption(
  hass: Hass,
  entityId: string,
  option: string,
): Promise<void> {
  await hass.callService("select", "select_option", {
    entity_id: entityId,
    option,
  });
}

export async function setNumber(
  hass: Hass,
  entityId: string,
  value: number,
): Promise<void> {
  await hass.callService("number", "set_value", {
    entity_id: entityId,
    value,
  });
}

export async function setSwitch(
  hass: Hass,
  entityId: string,
  on: boolean,
): Promise<void> {
  await hass.callService("switch", on ? "turn_on" : "turn_off", {
    entity_id: entityId,
  });
}

export async function setTime(hass: Hass, entityId: string, value: string): Promise<void> {
  const time = /^\d{2}:\d{2}$/.test(value) ? `${value}:00` : value;
  await hass.callService("time", "set_value", { entity_id: entityId, time });
}
