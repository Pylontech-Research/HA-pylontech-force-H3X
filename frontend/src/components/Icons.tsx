import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };
const paths: Record<string, string> = {
  alert: "M12 3 2.8 19h18.4L12 3Zm0 6v4m0 3h.01",
  down: "M12 4v15m0 0-6-6m6 6 6-6",
  up: "M12 20V5m0 0 6 6m-6-6-6 6",
  battery: "M5 7h13a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Zm14 3h2v4h-2M8 10h4v4H8z",
  check: "m5 12 4 4L19 6",
  chevron: "m9 18 6-6-6-6",
  gauge: "M4 14a8 8 0 1 1 16 0M12 14l3-4M5 19h14",
  cpu: "M8 8h8v8H8zM4 10v4m16-4v4M10 4v4m4-4v4m-4 12v-4m4 4v-4",
  house: "m3 10 9-7 9 7v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V10Zm6 11v-6h6v6",
  layout: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  moon: "M20 15.5A8 8 0 0 1 8.5 4 8 8 0 1 0 20 15.5Z",
  network: "M5 4h4v4H5zM15 4h4v4h-4zM10 16h4v4h-4zM9 6h6m-3 2v8m-3-4h6",
  panel: "M4 4h16v16H4zM4 9h16M9 9v11",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0-0-8Zm0-6v3m0 14v3M4.9 4.9 7 7m10 10 2.1 2.1M2 12h3m14 0h3M4.9 19.1 7 17m10-10 2.1-2.1",
  shield: "M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Zm-3 9 2 2 4-4",
  sun: "M12 3v2m0 14v2M5.6 5.6 7 7m10 10 1.4 1.4M3 12h2m14 0h2M5.6 18.4 7 17m10-10 1.4-1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
  thermometer: "M10 14.5V5a2 2 0 1 1 4 0v9.5a4 4 0 1 1-4 0ZM12 5v9",
  waves: "M3 12c3-5 6 5 9 0s6 5 9 0M3 17c3-5 6 5 9 0s6 5 9 0",
  zap: "m13 2-9 12h7l-1 8 9-12h-7l1-8Z",
};
function Icon({ name, size = 18, ...props }: IconProps & { name: string }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name] ?? paths.zap} /></svg>;
}
const make = (name: string) => (props: IconProps) => <Icon name={name} {...props} />;
export const AlertTriangle = make("alert");
export const ArrowDownToLine = make("down");
export const ArrowUpFromLine = make("up");
export const BatteryCharging = make("battery");
export const CheckCircle2 = make("check");
export const ChevronRight = make("chevron");
export const CircleGauge = make("gauge");
export const Cpu = make("cpu");
export const Gauge = make("gauge");
export const House = make("house");
export const Home = make("house");
export const LayoutDashboard = make("layout");
export const Moon = make("moon");
export const Network = make("network");
export const PanelTop = make("panel");
export const Settings2 = make("settings");
export const ShieldCheck = make("shield");
export const Sun = make("sun");
export const SunMedium = make("sun");
export const Thermometer = make("thermometer");
export const Waves = make("waves");
export const Zap = make("zap");
