import {
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpFromLine,
  BatteryCharging,
  CheckCircle2,
  ChevronRight,
  CircleGauge,
  Cpu,
  Gauge,
  House,
  LayoutDashboard,
  Moon,
  Network,
  PanelTop,
  Settings2,
  ShieldCheck,
  Sun,
  SunMedium,
  Thermometer,
  Waves,
  Zap,
} from "./components/Icons";
import { useEffect, useMemo, useState } from "react";
import { EnergyFlow } from "./components/EnergyFlow";
import { MetricCard } from "./components/MetricCard";
import { StatusPill } from "./components/StatusPill";
import { ENTITY_IDS } from "./ha/entities";
import { selectOption, setNumber, setSwitch, setTime, useEnergyFlow } from "./ha/useHass";
import type { AlarmEvent, AlarmItem, Hass } from "./ha/types";
import { alarmItems, findEntity, formatEnergy, formatPower, numberState } from "./lib/normalize";

type PageKey = "overview" | "solar" | "battery" | "load" | "grid" | "strategy" | "alerts" | "diagnostics" | "settings";

const navItems: Array<{ key: PageKey; label: string; icon: typeof LayoutDashboard }> = [
  { key: "overview", label: "能源总览", icon: LayoutDashboard },
  { key: "solar", label: "光伏", icon: SunMedium },
  { key: "battery", label: "电池", icon: BatteryCharging },
  { key: "load", label: "家庭负载", icon: House },
  { key: "grid", label: "电网", icon: Network },
  { key: "strategy", label: "运行策略", icon: Gauge },
  { key: "alerts", label: "告警中心", icon: AlertTriangle },
  { key: "diagnostics", label: "设备诊断", icon: Cpu },
];

const fallbackHass: Hass = { states: {}, callService: async () => undefined };

function value(hass: Hass, key: Parameters<typeof numberState>[1]): number | null {
  return numberState(hass, key);
}

function EntityValue({ hass, entityKey, suffix = "" }: { hass: Hass; entityKey: keyof typeof ENTITY_IDS; suffix?: string }) {
  const entity = findEntity(hass, entityKey);
  return <>{entity?.state && !["unknown", "unavailable"].includes(entity.state) ? `${entity.state}${suffix}` : "—"}</>;
}

function MiniChart({ tone = "cyan" }: { tone?: string }) {
  return (
    <svg className={`mini-chart chart-${tone}`} viewBox="0 0 340 90" preserveAspectRatio="none" aria-label="历史趋势示意图">
      <defs><linearGradient id={`chart-${tone}`} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopOpacity=".32" /><stop offset="1" stopOpacity="0" /></linearGradient></defs>
      <path className="chart-area" d="M0 76 C32 66 36 46 70 58 S108 42 136 52 S174 30 202 48 S240 58 266 34 S306 50 340 18 V90 H0Z" />
      <path className="chart-line" d="M0 76 C32 66 36 46 70 58 S108 42 136 52 S174 30 202 48 S240 58 266 34 S306 50 340 18" />
    </svg>
  );
}

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <header className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</header>;
}

function OverviewPage({ hass, reducedMotion }: { hass: Hass; reducedMotion: boolean }) {
  const flow = useEnergyFlow(hass);
  const pvEnergy = value(hass, "pvEnergy");
  const gridImport = value(hass, "gridImportEnergy");
  const chargeEnergy = value(hass, "batteryChargeEnergy");
  const soc = flow.batterySoc;
  return <>
    <PageHeader eyebrow="FH3X / LIVE SYSTEM" title="能源总览" description="从今天的第一缕阳光，到现在这一刻的每一瓦电。" action={<StatusPill state={flow.availability} label={flow.availability === "online" ? "系统在线" : flow.availability === "stale" ? "数据延迟" : "设备离线"} />} />
    <EnergyFlow flow={flow} reducedMotion={reducedMotion} />
    <div className="metric-grid four">
      <MetricCard label="今日光伏" value={formatEnergy(pvEnergy).replace(" kWh", "")} unit="kWh" trend="PV1 · PV2 · PV3" tone="gold" icon={<Sun size={17} />} />
      <MetricCard label="家庭负载" value={formatPower(flow.loadPowerW, true).replace(" kW", "").replace(" W", "")} unit={Math.abs(flow.loadPowerW) >= 1000 ? "kW" : "W"} trend="实时用电功率" tone="cyan" icon={<House size={17} />} />
      <MetricCard label="电池电量" value={soc === null ? "—" : String(Math.round(soc))} unit="% SOC" trend={flow.batteryState === "unknown" ? "等待 BMS" : flow.batteryState} tone="violet" icon={<BatteryCharging size={17} />} />
      <MetricCard label="今日购电" value={formatEnergy(gridImport).replace(" kWh", "")} unit="kWh" trend={chargeEnergy !== null ? `电池充电 ${formatEnergy(chargeEnergy)}` : "累计值"} tone="blue" icon={<ArrowDownToLine size={17} />} />
    </div>
    <div className="overview-lower">
      <section className="surface-card impact-card"><div className="section-title"><div><span className="eyebrow">IMPACT</span><h2>今天的能量足迹</h2></div><ChevronRight size={18} /></div><div className="impact-row"><div><strong>{pvEnergy === null ? "—" : `${pvEnergy.toFixed(1)} kWh`}</strong><span>光伏产出</span></div><div><strong>{soc === null ? "—" : `${Math.round(soc)}%`}</strong><span>当前电池</span></div><div><strong>{gridImport === null ? "—" : `${gridImport.toFixed(1)} kWh`}</strong><span>电网购电</span></div></div><MiniChart tone="gold" /></section>
      <section className="surface-card status-card"><div className="section-title"><div><span className="eyebrow">SYSTEM STATUS</span><h2>设备状态</h2></div><ShieldCheck size={18} /></div><div className="status-list"><div><span className="status-icon good"><CheckCircle2 size={16} /></span><div><strong>PCS</strong><small><EntityValue hass={hass} entityKey="inverterState" /></small></div><b>正常</b></div><div><span className="status-icon cyan"><Waves size={16} /></span><div><strong>BMS</strong><small><EntityValue hass={hass} entityKey="batteryState" /></small></div><b>在线</b></div><div><span className="status-icon quiet"><Zap size={16} /></span><div><strong>通信</strong><small>Modbus TCP · 地址 1 / 2</small></div><b>稳定</b></div></div></section>
    </div>
  </>;
}

function SolarPage({ hass }: { hass: Hass }) {
  return <><PageHeader eyebrow="PV ARRAY / 3 MPPT" title="光伏" description="三路 MPPT 的实时产出与效率。" /><div className="metric-grid three"><MetricCard label="总功率" value={formatPower(value(hass, "pvPower") ?? 0, true).replace(" kW", "").replace(" W", "")} unit={Math.abs(value(hass, "pvPower") ?? 0) >= 1000 ? "kW" : "W"} tone="gold" icon={<Sun size={17} />} /><MetricCard label="今日发电" value={formatEnergy(value(hass, "pvEnergy")).replace(" kWh", "")} unit="kWh" tone="gold" /><MetricCard label="系统效率" value="—" unit="%" trend="等待额定功率" tone="cyan" /></div><section className="surface-card chart-card"><div className="section-title"><div><span className="eyebrow">PV PRODUCTION</span><h2>光伏功率趋势</h2></div><div className="range-tabs"><button className="active">日</button><button>月</button><button>年</button></div></div><MiniChart tone="gold" /><div className="chart-axis"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>现在</span></div></section><div className="phase-grid">{[1,2,3].map((pv) => <section className="surface-card phase-card" key={pv}><div className="phase-head"><span>PV{pv}</span><span className="phase-live">MPPT</span></div><strong><EntityValue hass={hass} entityKey={`pv${pv}Power` as keyof typeof ENTITY_IDS} suffix=" W" /></strong><div className="phase-meta"><span>电压 — V</span><span>电流 — A</span></div></section>)}</div></>;
}

function BatteryPage({ hass }: { hass: Hass }) {
  const soc = value(hass, "batterySoc");
  return <><PageHeader eyebrow="FH3X BATTERY CABINET" title="电池" description="储能柜健康状态、功率与模块诊断。" action={<StatusPill state="normal" label="BMS 在线" />} /><div className="battery-hero"><div className="battery-visual"><div className="cabinet-lights"><i /><i /><i /></div><div className="cabinet-mark">FH3X</div><div className="cabinet-bars"><span style={{ height: `${Math.max(15, soc ?? 0)}%` }} /></div></div><div className="battery-summary"><span className="eyebrow">STATE OF CHARGE</span><strong>{soc === null ? "—" : `${Math.round(soc)}%`}</strong><p>{findEntity(hass, "batteryState")?.state ?? "等待 BMS 数据"}</p><div className="soc-track"><span style={{ width: `${Math.min(100, Math.max(0, soc ?? 0))}%` }} /></div><div className="battery-meta"><span><small>SOH</small><b><EntityValue hass={hass} entityKey="bmsSoh" suffix="%" /></b></span><span><small>循环</small><b><EntityValue hass={hass} entityKey="bmsCycles" /></b></span><span><small>功率</small><b>{formatPower(value(hass, "batteryPower") ?? 0, true)}</b></span></div></div></div><div className="metric-grid three"><MetricCard label="电池电压" value="—" unit="V" tone="violet" /><MetricCard label="电池温度" value="—" unit="°C" tone="violet" icon={<Thermometer size={17} />} /><MetricCard label="累计放电" value={formatEnergy(value(hass, "batteryDischargeEnergy")).replace(" kWh", "")} unit="kWh" tone="violet" icon={<ArrowUpFromLine size={17} />} /></div><section className="surface-card chart-card"><div className="section-title"><div><span className="eyebrow">BATTERY POWER</span><h2>充放电趋势</h2></div><span className="mono-note">正值放电 · 负值充电</span></div><MiniChart tone="violet" /></section></>;
}

function LoadPage({ hass }: { hass: Hass }) { return <><PageHeader eyebrow="HOUSE LOAD" title="家庭负载" description="实时用电、三相分布与历史趋势。" /><div className="metric-grid three"><MetricCard label="当前负载" value={formatPower(value(hass, "loadPower") ?? 0, true).replace(" kW", "").replace(" W", "")} unit="kW" tone="cyan" icon={<House size={17} />} /><MetricCard label="R 相" value="—" unit="W" tone="cyan" /><MetricCard label="S / T 相" value="—" unit="W" tone="cyan" /></div><section className="surface-card chart-card"><div className="section-title"><div><span className="eyebrow">LOAD PROFILE</span><h2>家庭用电趋势</h2></div><div className="range-tabs"><button className="active">日</button><button>月</button><button>年</button></div></div><MiniChart tone="cyan" /></section><div className="empty-note"><CircleGauge size={18} />高耗能设备识别将在接入独立负载实体后显示。</div></>; }

function GridPage({ hass }: { hass: Hass }) { return <><PageHeader eyebrow="GRID CONNECTION" title="电网" description="购电、馈电和三相并网状态。" /><div className="metric-grid three"><MetricCard label="并网功率" value={formatPower(value(hass, "gridPower") ?? 0, true).replace(" kW", "").replace(" W", "")} unit="kW" tone="blue" icon={<Network size={17} />} /><MetricCard label="累计购电" value={formatEnergy(value(hass, "gridImportEnergy")).replace(" kWh", "")} unit="kWh" tone="blue" icon={<ArrowDownToLine size={17} />} /><MetricCard label="累计馈电" value={formatEnergy(value(hass, "gridExportEnergy")).replace(" kWh", "")} unit="kWh" tone="blue" icon={<ArrowUpFromLine size={17} />} /></div><section className="surface-card chart-card"><div className="section-title"><div><span className="eyebrow">GRID POWER</span><h2>并网功率趋势</h2></div><span className="mono-note">正值购电 · 负值馈电</span></div><MiniChart tone="blue" /></section><div className="phase-grid">{["R", "S", "T"].map((phase) => <section className="surface-card phase-card" key={phase}><div className="phase-head"><span>{phase} 相</span><span className="phase-live">50.00 Hz</span></div><strong>— <small>V</small></strong><div className="phase-meta"><span>电流 — A</span><span>功率 — W</span></div></section>)}</div></>; }

function StrategyPage({ hass }: { hass: Hass }) {
  const ems = findEntity(hass, "emsMode")?.state ?? "unknown";
  const enabled = findEntity(hass, "period1Enabled")?.state === "on";
  const emsOptions = (findEntity(hass, "emsMode")?.attributes.options as string[] | undefined) ?? [];
  const [start, setStart] = useState(() => (findEntity(hass, "period1Start")?.state ?? "00:00").slice(0, 5));
  const [end, setEnd] = useState(() => (findEntity(hass, "period1End")?.state ?? "00:00").slice(0, 5));
  const [power, setPower] = useState(() => Number(findEntity(hass, "period1Power")?.state ?? 0));
  const [pending, setPending] = useState(false);
  async function updateMode(option: string) { if (!window.confirm(`确认将计划1设置为${option === "charge" ? "充电" : "放电"}？`)) return; setPending(true); try { await selectOption(hass, ENTITY_IDS.period1Mode[0], option); } finally { setPending(false); } }
  async function updateEnabled(on: boolean) { if (!window.confirm(`${on ? "启用" : "停用"}计划1？`)) return; setPending(true); try { await setSwitch(hass, ENTITY_IDS.period1Enabled[0], on); } finally { setPending(false); } }
  async function updateEms(option: string) { if (!option || option === ems || !window.confirm(`确认将 EMS 切换为“${option}”？`)) return; setPending(true); try { await selectOption(hass, ENTITY_IDS.emsMode[0], option); } finally { setPending(false); } }
  async function savePlan() {
    if (!window.confirm(`确认保存计划1？\n${start}–${end} · ${power}% · ${findEntity(hass, "period1Mode")?.state ?? "未选择模式"}`)) return;
    setPending(true);
    try {
      await Promise.all([
        setTime(hass, ENTITY_IDS.period1Start[0], start),
        setTime(hass, ENTITY_IDS.period1End[0], end),
        setNumber(hass, ENTITY_IDS.period1Power[0], power),
      ]);
    } finally { setPending(false); }
  }
  return <><PageHeader eyebrow="OPERATING STRATEGY" title="运行策略" description="用目标而不是技术参数，控制储能系统的下一步。" action={<StatusPill state="normal" label={pending ? "保存中" : "已同步"} />} /><section className="strategy-hero surface-card"><div><span className="eyebrow">EMS MODE</span><h2>{ems === "backup" ? "备电优先" : ems === "self_consumption" ? "自发自用" : ems === "user" ? "用户模式" : ems}</h2><p>当前策略由 PCS 地址 2 执行，写入后会读回校验。</p>{emsOptions.length > 0 ? <label className="inline-select">切换目标<select value={ems} onChange={(event) => void updateEms(event.target.value)}>{emsOptions.map((option) => <option value={option} key={option}>{option}</option>)}</select></label> : null}</div><div className="strategy-ring"><span>EMS</span><strong>LIVE</strong></div></section><section className="surface-card schedule-card"><div className="section-title"><div><span className="eyebrow">SCHEDULE 01</span><h2>计划时段 1</h2></div><button className={`toggle ${enabled ? "on" : ""}`} onClick={() => void updateEnabled(!enabled)} aria-label="切换计划1"><span /></button></div><div className="schedule-fields"><label>开始时间<input type="time" value={start} onChange={(event) => setStart(event.target.value)} /></label><label>结束时间<input type="time" value={end} onChange={(event) => setEnd(event.target.value)} /></label><label>功率参考<input type="number" value={power} onChange={(event) => setPower(Number(event.target.value))} min="0" max="100" /><small>% 额定功率</small></label></div><div className="mode-actions"><button className={findEntity(hass, "period1Mode")?.state === "charge" ? "selected gold" : ""} onClick={() => void updateMode("charge")}><ArrowDownToLine size={17} />充电</button><button className={findEntity(hass, "period1Mode")?.state === "discharge" ? "selected violet" : ""} onClick={() => void updateMode("discharge")}><ArrowUpFromLine size={17} />放电</button><button className="save-plan" onClick={() => void savePlan()} disabled={pending}>保存计划</button></div></section><div className="strategy-grid"><div className="surface-card compact-card"><span className="eyebrow">SOC LIMITS</span><h3>电池保护边界</h3><div className="setting-row"><span>充电上限</span><b>— %</b></div><div className="setting-row"><span>并网备电</span><b>— %</b></div></div><div className="surface-card compact-card"><span className="eyebrow">MORE PERIODS</span><h3>计划时段 2–4</h3><p>根据设备能力显示，当前页面保留四段计划的扩展位。</p></div></div></>;
}

function AlarmCard({ alarm }: { alarm: AlarmItem }) { const active = alarm.state === "on"; return <div className={`alarm-row ${active ? "active" : ""}`}><span className={`alarm-icon ${active ? "danger" : "ok"}`}>{active ? <AlertTriangle size={17} /> : <CheckCircle2 size={17} />}</span><div><strong>{alarm.label}</strong><small>{active ? alarm.issues.join(" · ") || `故障码 ${alarm.code ?? "—"}` : "未检测到问题"}</small></div><b>{active ? "处理中" : "正常"}</b></div>; }
function AlertsPage({ hass }: { hass: Hass }) {
  const alarms = useMemo(() => alarmItems(hass), [hass]);
  const active = alarms.filter((item) => item.state === "on").length;
  const [events, setEvents] = useState<AlarmEvent[]>([]);
  const [days, setDays] = useState(7);
  const [historyError, setHistoryError] = useState(false);
  useEffect(() => {
    if (!hass.callWS) return;
    const entityIds = Object.keys(hass.states).filter((id) =>
      ["bms_alarm", "bms_protection", "inverter_fault", "inverter_warning"].some((key) => id.endsWith(`_${key}`)),
    );
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    setHistoryError(false);
    void hass.callWS({ type: "logbook/get_events", start_time: start.toISOString(), end_time: end.toISOString(), entity_ids: entityIds })
      .then((result) => {
        const raw = Array.isArray(result) ? result : (result && typeof result === "object" && Array.isArray((result as { events?: unknown }).events) ? (result as { events: unknown[] }).events : []);
        setEvents(raw.filter((item): item is AlarmEvent => typeof item === "object" && item !== null).map((item) => {
          const data = item.data && typeof item.data === "object" ? item.data : {};
          return { ...data, ...item } as AlarmEvent;
        }).filter((item) => item.category || item.entity_id?.includes("bms_alarm") || item.entity_id?.includes("bms_protection")));
      })
      .catch(() => setHistoryError(true));
  }, [hass, days]);
  return <><PageHeader eyebrow="SAFETY & EVENTS" title="告警中心" description={active ? `${active} 项问题需要关注。` : "系统当前没有未处理的故障或警告。"} action={<span className={`alert-count ${active ? "has-alert" : ""}`}>{active} 当前告警</span>} /><section className="surface-card alarm-card"><div className="section-title"><div><span className="eyebrow">CURRENT STATUS</span><h2>当前状态</h2></div><ShieldCheck size={18} /></div>{alarms.map((alarm) => <AlarmCard key={alarm.id} alarm={alarm} />)}</section><section className="surface-card history-card"><div className="section-title"><div><span className="eyebrow">EVENT HISTORY</span><h2>历史事件</h2></div><div className="range-tabs"><button className={days === 1 ? "active" : ""} onClick={() => setDays(1)}>24小时</button><button className={days === 7 ? "active" : ""} onClick={() => setDays(7)}>7天</button><button className={days === 30 ? "active" : ""} onClick={() => setDays(30)}>30天</button></div></div>{historyError ? <div className="empty-note"><AlertTriangle size={18} />无法读取 HA Logbook，请稍后重试。</div> : events.length === 0 ? <div className="empty-note"><CheckCircle2 size={18} />当前时间范围内没有告警事件。</div> : <div className="alarm-history-list">{events.map((event, index) => <div className="alarm-history-row" key={`${event.timestamp ?? event.when ?? "event"}-${index}`}><div><strong>{event.issues?.join(" · ") || event.message || event.category || "FH3X 告警"}</strong><small>{event.timestamp ?? event.when ?? "—"} · {event.status === "recovered" ? "已恢复" : event.status === "startup" ? "启动时检测到" : event.status === "updated" ? "告警更新" : "已触发"}</small></div><b>{event.category ?? "FH3X"}</b></div>)}</div>}</section></>;
}

function DiagnosticsPage({ hass }: { hass: Hass }) { return <><PageHeader eyebrow="ENGINEERING DATA" title="设备诊断" description="PCS、BMS 和通信链路的工程数据。" /><div className="metric-grid four"><MetricCard label="PCS" value={findEntity(hass, "inverterState")?.state ?? "—"} tone="cyan" icon={<Cpu size={17} />} /><MetricCard label="BMS" value={findEntity(hass, "batteryState")?.state ?? "—"} tone="violet" icon={<BatteryCharging size={17} />} /><MetricCard label="通信" value="在线" tone="cyan" icon={<Waves size={17} />} /><MetricCard label="协议" value="Modbus" unit="TCP" tone="blue" /></div><div className="diagnostic-grid"><section className="surface-card table-card"><div className="section-title"><div><span className="eyebrow">PCS MONITOR</span><h2>逆变器摘要</h2></div></div>{[["软件版本", "—"], ["最大输出", "— W"], ["R/S/T 电压", "— / — / — V"], ["频率", "— Hz"], ["故障位图", "0x00000000"]].map(([label, value]) => <div className="setting-row" key={label}><span>{label}</span><b>{value}</b></div>)}</section><section className="surface-card table-card"><div className="section-title"><div><span className="eyebrow">BMS SUMMARY</span><h2>电池管理系统</h2></div></div>{[["SOC", `${value(hass, "batterySoc") ?? "—"}%`], ["SOH", `${findEntity(hass, "bmsSoh")?.state ?? "—"}%`], ["循环次数", findEntity(hass, "bmsCycles")?.state ?? "—"], ["总电压", `${findEntity(hass, "bmsVoltage")?.state ?? "—"} V`], ["模块 / 电芯", "— / —"]].map(([label, value]) => <div className="setting-row" key={label}><span>{label}</span><b>{value}</b></div>)}</section></div></>; }

function SettingsPage({ dark, reducedMotion, onTheme, onMotion }: { dark: boolean; reducedMotion: boolean; onTheme: () => void; onMotion: () => void }) { return <><PageHeader eyebrow="CONSOLE SETTINGS" title="设置" description="调整这块屏幕的显示方式，不改变设备控制参数。" /><section className="surface-card settings-card"><div className="setting-row"><div><strong>外观主题</strong><small>{dark ? "深色 · 石墨灰表面" : "浅色 · 雾白表面"}</small></div><button className="setting-action" onClick={onTheme}>{dark ? <Moon size={17} /> : <Sun size={17} />}切换主题</button></div><div className="setting-row"><div><strong>减少动态效果</strong><small>保留方向和状态，停止能量流循环动画</small></div><button className={`toggle ${reducedMotion ? "on" : ""}`} onClick={onMotion} aria-label="减少动态效果"><span /></button></div><div className="setting-row"><div><strong>数据刷新</strong><small>跟随 HA 集成轮询周期，实时状态由 WebSocket 推送</small></div><b>10 s</b></div><div className="setting-row"><div><strong>设备连接</strong><small>BMS 地址 1 · PCS 地址 2 · 本地 Modbus TCP</small></div><span className="status-pill status-online"><span className="status-dot" />本地</span></div></section><section className="surface-card settings-card"><div className="section-title"><div><span className="eyebrow">CAPABILITIES</span><h2>可选节点</h2></div><Settings2 size={18} /></div><div className="empty-note"><PanelTop size={18} />充电桩、发电机等节点将在对应 HA 实体接入后自动显示。</div></section></>; }

export function App({ hass: injectedHass }: { hass?: Hass }) {
  const hass = injectedHass ?? fallbackHass;
  const [page, setPage] = useState<PageKey>("overview");
  const [dark, setDark] = useState(() => localStorage.getItem("fh3x-theme") === "dark");
  const [reducedMotion, setReducedMotion] = useState(() => localStorage.getItem("fh3x-reduced-motion") === "true");
  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; localStorage.setItem("fh3x-theme", dark ? "dark" : "light"); }, [dark]);
  useEffect(() => { document.documentElement.dataset.motion = reducedMotion ? "reduced" : "full"; localStorage.setItem("fh3x-reduced-motion", String(reducedMotion)); }, [reducedMotion]);
  const activeAlarmCount = alarmItems(hass).filter((alarm) => alarm.state === "on").length;
  const content = {
    overview: <OverviewPage hass={hass} reducedMotion={reducedMotion} />,
    solar: <SolarPage hass={hass} />,
    battery: <BatteryPage hass={hass} />,
    load: <LoadPage hass={hass} />,
    grid: <GridPage hass={hass} />,
    strategy: <StrategyPage hass={hass} />,
    alerts: <AlertsPage hass={hass} />,
    diagnostics: <DiagnosticsPage hass={hass} />,
    settings: <SettingsPage dark={dark} reducedMotion={reducedMotion} onTheme={() => setDark((value) => !value)} onMotion={() => setReducedMotion((value) => !value)} />,
  }[page];
  return <div className="console-shell"><aside className="console-sidebar"><div className="brand-lockup"><div className="brand-mark">F<span>H</span></div><div><strong>FH3X</strong><small>ENERGY CONSOLE</small></div></div><div className="sidebar-status"><span className="status-dot" />LOCAL SYSTEM <span>·</span> 3402</div><nav className="main-nav">{navItems.map(({ key, label, icon: Icon }) => <button className={page === key ? "active" : ""} onClick={() => setPage(key)} key={key}><Icon size={18} /><span>{label}</span>{key === "alerts" && activeAlarmCount > 0 ? <b className="nav-badge">{activeAlarmCount}</b> : null}</button>)}</nav><div className="sidebar-foot"><button className={page === "settings" ? "active" : ""} onClick={() => setPage("settings")}><Settings2 size={18} /><span>设置</span></button><div className="sidebar-footnote">LOCAL MODBUS<br /><span>NO CLOUD REQUIRED</span></div></div></aside><main className="console-main"><div className="mobile-topbar"><div className="brand-lockup"><div className="brand-mark">F<span>H</span></div><strong>FH3X</strong></div><button onClick={() => setPage("settings")} aria-label="打开设置"><Settings2 size={20} /></button></div><div className="content-wrap">{content}</div><footer className="console-footer"><span>FH3X ENERGY CONSOLE <b>0.1.0</b></span><span>最后同步 {new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</span></footer></main></div>;
}
