export function StatusPill({ state, label }: { state: "online" | "stale" | "offline" | "normal" | "fault"; label: string }) {
  return <span className={`status-pill status-${state}`}><span className="status-dot" />{label}</span>;
}
