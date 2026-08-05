import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  unit,
  trend,
  tone = "cyan",
  icon,
}: {
  label: string;
  value: string;
  unit?: string;
  trend?: string;
  tone?: "cyan" | "gold" | "violet" | "blue" | "red";
  icon?: ReactNode;
}) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <div className="metric-top"><span>{label}</span>{icon ? <span className="metric-icon">{icon}</span> : null}</div>
      <div className="metric-value">{value}<small>{unit}</small></div>
      {trend ? <div className="metric-trend">{trend}</div> : null}
    </article>
  );
}
