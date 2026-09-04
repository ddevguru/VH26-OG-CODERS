"use client";

import React, { useState } from "react";
import { X, CheckCircle, AlertOctagon, HelpCircle, Code, Sparkles, CheckCheck } from "lucide-react";
import { FindingItem, api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

interface FindingDetailModalProps {
  finding: FindingItem | null;
  onClose: () => void;
  onStatusUpdated?: (updated: FindingItem) => void;
}

export const FindingDetailModal: React.FC<FindingDetailModalProps> = ({
  finding,
  onClose,
  onStatusUpdated,
}) => {
  const [updating, setUpdating] = useState(false);
  const [remediating, setRemediating] = useState(false);
  const [aiData, setAiData] = useState<any>(null);
  const [patchApplied, setPatchApplied] = useState(false);

  if (!finding) return null;

  const handleUpdateStatus = async (newStatus: string) => {
    try {
      setUpdating(true);
      const updated = await api.updateFindingStatus(finding.id, newStatus);
      if (onStatusUpdated) onStatusUpdated(updated);
    } catch (e) {
      alert(`Failed to update status: ${(e as Error).message}`);
    } finally {
      setUpdating(false);
    }
  };

  const handleTriggerAIRemediation = async () => {
    try {
      setRemediating(true);
      const res = await api.request<any>(`/findings/${finding.id}/remediate`, { method: "POST" });
      setAiData(res);
    } catch (e) {
      alert(`AI Remediation Error: ${(e as Error).message}`);
    } finally {
      setRemediating(false);
    }
  };

  const handleApplyPatch = async () => {
    try {
      setUpdating(true);
      const updated = await api.request<FindingItem>(`/findings/${finding.id}/apply-patch`, {
        method: "POST",
        body: JSON.stringify({ approved: true }),
      });
      setPatchApplied(true);
      if (onStatusUpdated) onStatusUpdated(updated);
    } catch (e) {
      alert(`Apply Patch Error: ${(e as Error).message}`);
    } finally {
      setUpdating(false);
    }
  };

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

  const ownership = finding.classification === "DEFINITE_LEAK" ? "OWNED (Leaked on Return/Exit)" : "BORROWED (Unbounded Lifetime)";
  const remediation = finding.description || "Enclose resource initialization inside a standard context manager ('with' or 'async with') to guarantee cleanup across all execution paths.";

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#0e1626] border border-gray-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-[#11192e]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-950/60 text-red-400 border border-red-800/40 rounded-lg">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">{finding.title}</h2>
              <p className="text-xs text-gray-400 font-mono">Rule: {finding.rule_id} • Fingerprint: {finding.fingerprint}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm">
          {/* Status Badges Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-gray-900/60 border border-gray-800">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Severity</span>
                <StatusBadge text={finding.severity} type="severity" />
              </div>
              <div>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Confidence</span>
                <StatusBadge text={finding.confidence} type="confidence" />
              </div>
              <div>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Classification</span>
                <StatusBadge text={finding.classification} type="classification" />
              </div>
              <div>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-semibold">Current Status</span>
                <StatusBadge text={finding.status} type="status" />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={remediating}
                onClick={handleTriggerAIRemediation}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/30 transition-all"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {remediating ? "Synthesizing AI Fix..." : "AI Remediation Fix"}
              </button>
              <button
                disabled={updating || finding.status === "RESOLVED"}
                onClick={() => handleUpdateStatus("RESOLVED")}
                className="px-3 py-1.5 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 hover:bg-emerald-900/60 text-xs font-semibold disabled:opacity-40 transition-all"
              >
                Mark Resolved
              </button>
            </div>
          </div>

          {/* AI Remediation Panel if active */}
          {aiData && (
            <div className="p-5 rounded-xl bg-indigo-950/40 border border-indigo-800/60 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-indigo-300 font-bold text-sm">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>AI Patch Proposal & 9-Step AST Validation</span>
                </div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-indigo-900/80 text-indigo-200">
                  {aiData.provider}
                </span>
              </div>

              <div className="text-xs text-gray-300 space-y-1">
                <p><span className="font-semibold text-gray-400">Explanation:</span> {aiData.explanation}</p>
                <p><span className="font-semibold text-gray-400">Suggested Fix:</span> {aiData.suggested_fix}</p>
              </div>

              {aiData.validation_report?.is_valid ? (
                <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 text-xs font-semibold flex items-center gap-2">
                  <CheckCheck className="w-4 h-4" />
                  <span>Validated by LeakGuard AST Engine (Target leak cleared, 0 new leaks introduced)</span>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-red-950/60 border border-red-800/60 text-red-400 text-xs font-semibold">
                  Validation Failed: {aiData.validation_report?.failure_reason}
                </div>
              )}

              {aiData.validation_report?.unified_diff && (
                <div>
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-1">Unified Diff Preview</span>
                  <pre className="p-3 rounded-lg bg-gray-950 border border-gray-800 font-mono text-xs text-emerald-400 overflow-x-auto">
                    {aiData.validation_report.unified_diff}
                  </pre>
                </div>
              )}

              {aiData.validation_report?.is_valid && !patchApplied && (
                <div className="flex justify-end pt-1">
                  <button
                    disabled={updating}
                    onClick={handleApplyPatch}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/30 transition-all flex items-center gap-1.5"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Apply Verified AI Patch (Human Approval)
                  </button>
                </div>
              )}

              {patchApplied && (
                <p className="text-xs font-bold text-emerald-400 text-right">✓ Patch Applied Successfully!</p>
              )}
            </div>
          )}

          {/* Grid Layout for Required Sections */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* WHAT & WHY */}
            <div className="p-4 rounded-xl bg-gray-900/40 border border-gray-800/80 space-y-3">
              <div>
                <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">WHAT</span>
                <p className="text-gray-200 font-medium mt-1">{finding.title}</p>
              </div>

              <div>
                <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">WHY</span>
                <p className="text-gray-300 text-xs mt-1 leading-relaxed">
                  The static analyzer identified an unclosed resource handle acquired along control-flow branches without a matching release call or context manager exit.
                </p>
              </div>
            </div>

            {/* WHERE & PATH */}
            <div className="p-4 rounded-xl bg-gray-900/40 border border-gray-800/80 space-y-3">
              <div>
                <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">WHERE / PATH</span>
                <div className="mt-1 font-mono text-xs text-emerald-400 bg-gray-950 p-2.5 rounded-lg border border-gray-800 flex items-center gap-2">
                  <Code className="w-4 h-4 text-emerald-500" />
                  <span>{finding.file_path}:{finding.line_number}</span>
                </div>
              </div>

              <div>
                <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block">RESOURCE & OWNERSHIP</span>
                <div className="mt-1 space-y-1 text-xs text-gray-300">
                  <p><span className="text-gray-400 font-semibold">Resource Type:</span> {resourceType}</p>
                  <p><span className="text-gray-400 font-semibold">Ownership State:</span> {ownership}</p>
                </div>
              </div>
            </div>
          </div>

          {/* REMEDIATION */}
          <div className="p-4 rounded-xl bg-gray-900/60 border border-indigo-900/40 space-y-2">
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block">REMEDIATION GUIDANCE</span>
            <p className="text-xs text-gray-300 leading-relaxed">{remediation}</p>
            <div className="bg-gray-950 p-3 rounded-lg border border-gray-800 text-xs font-mono text-gray-300 mt-2">
              <span className="text-gray-400"># Recommended Fix Pattern</span>
              <p className="text-emerald-400 mt-1">with open("{finding.file_path.split("/").pop() || "resource"}", "r") as handle:</p>
              <p className="text-gray-400 pl-4"># Safely perform resource operations</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-800 bg-[#11192e] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-semibold text-gray-200 transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
