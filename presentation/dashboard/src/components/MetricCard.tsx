import React from "react";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: string;
  trendType?: "positive" | "negative" | "neutral";
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendType = "neutral",
}) => {
  let trendColor = "text-slate-400 bg-slate-500/10 border-slate-500/20";
  if (trendType === "positive") trendColor = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
  if (trendType === "negative") trendColor = "text-rose-400 bg-rose-500/10 border-rose-500/20";

  return (
    <div className="glass-card p-6 rounded-2xl flex flex-col justify-between group hover:-translate-y-0.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{title}</span>
        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform duration-200 shadow-[0_0_15px_rgba(99,102,241,0.15)]">
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-4">
        <div className="text-3xl font-extrabold text-white tracking-tight font-mono-code">{value}</div>
        {(subtitle || trend) && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            {trend && (
              <span className={`px-2 py-0.5 rounded-full font-bold border text-[11px] ${trendColor}`}>
                {trend}
              </span>
            )}
            {subtitle && <span className="text-slate-400 font-medium">{subtitle}</span>}
          </div>
        )}
      </div>
    </div>
  );
};
