"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  CheckCircle,
  AlertOctagon,
  Code,
  Sparkles,
  CheckCheck,
  ShieldAlert,
  GitFork,
  Zap,
  Play,
  FileCode,
  Info,
  ShieldCheck,
  AlertTriangle,
  Cpu,
  Flame,
  Check
} from "lucide-react";
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
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200/90 rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header - Native Web App Brand Header Style */}
        <div className="px-8 py-5 border-b border-slate-200/80 bg-white flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200/80 flex items-center justify-center text-rose-600 shadow-2xs">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-slate-900 tracking-tight">{finding.title}</h2>
              <p className="text-xs text-slate-500 font-semibold mt-0.5 flex items-center gap-2">
                <span>Rule:</span>
                <span className="font-mono-code font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">{finding.rule_id}</span>
                <span>• Fingerprint:</span>
                <span className="font-mono-code text-slate-700 font-medium">{finding.fingerprint}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {riskData && (
              <div className="px-3.5 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 shadow-2xs">
                <ShieldAlert className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-extrabold text-emerald-900">
                  Risk Score: {riskData.score}/100 ({riskData.level})
                </span>
              </div>
            )}
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-700 rounded-xl hover:bg-slate-100 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body - Native Web App Ambient Background */}
        <div className="p-8 overflow-y-auto space-y-6 text-xs bg-[#f8fafc]">

          {/* Status Badges & Quick Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-white border border-slate-200/80 shadow-2xs">
            <div className="flex flex-wrap items-center gap-6">
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-extrabold mb-1.5">Severity</span>
                <StatusBadge text={finding.severity} type="severity" />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-extrabold mb-1.5">Confidence</span>
                <StatusBadge text={finding.confidence} type="confidence" />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-extrabold mb-1.5">Classification</span>
                <StatusBadge text={finding.classification} type="classification" />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-extrabold mb-1.5">Current Status</span>
                <StatusBadge text={finding.status} type="status" />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                disabled={remediating}
                onClick={handleTriggerAIRemediation}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white text-xs font-extrabold whitespace-nowrap shrink-0 inline-flex items-center gap-2 shadow-md shadow-emerald-600/20 transition cursor-pointer"
              >
                <Sparkles className="w-4 h-4 fill-white shrink-0" />
                <span>{remediating ? "Synthesizing AI Fix..." : "AI Remediation Fix"}</span>
              </button>
              <button
                disabled={updating || finding.status === "RESOLVED"}
                onClick={() => handleUpdateStatus("RESOLVED")}
                className="px-5 py-2.5 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100 text-xs font-extrabold whitespace-nowrap shrink-0 disabled:opacity-40 transition cursor-pointer"
              >
                Mark Resolved
              </button>
            </div>
          </div>

          {/* WHAT & WHY (HIGH CONTRAST NATIVE LIGHT TYPOGRAPHY) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* WHAT & WHY CARD */}
            <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-2xs space-y-4">
              <div>
                <span className="text-[11px] font-extrabold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-emerald-600" /> WHAT IS LEAKED
                </span>
                <p className="text-slate-900 font-extrabold text-sm mt-1.5 leading-snug">
                  {finding.title}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-200/80">
                <span className="text-[11px] font-extrabold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Flame className="w-3.5 h-3.5 text-amber-600" /> WHY IT HAPPENED
                </span>
                <p className="text-slate-700 font-semibold text-xs mt-1.5 leading-relaxed">
                  The static analyzer identified an unclosed resource handle acquired along control-flow branches without a matching release call or context manager exit.
                </p>
              </div>
            </div>

            {/* WHERE & OWNERSHIP CARD */}
            <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-2xs space-y-4">
              <div>
                <span className="text-[11px] font-extrabold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Code className="w-3.5 h-3.5 text-cyan-600" /> WHERE / LOCATION
                </span>
                <div className="mt-2 font-mono-code text-xs text-emerald-400 bg-[#060911] p-3.5 rounded-xl border border-slate-800 flex items-center gap-2 shadow-inner">
                  <FileCode className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="font-extrabold tracking-wide select-all">{finding.file_path}:{finding.line_number}</span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200/80">
                <span className="text-[11px] font-extrabold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-purple-600" /> RESOURCE & OWNERSHIP
                </span>
                <div className="mt-2 space-y-1.5 text-xs">
                  <p className="flex justify-between items-center bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-slate-800">
                    <span className="font-bold text-slate-600">Resource Type:</span> 
                    <span className="font-mono-code font-extrabold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-300 shadow-2xs">{resourceType}</span>
                  </p>
                  <p className="flex justify-between items-center bg-rose-50/60 p-2.5 rounded-xl border border-rose-200/80 text-rose-900">
                    <span className="font-bold text-rose-800">Ownership State:</span> 
                    <span className="font-extrabold text-rose-700 bg-rose-100 px-2 py-0.5 rounded border border-rose-300 shadow-2xs">{ownership}</span>
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Strategy Pattern Auto Fixer */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50/50 border border-emerald-200/80 space-y-4 shadow-2xs">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-emerald-950 font-black text-sm">
                <Zap className="w-4 h-4 text-emerald-600" />
                <span>Strategy Pattern Auto Fixer & Deterministic Verification</span>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                  className="px-3.5 py-2 rounded-xl bg-white border border-slate-300 text-xs font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-2xs"
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
                  className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 shadow-sm shadow-emerald-600/20 transition cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5 fill-white shrink-0" />
                  <span>{generatingFix ? "Verifying Strategy..." : "Synthesize Strategy Fix"}</span>
                </button>
              </div>
            </div>

            {fixData && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-white border border-emerald-200 shadow-2xs">
                  <span className="font-extrabold text-slate-800">Verification Status:</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-black ${
                    fixData.is_verified 
                      ? "bg-emerald-100 text-emerald-900 border border-emerald-300" 
                      : "bg-rose-100 text-rose-900 border border-rose-300"
                  }`}>
                    {fixData.verification_status} ({fixData.is_verified ? "Target Leak Cleared, 0 New Leaks Introduced" : fixData.rejected_reason})
                  </span>
                </div>

                {fixData.unified_diff && (
                  <div>
                    <span className="text-[10px] font-extrabold text-slate-600 uppercase tracking-wider block mb-1.5">Deterministic Verification Diff</span>
                    <pre className="p-4 rounded-xl bg-[#060911] border border-slate-800 font-mono-code text-xs text-emerald-400 overflow-x-auto shadow-inner">
                      {fixData.unified_diff || fixData.candidate_code}
                    </pre>
                  </div>
                )}

                {fixData.is_verified && (
                  <div className="flex justify-end pt-2">
                    <button
                      disabled={updating || patchApplied}
                      onClick={handleApplyPatch}
                      className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition cursor-pointer whitespace-nowrap shrink-0 flex items-center gap-2"
                    >
                      <CheckCircle className="w-4 h-4 text-white fill-current shrink-0" />
                      <span>{patchApplied ? "✓ Strategy Patch Applied & Marked Resolved" : "Apply Verified Strategy Fix"}</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Risk Factors & Ownership Graph */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {riskData && (
              <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-extrabold text-amber-800 uppercase tracking-wider block">DETERMINISTIC RISK SCORE FACTORS</span>
                  <span className="text-xs font-mono-code font-black text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded border border-emerald-300">{riskData.score} / 100</span>
                </div>
                <p className="text-slate-700 text-xs font-semibold">{riskData.explanation}</p>
                <div className="space-y-1.5 pt-1">
                  {riskData.factors?.map((f: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px]">
                      <span className="font-bold text-slate-800">{f.name}</span>
                      <span className="font-mono-code text-amber-700 font-bold">+{f.score_contribution.toFixed(1)} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Ownership Graph Nodes */}
            {ownershipData && (
              <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-2xs space-y-3">
                <div className="flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-cyan-600" />
                  <span className="text-[11px] font-extrabold text-cyan-800 uppercase tracking-wider block">RESOURCE OWNERSHIP GRAPH</span>
                </div>
                <div className="space-y-2">
                  <div className="text-[11px] font-extrabold text-slate-500 uppercase">Tracked Graph Nodes ({ownershipData.nodes?.length})</div>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                    {ownershipData.nodes?.map((node: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px]">
                        <div className="font-mono-code text-slate-900">
                          <span className="font-black text-emerald-700">{node.variable}</span> ({node.resource_type})
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-black ${
                          node.leak_status?.includes("LEAK") 
                            ? "bg-rose-100 text-rose-800 border border-rose-300" 
                            : "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        }`}>
                          {node.state} ({node.leak_status})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Static Exception Simulator */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-amber-600" />
                <span className="text-[11px] font-extrabold text-amber-800 uppercase tracking-wider block">WHAT-IF STATIC EXCEPTION SIMULATOR</span>
              </div>
              <button
                disabled={whatIfLoading}
                onClick={handleRunWhatIf}
                className="px-3.5 py-1.5 rounded-xl bg-amber-50 text-amber-900 border border-amber-300 hover:bg-amber-100 font-extrabold text-xs transition cursor-pointer"
              >
                {whatIfLoading ? "Simulating..." : "Simulate Exception at Line"}
              </button>
            </div>

            {whatIfData && (
              <div className="space-y-2 pt-1 text-xs p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-800">
                <p><span className="font-bold text-slate-600">Location:</span> {whatIfData.source_location} ({whatIfData.function_name})</p>
                <p><span className="font-bold text-slate-600">Cleanup Guarantee:</span> <span className={whatIfData.cleanup_status === "GUARANTEED" ? "text-emerald-700 font-extrabold" : "text-rose-700 font-extrabold"}>{whatIfData.cleanup_status}</span></p>
                <p><span className="font-bold text-slate-600">Explanation:</span> {whatIfData.explanation}</p>
              </div>
            )}
          </div>

          {/* AI Remediation Panel */}
          {aiData && (
            <div className="p-6 rounded-2xl bg-emerald-50/70 border border-emerald-200/80 space-y-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-950 font-black text-sm">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  <span>AI Patch Proposal & 9-Step AST Validation</span>
                </div>
                <span className="text-[10px] font-mono-code font-bold px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-900 border border-emerald-300">
                  {aiData.provider}
                </span>
              </div>

              <div className="text-xs text-slate-800 space-y-1.5">
                <p><span className="font-bold text-slate-600">Explanation:</span> {aiData.explanation}</p>
                <p><span className="font-bold text-slate-600">Suggested Fix:</span> {aiData.suggested_fix}</p>
              </div>

              {aiData.validation_report?.is_valid ? (
                <div className="p-3.5 rounded-xl bg-emerald-100 border border-emerald-300 text-emerald-900 text-xs font-bold flex items-center gap-2">
                  <CheckCheck className="w-4 h-4 text-emerald-700" />
                  <span>Validated by LeakGuard AST Engine (Target leak cleared, 0 new leaks introduced)</span>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-rose-100 border border-rose-300 text-rose-900 text-xs font-bold">
                  Validation Failed: {aiData.validation_report?.failure_reason}
                </div>
              )}

              {aiData.validation_report?.unified_diff && (
                <div>
                  <span className="text-[11px] font-extrabold text-slate-600 uppercase tracking-wider block mb-1.5">Unified Diff Preview</span>
                  <pre className="p-4 rounded-xl bg-[#060911] border border-slate-800 font-mono-code text-xs text-emerald-400 overflow-x-auto shadow-inner">
                    {aiData.validation_report.unified_diff}
                  </pre>
                </div>
              )}

              {aiData.validation_report?.is_valid && !patchApplied && (
                <div className="flex justify-end pt-1">
                  <button
                    disabled={updating}
                    onClick={handleApplyPatch}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition cursor-pointer flex items-center gap-2"
                  >
                    <CheckCircle className="w-4 h-4 text-white fill-current" />
                    Apply Verified AI Patch (Human Approval)
                  </button>
                </div>
              )}

              {patchApplied && (
                <p className="text-xs font-bold text-emerald-700 text-right flex items-center justify-end gap-1">
                  <Check className="w-4 h-4 text-emerald-700" /> Patch Applied Successfully!
                </p>
              )}
            </div>
          )}

          {/* REMEDIATION GUIDANCE */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-2xs space-y-2">
            <span className="text-[11px] font-extrabold text-emerald-800 uppercase tracking-wider block">
              🛠️ REMEDIATION GUIDANCE
            </span>
            <p className="text-xs text-slate-700 font-semibold leading-relaxed">{remediation}</p>
            <div className="bg-[#060911] p-4 rounded-xl border border-slate-800 text-xs font-mono-code text-slate-300 mt-2 shadow-inner">
              <span className="text-slate-500"># Recommended Fix Pattern</span>
              <p className="text-emerald-400 mt-1">with open("{finding.file_path.split("/").pop() || "resource"}", "r") as handle:</p>
              <p className="text-slate-500 pl-4"># Safely perform resource operations</p>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-8 py-4 border-t border-slate-200/80 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-xs font-extrabold text-slate-900 transition cursor-pointer"
          >
            Close Inspector
          </button>
        </div>

      </div>
    </div>
  );
};
