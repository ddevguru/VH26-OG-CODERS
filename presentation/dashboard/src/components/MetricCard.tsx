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
  let trendColor = "text-gray-400";
  if (trendType === "positive") trendColor = "text-emerald-400";
  if (trendType === "negative") trendColor = "text-red-400";

  return (
    <div className="glass-card p-5 rounded-xl flex flex-col justify-between border border-gray-800/80 hover:border-gray-700/80 transition-all">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{title}</span>
        <div className="p-2 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-3">
        <div className="text-3xl font-extrabold text-white tracking-tight">{value}</div>
        {(subtitle || trend) && (
          <div className="mt-1 flex items-center gap-2 text-xs">
            {trend && <span className={`font-semibold ${trendColor}`}>{trend}</span>}
            {subtitle && <span className="text-gray-400">{subtitle}</span>}
          </div>
        )}
      </div>
    </div>
  );
};
