"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, AlertOctagon, Code, ShieldCheck, CheckCircle } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { api, FindingItem } from "@/lib/api";

export default function FindingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const findingId = params?.id as string;

  const [loading, setLoading] = useState(true);
  const [finding, setFinding] = useState<FindingItem | null>(null);

  useEffect(() => {
    if (!findingId) return;
    api
      .getFinding(findingId)
      .then(setFinding)
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [findingId]);

  if (loading) {
    return (
      <div className="p-12 text-center text-gray-400">
        <div className="animate-pulse space-y-4 max-w-xl mx-auto">
          <div className="h-8 bg-gray-800 rounded w-1/2 mx-auto"></div>
          <div className="h-4 bg-gray-800 rounded w-3/4 mx-auto"></div>
          <div className="h-32 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (!finding) {
    return (
      <div className="p-12 text-center text-gray-400 space-y-4">
        <AlertOctagon className="w-12 h-12 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Finding Not Found</h2>
        <p className="text-xs text-gray-400">The requested finding ID does not exist or has been removed.</p>
        <button
          onClick={() => router.push("/findings")}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
        >
          Back to Findings
        </button>
      </div>
    );
  }

  const resourceType = finding.rule_id.includes("FILE")
    ? "FILE"
    : finding.rule_id.includes("DB")
    ? "DATABASE"
    : finding.rule_id.includes("NET")
    ? "SOCKET"
    : finding.rule_id.includes("HTTP")
    ? "HTTP"
    : finding.rule_id.includes("PROC")
    ? "SUBPROCESS"
    : "RESOURCE";

  const ownership =
    finding.classification === "DEFINITE_LEAK"
      ? "OWNED (Definite Leak on Path Exit)"
      : "BORROWED (Potential Scope Escape)";

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <button
        onClick={() => router.push("/findings")}
        className="flex items-center gap-2 text-xs font-semibold text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Findings List
      </button>

      <div className="glass-card p-6 rounded-2xl border border-gray-800 space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
          <div>
            <span className="font-mono text-xs font-bold text-amber-400 block">{finding.rule_id}</span>
            <h1 className="text-2xl font-bold text-white mt-1">{finding.title}</h1>
            <p className="text-xs text-gray-400 font-mono mt-1">Fingerprint: {finding.fingerprint}</p>
          </div>

          <div className="flex items-center gap-2">
            <StatusBadge text={finding.severity} type="severity" />
            <StatusBadge text={finding.confidence} type="confidence" />
            <StatusBadge text={finding.status} type="status" />
          </div>
        </div>

        {/* 9 Required Sections Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-sm">
          {/* WHAT */}
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">WHAT</span>
            <p className="text-gray-200 font-semibold">{finding.title}</p>
          </div>

          {/* WHERE */}
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">WHERE</span>
            <div className="font-mono text-xs text-emerald-400 bg-gray-950 p-2 rounded border border-gray-800 flex items-center gap-2">
              <Code className="w-4 h-4 text-emerald-500" />
              <span>{finding.file_path}:{finding.line_number}</span>
            </div>
          </div>

          {/* WHY */}
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-1 md:col-span-2">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">WHY</span>
            <p className="text-xs text-gray-300 leading-relaxed">
              Resource handle acquired at line {finding.line_number} is not closed along all possible execution branches (e.g. early returns or unhandled exceptions).
            </p>
          </div>

          {/* RESOURCE & OWNERSHIP */}
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-2">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">RESOURCE & OWNERSHIP</span>
            <div className="text-xs text-gray-300 space-y-1">
              <p><span className="text-gray-400 font-semibold">Type:</span> {resourceType}</p>
              <p><span className="text-gray-400 font-semibold">Ownership:</span> {ownership}</p>
            </div>
          </div>

          {/* CONFIDENCE & SEVERITY */}
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 space-y-2">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">CONFIDENCE & SEVERITY</span>
            <div className="flex items-center gap-2">
              <StatusBadge text={finding.severity} type="severity" />
              <StatusBadge text={finding.confidence} type="confidence" />
            </div>
          </div>
        </div>

        {/* REMEDIATION */}
        <div className="p-5 rounded-xl bg-gray-900/80 border border-indigo-900/50 space-y-3">
          <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block flex items-center gap-2">
            <CheckCircle className="w-4 h-4" /> REMEDIATION CODE PATTERN
          </span>
          <p className="text-xs text-gray-300 leading-relaxed">
            {finding.description || "Refactor code to use context managers or try-finally blocks."}
          </p>
          <pre className="bg-gray-950 p-4 rounded-lg border border-gray-800 text-xs font-mono text-emerald-400 overflow-x-auto">
{`# Safe Context Manager Refactoring
with open("${finding.file_path.split("/").pop() || "resource"}", "r") as handle:
    # Process resource content safely
    pass`}
          </pre>
        </div>
      </div>
    </div>
  );
}
