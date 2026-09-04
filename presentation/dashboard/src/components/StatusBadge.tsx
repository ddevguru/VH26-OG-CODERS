import React from "react";

interface StatusBadgeProps {
  text: string;
  type?: "severity" | "confidence" | "classification" | "status";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ text, type = "status" }) => {
  const upper = text.toUpperCase();

  let bgClass = "bg-gray-800 text-gray-300 border-gray-700";

  if (type === "severity") {
    if (upper === "CRITICAL" || upper === "ERROR") {
      bgClass = "bg-red-950/70 text-red-400 border-red-800/60";
    } else if (upper === "WARNING") {
      bgClass = "bg-amber-950/70 text-amber-400 border-amber-800/60";
    } else {
      bgClass = "bg-blue-950/70 text-blue-400 border-blue-800/60";
    }
  } else if (type === "status") {
    if (upper === "OPEN") {
      bgClass = "bg-red-950/60 text-red-400 border-red-800/40";
    } else if (upper === "RESOLVED") {
      bgClass = "bg-emerald-950/60 text-emerald-400 border-emerald-800/40";
    } else if (upper === "SUPPRESSED") {
      bgClass = "bg-gray-800 text-gray-400 border-gray-700";
    }
  } else if (type === "classification") {
    if (upper === "DEFINITE_LEAK") {
      bgClass = "bg-red-950/70 text-red-400 border-red-800/60";
    } else if (upper === "POTENTIAL_LEAK") {
      bgClass = "bg-amber-950/70 text-amber-400 border-amber-800/60";
    } else if (upper === "SAFE") {
      bgClass = "bg-emerald-950/70 text-emerald-400 border-emerald-800/60";
    }
  } else if (type === "confidence") {
    if (upper === "HIGH") {
      bgClass = "bg-purple-950/60 text-purple-400 border-purple-800/40";
    } else if (upper === "MEDIUM") {
      bgClass = "bg-blue-950/60 text-blue-400 border-blue-800/40";
    } else {
      bgClass = "bg-gray-800 text-gray-400 border-gray-700";
    }
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${bgClass}`}
    >
      {text}
    </span>
  );
};
