import React from "react";

interface StatusBadgeProps {
  text: string;
  type?: "severity" | "confidence" | "classification" | "status";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ text, type = "status" }) => {
  const upper = text.toUpperCase();

  let bgClass = "bg-slate-800/60 text-slate-300 border-slate-700/60 shadow-sm";

  if (type === "severity") {
    if (upper === "CRITICAL" || upper === "ERROR") {
      bgClass = "bg-rose-500/10 text-rose-400 border-rose-500/30 shadow-[0_0_12px_rgba(244,63,94,0.15)]";
    } else if (upper === "WARNING") {
      bgClass = "bg-amber-500/10 text-amber-400 border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.15)]";
    } else {
      bgClass = "bg-sky-500/10 text-sky-400 border-sky-500/30 shadow-[0_0_12px_rgba(14,165,233,0.15)]";
    }
  } else if (type === "status") {
    if (upper === "OPEN" || upper === "FAILED") {
      bgClass = "bg-rose-500/10 text-rose-400 border-rose-500/30 shadow-[0_0_12px_rgba(244,63,94,0.15)]";
    } else if (upper === "RESOLVED" || upper === "PASSED") {
      bgClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.15)]";
    } else if (upper === "SUPPRESSED") {
      bgClass = "bg-slate-800/80 text-slate-400 border-slate-700/60";
    }
  } else if (type === "classification") {
    if (upper === "DEFINITE_LEAK") {
      bgClass = "bg-rose-500/10 text-rose-400 border-rose-500/30 shadow-[0_0_12px_rgba(244,63,94,0.15)]";
    } else if (upper === "POTENTIAL_LEAK") {
      bgClass = "bg-amber-500/10 text-amber-400 border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.15)]";
    } else if (upper === "SAFE") {
      bgClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.15)]";
    }
  } else if (type === "confidence") {
    if (upper === "HIGH") {
      bgClass = "bg-purple-500/10 text-purple-400 border-purple-500/30 shadow-[0_0_12px_rgba(168,85,247,0.15)]";
    } else if (upper === "MEDIUM") {
      bgClass = "bg-indigo-500/10 text-indigo-400 border-indigo-500/30 shadow-[0_0_12px_rgba(99,102,241,0.15)]";
    } else {
      bgClass = "bg-slate-800/60 text-slate-400 border-slate-700/60";
    }
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${bgClass}`}
    >
      {text}
    </span>
  );
};
