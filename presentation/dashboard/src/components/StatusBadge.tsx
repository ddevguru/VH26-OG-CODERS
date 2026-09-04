import React from "react";

interface StatusBadgeProps {
  text: string;
  type?: "severity" | "confidence" | "classification" | "status";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ text, type = "status" }) => {
  const upper = text.toUpperCase();

  let bgClass = "bg-slate-100 text-slate-700 border-slate-200";

  if (type === "severity") {
    if (upper === "CRITICAL" || upper === "ERROR") {
      bgClass = "bg-rose-50 text-rose-700 border-rose-200 shadow-2xs font-extrabold";
    } else if (upper === "WARNING") {
      bgClass = "bg-amber-50 text-amber-800 border-amber-200 shadow-2xs font-bold";
    } else {
      bgClass = "bg-sky-50 text-sky-800 border-sky-200 shadow-2xs font-bold";
    }
  } else if (type === "status") {
    if (upper === "OPEN" || upper === "FAILED") {
      bgClass = "bg-rose-50 text-rose-700 border-rose-200 shadow-2xs font-extrabold";
    } else if (upper === "RESOLVED" || upper === "PASSED") {
      bgClass = "bg-emerald-50 text-emerald-800 border-emerald-200 shadow-2xs font-extrabold";
    } else if (upper === "SUPPRESSED") {
      bgClass = "bg-slate-100 text-slate-600 border-slate-200 font-bold";
    }
  } else if (type === "classification") {
    if (upper === "DEFINITE_LEAK") {
      bgClass = "bg-rose-50 text-rose-700 border-rose-200 shadow-2xs font-extrabold";
    } else if (upper === "POTENTIAL_LEAK") {
      bgClass = "bg-amber-50 text-amber-800 border-amber-200 shadow-2xs font-bold";
    } else if (upper === "SAFE") {
      bgClass = "bg-emerald-50 text-emerald-800 border-emerald-200 shadow-2xs font-extrabold";
    }
  } else if (type === "confidence") {
    if (upper === "HIGH") {
      bgClass = "bg-purple-50 text-purple-800 border-purple-200 shadow-2xs font-extrabold";
    } else if (upper === "MEDIUM") {
      bgClass = "bg-teal-50 text-teal-800 border-teal-200 shadow-2xs font-bold";
    } else {
      bgClass = "bg-slate-100 text-slate-600 border-slate-200 font-bold";
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

