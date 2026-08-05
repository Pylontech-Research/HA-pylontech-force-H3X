import { BatteryCharging, Home, Network, Sun, Zap } from "./Icons";
import type { EnergyFlowSnapshot } from "../ha/types";
import { formatPower } from "../lib/normalize";

type Props = { flow: EnergyFlowSnapshot; reducedMotion?: boolean };

function Lane({
  d,
  color,
  active,
  reverse = false,
  reducedMotion,
}: {
  d: string;
  color: string;
  active: boolean;
  reverse?: boolean;
  reducedMotion?: boolean;
}) {
  return (
    <g className={`energy-lane ${active ? "is-active" : ""}`}>
      <path className="lane-base" d={d} />
      {active && !reducedMotion ? (
        <path
          className="lane-pulse"
          d={d}
          style={{ stroke: color, animationDirection: reverse ? "reverse" : "normal" }}
        />
      ) : null}
      <path className="lane-accent" d={d} style={{ stroke: active ? color : undefined }} />
    </g>
  );
}

function Node({
  kind,
  title,
  value,
  tone,
  icon,
  subtitle,
}: {
  kind: string;
  title: string;
  value: string;
  tone: string;
  icon: React.ReactNode;
  subtitle?: string;
}) {
  return (
    <div className={`flow-node flow-node-${kind}`} style={{ "--node-tone": tone } as React.CSSProperties}>
      <div className="flow-node-icon">{icon}</div>
      <div className="flow-node-copy">
        <span className="flow-node-title">{title}</span>
        <strong>{value}</strong>
        {subtitle ? <small>{subtitle}</small> : null}
      </div>
    </div>
  );
}

export function EnergyFlow({ flow, reducedMotion = false }: Props) {
  const gridValue = flow.gridImportW > 0 ? flow.gridImportW : flow.gridExportW;
  const gridLabel = flow.gridImportW > 0 ? "购电" : flow.gridExportW > 0 ? "馈电" : "待机";
  const batteryValue = flow.batteryChargeW > 0 ? flow.batteryChargeW : flow.batteryDischargeW;
  const batteryLabel = flow.batteryChargeW > 0 ? "充电" : flow.batteryDischargeW > 0 ? "放电" : "待机";
  const status =
    flow.availability === "offline"
      ? "设备离线，暂时无法获取实时功率"
      : flow.availability === "stale"
        ? "数据更新延迟，正在等待设备响应"
        : flow.pvPowerW > 0 && flow.batteryChargeW > 0
          ? "光伏正在供给家庭，多余电量进入电池"
          : flow.batteryDischargeW > 0
            ? "电池正在为家庭负载提供电力"
            : flow.gridImportW > 0
              ? "家庭当前主要使用电网电力"
              : "系统在线，等待能量流动";

  return (
    <section className="flow-card" aria-label="实时能量流">
      <div className="flow-card-head">
        <div>
          <span className="eyebrow">LIVE ENERGY FLOW</span>
          <h2>现在发生了什么</h2>
          <p>{status}</p>
        </div>
        <div className={`live-badge ${flow.availability}`}>
          <span className="live-dot" />
          {flow.availability === "online" ? "实时" : flow.availability === "stale" ? "延迟" : "离线"}
        </div>
      </div>
      <div className="flow-stage">
        <svg className="flow-lines" viewBox="0 0 900 460" role="img" aria-label="光伏、电池、电网和负载能量流">
          <defs>
            <linearGradient id="pv-lane" x1="0" x2="1">
              <stop offset="0" stopColor="#F4C66B" />
              <stop offset="1" stopColor="#FFE6A6" />
            </linearGradient>
            <linearGradient id="battery-lane" x1="0" x2="1">
              <stop offset="0" stopColor="#8E8BFF" />
              <stop offset="1" stopColor="#C1BFFF" />
            </linearGradient>
            <linearGradient id="grid-lane" x1="0" x2="1">
              <stop offset="0" stopColor="#6BA7FF" />
              <stop offset="1" stopColor="#A9CDFF" />
            </linearGradient>
            <filter id="lane-glow">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          <Lane d="M170 112 C 300 112, 330 210, 402 220" color="url(#pv-lane)" active={flow.pvPowerW > 0} reducedMotion={reducedMotion} />
          <Lane d="M170 112 C 300 112, 330 290, 402 300" color="url(#pv-lane)" active={flow.pvPowerW > 0 && flow.batteryChargeW > 0} reducedMotion={reducedMotion} />
          <Lane d="M730 112 C 610 112, 575 210, 500 220" color="url(#grid-lane)" active={flow.gridImportW > 0} reducedMotion={reducedMotion} reverse />
          <Lane d="M500 300 C 585 300, 620 112, 730 112" color="url(#grid-lane)" active={flow.gridExportW > 0} reducedMotion={reducedMotion} />
          <Lane d="M450 280 C 450 250, 450 230, 450 210" color="url(#battery-lane)" active={flow.batteryDischargeW > 0} reducedMotion={reducedMotion} reverse />
          <Lane d="M450 230 C 450 260, 450 280, 450 300" color="url(#battery-lane)" active={flow.batteryChargeW > 0} reducedMotion={reducedMotion} />
          <circle className="flow-core-halo" cx="450" cy="255" r="82" />
          <path className="flow-house" d="M398 255 L450 208 L502 255 V318 H398 Z" />
          <path className="flow-house-detail" d="M430 318 V278 H470 V318 M414 260 H430 M470 260 H486" />
        </svg>
        <Node kind="pv" title="光伏" value={formatPower(flow.pvPowerW, true)} tone="#F4C66B" icon={<Sun size={20} />} subtitle="PV1 · PV2 · PV3" />
        <Node kind="grid" title="电网" value={formatPower(gridValue, true)} tone="#79AEFF" icon={<Network size={20} />} subtitle={gridLabel} />
        <Node kind="load" title="家庭负载" value={formatPower(flow.loadPowerW, true)} tone="#53E3DC" icon={<Home size={20} />} subtitle="实时用电" />
        <Node kind="battery" title="FH3X 电池" value={formatPower(batteryValue, true)} tone="#A29CFF" icon={<BatteryCharging size={20} />} subtitle={`${batteryLabel} · ${flow.batterySoc === null ? "—" : `${Math.round(flow.batterySoc)}% SOC`}`} />
        <div className="flow-center-label"><Zap size={15} /> FH3X HOME ENERGY</div>
      </div>
    </section>
  );
}
