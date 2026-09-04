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
  let trendColor = "text-slate-600 bg-slate-100 border-slate-200";
  if (trendType === "positive") trendColor = "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (trendType === "negative") trendColor = "text-rose-700 bg-rose-50 border-rose-200";

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl p-6 flex flex-col justify-between shadow-xs hover:border-emerald-300 hover:shadow-md transition-all duration-200 group cursor-pointer">
      <div className="flex items-center justify-between">
        <span className="text-xs font-extrabold text-slate-500 uppercase tracking-wider">{title}</span>
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 group-hover:scale-110 group-hover:bg-emerald-100 group-hover:border-emerald-300 transition-all duration-200 shadow-2xs">
          <Icon className="w-5 h-5 text-emerald-600 group-hover:text-emerald-700 transition-colors" />
        </div>
      </div>

      <div className="mt-4">
        <div className="text-3xl font-black text-slate-900 tracking-tight font-mono-code">{value}</div>
        {(subtitle || trend) && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            {trend && (
              <span className={`px-2.5 py-0.5 rounded-full font-bold border text-[11px] ${trendColor}`}>
                {trend}
              </span>
            )}
            {subtitle && <span className="text-slate-500 font-semibold">{subtitle}</span>}
          </div>
        )}
      </div>
    </div>
  );
};

