"use client";

import React, { useState, useEffect } from "react";
import { X, CheckCircle, AlertOctagon, Code, Sparkles, CheckCheck, ShieldAlert, GitFork, Zap, Play } from "lucide-react";
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

  // Phase 16 State
  const [riskData, setRiskData] = useState<any>(null);
  const [ownershipData, setOwnershipData] = useState<any>(null);
  const [whatIfData, setWhatIfData] = useState<any>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState("context-manager");
  const [fixData, setFixData] = useState<any>(null);
  const [generatingFix, setGeneratingFix] = useState(false);

  useEffect(() => {
    if (!finding) return;
    // Fetch Phase 16 Risk Score & Ownership Graph
    api.getRiskScore(finding.id).then(setRiskData).catch(() => {});
    api.getOwnershipGraph(finding.id).then(setOwnershipData).catch(() => {});
  }, [finding]);

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

  const handleGenerateStrategyFix = async () => {
    try {
      setGeneratingFix(true);
      const defaultCode = `def process():\n    f = open('${finding.file_path.split("/").pop() || "resource.txt"}')\n    return f.read()\n`;
      const res = await api.generateAutoFix(finding.id, defaultCode, selectedStrategy);
      setFixData(res);
    } catch (e) {
      alert(`Auto Fix Error: ${(e as Error).message}`);
    } finally {
      setGeneratingFix(false);
    }
  };

  const handleRunWhatIf = async () => {
    try {
      setWhatIfLoading(true);
      const sampleCode = `def execute():\n    conn = connect()\n    cursor = conn.cursor()\n    res = cursor.execute()\n    return res\n`;
      const res = await api.runWhatIf(sampleCode, finding.line_number, finding.file_path);
      setWhatIfData(res);
    } catch (e) {
      alert(`What-If Error: ${(e as Error).message}`);
    } finally {
      setWhatIfLoading(false);
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
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="glass-card border border-white/[0.1] rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-8 py-5 border-b border-white/[0.08] flex items-center justify-between bg-[#080d18]/80">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.15)]">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">{finding.title}</h2>
              <p className="text-xs text-slate-400 font-mono-code">Rule: {finding.rule_id} • Fingerprint: {finding.fingerprint}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {riskData && (
              <div className="px-3.5 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-extrabold text-emerald-300">
                  Risk Score: {riskData.score}/100 ({riskData.level})
                </span>
              </div>
            )}
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-white/[0.06] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-8 overflow-y-auto space-y-6 text-xs">
          {/* Status Badges Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold mb-1">Severity</span>
                <StatusBadge text={finding.severity} type="severity" />
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold mb-1">Confidence</span>
                <StatusBadge text={finding.confidence} type="confidence" />
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold mb-1">Classification</span>
                <StatusBadge text={finding.classification} type="classification" />
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold mb-1">Current Status</span>
                <StatusBadge text={finding.status} type="status" />
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                disabled={remediating}
                onClick={handleTriggerAIRemediation}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-indigo-600/25 transition-all"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {remediating ? "Synthesizing AI Fix..." : "AI Remediation Fix"}
              </button>
              <button
                disabled={updating || finding.status === "RESOLVED"}
                onClick={() => handleUpdateStatus("RESOLVED")}
                className="px-3.5 py-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 text-xs font-bold disabled:opacity-40 transition-all"
              >
                Mark Resolved
              </button>
            </div>
          </div>

          {/* Phase 16: Resource Ownership Graph & Deterministic Risk Score */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Deterministic Risk Factors */}
            {riskData && (
              <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-extrabold text-amber-400 uppercase tracking-wider block">DETERMINISTIC RISK SCORE FACTORS</span>
                  <span className="text-xs font-mono-code font-bold text-emerald-400">{riskData.score} / 100</span>
                </div>
                <p className="text-slate-300 text-xs">{riskData.explanation}</p>
                <div className="space-y-1.5 pt-1">
                  {riskData.factors?.map((f: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-2 rounded-xl bg-[#060911] border border-white/[0.04]">
                      <span className="text-[11px] font-semibold text-slate-200">{f.name}</span>
                      <span className="text-[11px] font-mono-code text-amber-400 font-bold">+{f.score_contribution.toFixed(1)} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Resource Ownership Graph Preview */}
            {ownershipData && (
              <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                <div className="flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-cyan-400" />
                  <span className="text-[10px] font-extrabold text-cyan-400 uppercase tracking-wider block">RESOURCE OWNERSHIP GRAPH</span>
                </div>
                <div className="space-y-2">
                  <div className="text-[11px] font-bold text-slate-400 uppercase">Tracked Graph Nodes ({ownershipData.nodes?.length})</div>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {ownershipData.nodes?.map((node: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between p-2 rounded-xl bg-[#060911] border border-white/[0.04] text-[11px]">
                        <div className="font-mono-code text-slate-200">
                          <span className="font-bold text-indigo-400">{node.variable}</span> ({node.resource_type})
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${node.leak_status?.includes("LEAK") ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 text-emerald-300"}`}>
                          {node.state} ({node.leak_status})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Phase 16: Interactive Strategy Pattern Auto Fixer */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/20 to-indigo-950/20 border border-emerald-500/20 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                <Zap className="w-4 h-4 text-emerald-400" />
                <span>Strategy Pattern Auto Fixer & Deterministic Verification</span>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                  className="px-3 py-1.5 rounded-xl bg-[#060911] border border-slate-700 text-xs font-bold text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="context-manager">Context Manager ('with')</option>
                  <option value="try-finally">Try-Finally Block</option>
                  <option value="close-insertion">Explicit Close Insertion</option>
                  <option value="exception-safe">Exception Safe Cleanup</option>
                  <option value="async-cleanup">Async Context Manager</option>
                </select>

                <button
                  disabled={generatingFix}
                  onClick={handleGenerateStrategyFix}
                  className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-600/20"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {generatingFix ? "Verifying Strategy..." : "Synthesize Strategy Fix"}
                </button>
              </div>
            </div>

            {fixData && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-300">Verification Status:</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold ${fixData.is_verified ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/20 text-rose-400 border border-rose-500/30"}`}>
                    {fixData.verification_status} ({fixData.is_verified ? "Target Leak Cleared, 0 New Leaks Introduced" : fixData.rejected_reason})
                  </span>
                </div>

                {fixData.unified_diff && (
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Deterministic Verification Diff</span>
                    <pre className="p-4 rounded-xl bg-[#060911] border border-white/[0.06] font-mono-code text-xs text-emerald-400 overflow-x-auto">
                      {fixData.unified_diff || fixData.candidate_code}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Phase 16: What-If Static Exception Simulator */}
          <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-amber-400" />
                <span className="text-[10px] font-extrabold text-amber-400 uppercase tracking-wider block">WHAT-IF STATIC EXCEPTION SIMULATOR</span>
              </div>
              <button
                disabled={whatIfLoading}
                onClick={handleRunWhatIf}
                className="px-3 py-1 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 font-bold text-xs"
              >
                {whatIfLoading ? "Simulating..." : "Simulate Exception at Line"}
              </button>
            </div>

            {whatIfData && (
              <div className="space-y-2 pt-1 text-xs text-slate-300">
                <p><span className="font-bold text-slate-400">Location:</span> {whatIfData.source_location} ({whatIfData.function_name})</p>
                <p><span className="font-bold text-slate-400">Cleanup Guarantee:</span> <span className={whatIfData.cleanup_status === "GUARANTEED" ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>{whatIfData.cleanup_status}</span></p>
                <p><span className="font-bold text-slate-400">Explanation:</span> {whatIfData.explanation}</p>
              </div>
            )}
          </div>

          {/* AI Remediation Panel if active */}
          {aiData && (
            <div className="p-6 rounded-2xl bg-indigo-500/5 border border-indigo-500/20 space-y-4 shadow-inner">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-indigo-300 font-bold text-sm">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>AI Patch Proposal & 9-Step AST Validation</span>
                </div>
                <span className="text-[10px] font-mono-code font-bold px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-200">
                  {aiData.provider}
                </span>
              </div>

              <div className="text-xs text-slate-300 space-y-1.5">
                <p><span className="font-bold text-slate-400">Explanation:</span> {aiData.explanation}</p>
                <p><span className="font-bold text-slate-400">Suggested Fix:</span> {aiData.suggested_fix}</p>
              </div>

              {aiData.validation_report?.is_valid ? (
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center gap-2">
                  <CheckCheck className="w-4 h-4" />
                  <span>Validated by LeakGuard AST Engine (Target leak cleared, 0 new leaks introduced)</span>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-bold">
                  Validation Failed: {aiData.validation_report?.failure_reason}
                </div>
              )}

              {aiData.validation_report?.unified_diff && (
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Unified Diff Preview</span>
                  <pre className="p-4 rounded-xl bg-[#060911] border border-white/[0.06] font-mono-code text-xs text-emerald-400 overflow-x-auto">
                    {aiData.validation_report.unified_diff}
                  </pre>
                </div>
              )}

              {aiData.validation_report?.is_valid && !patchApplied && (
                <div className="flex justify-end pt-1">
                  <button
                    disabled={updating}
                    onClick={handleApplyPatch}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/25 transition-all flex items-center gap-2"
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* WHAT & WHY */}
            <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
              <div>
                <span className="text-[10px] font-extrabold text-indigo-400 uppercase tracking-wider block">WHAT</span>
                <p className="text-slate-100 font-bold text-sm mt-1">{finding.title}</p>
              </div>

              <div>
                <span className="text-[10px] font-extrabold text-indigo-400 uppercase tracking-wider block">WHY</span>
                <p className="text-slate-300 text-xs mt-1 leading-relaxed">
                  The static analyzer identified an unclosed resource handle acquired along control-flow branches without a matching release call or context manager exit.
                </p>
              </div>
            </div>

            {/* WHERE & PATH */}
            <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
              <div>
                <span className="text-[10px] font-extrabold text-indigo-400 uppercase tracking-wider block">WHERE / PATH</span>
                <div className="mt-1 font-mono-code text-xs text-emerald-400 bg-[#060911] p-3 rounded-xl border border-white/[0.06] flex items-center gap-2">
                  <Code className="w-4 h-4 text-emerald-500" />
                  <span>{finding.file_path}:{finding.line_number}</span>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-extrabold text-indigo-400 uppercase tracking-wider block">RESOURCE & OWNERSHIP</span>
                <div className="mt-1 space-y-1 text-xs text-slate-300">
                  <p><span className="text-slate-400 font-bold">Resource Type:</span> {resourceType}</p>
                  <p><span className="text-slate-400 font-bold">Ownership State:</span> {ownership}</p>
                </div>
              </div>
            </div>
          </div>

          {/* REMEDIATION */}
          <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2">
            <span className="text-[10px] font-extrabold text-emerald-400 uppercase tracking-wider block">REMEDIATION GUIDANCE</span>
            <p className="text-xs text-slate-300 leading-relaxed">{remediation}</p>
            <div className="bg-[#060911] p-4 rounded-xl border border-white/[0.06] text-xs font-mono-code text-slate-300 mt-2">
              <span className="text-slate-500"># Recommended Fix Pattern</span>
              <p className="text-emerald-400 mt-1">with open("{finding.file_path.split("/").pop() || "resource"}", "r") as handle:</p>
              <p className="text-slate-500 pl-4"># Safely perform resource operations</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-8 py-4 border-t border-white/[0.08] bg-[#080d18]/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-xs font-bold text-slate-200 transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
