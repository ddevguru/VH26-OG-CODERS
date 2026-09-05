"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Shield, AlertTriangle, CheckCircle, Clock, GitBranch, GitCommit,
  ChevronDown, ChevronUp, Loader2, FileCode, Zap, X, Check, Info
} from "lucide-react";
import { api } from "@/lib/api";

const CLASSIFICATION_CONFIG: Record<string, any> = {
  DEFINITE_LEAK: { label: "DEFINITE RESOURCE LEAK", emoji: "🔴", color: "text-red-700 bg-red-50 border-red-200" },
  POTENTIAL_LEAK: { label: "POTENTIAL RESOURCE LEAK", emoji: "🟠", color: "text-amber-700 bg-amber-50 border-amber-200" },
  SAFE: { label: "SAFE", emoji: "🟢", color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  UNKNOWN: { label: "UNKNOWN", emoji: "⚪", color: "text-slate-600 bg-slate-50 border-slate-200" },
};

const PR_STATUS_CONFIG: Record<string, any> = {
  FAIL: { label: "FAILED", emoji: "❌", bg: "bg-red-600", text: "text-white" },
  WARNING: { label: "WARNING", emoji: "⚠️", bg: "bg-amber-500", text: "text-white" },
  PASS: { label: "PASSED", emoji: "✅", bg: "bg-emerald-600", text: "text-white" },
  UNKNOWN: { label: "PENDING", emoji: "⏳", bg: "bg-slate-400", text: "text-white" },
};

function RiskGauge({ score }: { score: number }) {
  const color = score >= 80 ? "#dc2626" : score >= 60 ? "#ea580c" : score >= 40 ? "#d97706" : score >= 20 ? "#ca8a04" : "#059669";
  const label = score >= 80 ? "CRITICAL" : score >= 60 ? "HIGH" : score >= 40 ? "MEDIUM" : score >= 20 ? "LOW" : "MINIMAL";
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#e2e8f0" strokeWidth="10" />
          <circle
            cx="50" cy="50" r="40" fill="none" stroke={color} strokeWidth="10"
            strokeDasharray={`${(score / 100) * 251.2} 251.2`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-black text-slate-900">{score}</span>
          <span className="text-[9px] font-extrabold text-slate-500 uppercase">/100</span>
        </div>
      </div>
      <span className="text-xs font-extrabold mt-1" style={{ color }}>{label}</span>
    </div>
  );
}

function FindingCard({ finding, prScanId, onFixGenerated }: { finding: any; prScanId: string; onFixGenerated: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [fix, setFix] = useState<any>(null);
  const [committing, setCommitting] = useState(false);
  const [committed, setCommitted] = useState(false);
  const [sourceCode, setSourceCode] = useState("");
  const [sourceLoading, setSourceLoading] = useState(false);
  const [localAiExp, setLocalAiExp] = useState<any>(finding.ai_explanation || {});

  const cfg = CLASSIFICATION_CONFIG[finding.classification] || CLASSIFICATION_CONFIG.UNKNOWN;
  const aiExp = localAiExp;

  useEffect(() => {
    if (expanded && !sourceCode && finding.file_path) {
      setSourceLoading(true);
      api.getGitHubFindingSource(prScanId, finding.id)
        .then((data) => setSourceCode(data.source_code || ""))
        .catch(() => {})
        .finally(() => setSourceLoading(false));
    }
  }, [expanded, prScanId, finding.id, finding.file_path, sourceCode]);

  const handleExplain = async () => {
    setExplaining(true);
    try {
      const result = await api.explainGitHubFinding(prScanId, finding.id);
      setLocalAiExp(result.ai_explanation || {});
    } catch (e: any) {
      alert(`Explain failed: ${e.message}`);
    } finally {
      setExplaining(false);
    }
  };

  const handleGenerateFix = async () => {
    setGenerating(true);
    try {
      const result = await api.generateGitHubFix(prScanId, finding.id, {
        strategy: aiExp.recommended_strategy || "try_finally",
        source_code: sourceCode || undefined,
      });
      setFix(result);
    } catch (e: any) {
      alert(`Fix generation failed: ${e.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleCommit = async () => {
    if (!fix || !fix.is_verified) return;
    setCommitting(true);
    try {
      await api.commitGitHubFix(prScanId, finding.id, { fix_candidate_id: fix.fix_candidate_id });
      setCommitted(true);
      onFixGenerated();
    } catch (e: any) {
      alert(`Commit failed: ${e.message}`);
    } finally {
      setCommitting(false);
    }
  };

  return (
    <div className={`bg-white border rounded-2xl overflow-hidden ${finding.classification === "DEFINITE_LEAK" ? "border-red-200" : finding.classification === "POTENTIAL_LEAK" ? "border-amber-200" : "border-slate-200"}`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between gap-4 text-left hover:bg-slate-50 transition"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`px-2 py-1 rounded-lg text-[10px] font-extrabold border whitespace-nowrap ${cfg.color}`}>
            {cfg.emoji} {cfg.label}
          </span>
          <div className="min-w-0">
            <div className="text-xs font-extrabold text-slate-900 truncate">
              <code className="text-emerald-700">{finding.file_path}</code>
              <span className="text-slate-400 font-semibold">:{finding.line_number}</span>
            </div>
            <div className="text-[11px] text-slate-500 font-semibold truncate">
              Resource: <code>{finding.resource_variable}</code> ({finding.resource_type})
            </div>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" /> : <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />}
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-slate-100 p-5 space-y-5">
          {/* Problem */}
          <div>
            <p className="text-[11px] font-extrabold text-slate-700 uppercase tracking-wider mb-1">Problem</p>
            <p className="text-xs text-slate-700 font-semibold">{finding.message}</p>
          </div>

          {/* AI Explanation */}
          {(aiExp.summary || finding.classification !== "SAFE") && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
              <p className="text-[11px] font-extrabold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-emerald-600" /> AI Analysis
                <span className="text-[9px] font-semibold text-slate-400 normal-case">explanatory only — deterministic classification preserved</span>
              </p>
              {aiExp.summary ? (
                <>
                  <p className="text-xs text-slate-700"><strong>Summary:</strong> {aiExp.summary}</p>
                  {aiExp.root_cause && <p className="text-xs text-slate-700"><strong>Root Cause:</strong> {aiExp.root_cause}</p>}
                  {aiExp.impact && <p className="text-xs text-slate-600"><strong>Impact:</strong> {aiExp.impact}</p>}
                  {aiExp.recommended_strategy && (
                    <p className="text-xs text-slate-600">
                      <strong>Strategy:</strong> <code className="bg-slate-100 px-1 rounded">{aiExp.recommended_strategy}</code>
                    </p>
                  )}
                </>
              ) : (
                <button
                  onClick={handleExplain}
                  disabled={explaining}
                  className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-[11px] font-bold rounded-lg transition cursor-pointer disabled:opacity-50"
                >
                  {explaining ? "Generating..." : "💡 Explain Root Cause"}
                </button>
              )}
            </div>
          )}

          {/* Source code (auto-fetched from GitHub) */}
          {!fix && (
            <div>
              <label className="block text-[11px] font-extrabold text-slate-700 uppercase tracking-wider mb-1.5">
                Source file {sourceLoading ? "(loading from GitHub...)" : "(auto-fetched from GitHub)"}:
              </label>
              <textarea
                value={sourceCode}
                onChange={(e) => setSourceCode(e.target.value)}
                rows={6}
                placeholder={sourceLoading ? "Fetching source..." : `# ${finding.file_path}`}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-300 text-[11px] font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-slate-50"
              />
            </div>
          )}

          {/* Fix Panel */}
          {fix ? (
            <div className={`rounded-xl border p-4 space-y-3 ${fix.is_verified ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"}`}>
              <div className="flex items-center justify-between">
                <p className="text-xs font-extrabold text-slate-900">
                  {fix.is_verified ? "✅ Verified Fix Ready" : "❌ Fix Rejected"}
                </p>
                <span className="text-[10px] font-bold text-slate-500">Strategy: {fix.strategy}</span>
              </div>

              {fix.is_verified && (
                <>
                  <div>
                    <p className="text-[11px] font-extrabold text-slate-700 mb-1.5">Verification Steps:</p>
                    {(fix.verification_steps || []).map((s: string, i: number) => (
                      <div key={i} className="flex items-start gap-1.5 text-[11px] text-emerald-700 font-semibold">
                        <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {s}
                      </div>
                    ))}
                  </div>
                  <p className="text-[11px] font-semibold text-slate-600">
                    Before: 🔴 DEFINITE_LEAK → After: 🟢 SAFE
                  </p>
                </>
              )}

              {fix.rejected_reason && (
                <p className="text-xs text-red-700 font-semibold">{fix.rejected_reason}</p>
              )}

              {fix.unified_diff && (
                <div>
                  <p className="text-[11px] font-extrabold text-slate-700 mb-1.5">Unified Diff:</p>
                  <pre className="bg-slate-900 text-slate-100 text-[10px] p-3 rounded-lg overflow-x-auto max-h-48">
                    {fix.unified_diff}
                  </pre>
                </div>
              )}

              {fix.is_verified && !committed && (
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={handleCommit}
                    disabled={committing}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold rounded-xl shadow-sm transition cursor-pointer disabled:opacity-50 flex items-center gap-2"
                  >
                    {committing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                    Apply Fix & Commit
                  </button>
                  <button
                    onClick={() => setFix(null)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition cursor-pointer"
                  >
                    Reject Fix
                  </button>
                </div>
              )}

              {committed && (
                <div className="flex items-center gap-2 text-xs text-emerald-700 font-extrabold">
                  <Check className="w-4 h-4" /> Fix committed! GitHub will trigger a re-scan.
                </div>
              )}
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={handleGenerateFix}
                disabled={generating}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold rounded-xl shadow-sm transition cursor-pointer disabled:opacity-50 flex items-center gap-2"
              >
                {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                {generating ? "Generating & Verifying..." : "🤖 Generate AI Fix"}
              </button>
            </div>
          )}

          <p className="text-[10px] text-slate-400 font-semibold">
            Finding ID: <code>{finding.finding_id}</code>
          </p>
        </div>
      )}
    </div>
  );
}

export default function PRDetailPage() {
  const params = useParams();
  const prScanId = params.id as string;

  const [scan, setScan] = useState<any>(null);
  const [findings, setFindings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.getGitHubPR(prScanId);
      setScan(data);
      setFindings(data.findings || []);
    } catch (e) {
      setScan(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [prScanId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
        <p className="text-xs text-slate-500 font-semibold">Loading PR review...</p>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-sm font-extrabold text-slate-700">PR scan not found</p>
      </div>
    );
  }

  const statusCfg = PR_STATUS_CONFIG[scan.pr_status || "UNKNOWN"] || PR_STATUS_CONFIG.UNKNOWN;
  const blockingFindings = findings.filter(f => f.classification !== "SAFE");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200/80 pb-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-3 py-1 rounded-xl text-xs font-extrabold ${statusCfg.bg} ${statusCfg.text}`}>
                {statusCfg.emoji} {statusCfg.label}
              </span>
              <h1 className="text-xl font-extrabold text-slate-900">
                PR #{scan.pr_number}
                {scan.pr_title && <span className="text-slate-500 font-semibold ml-2 text-sm">— {scan.pr_title}</span>}
              </h1>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500 font-semibold">
              <span className="flex items-center gap-1"><GitBranch className="w-3.5 h-3.5" />{scan.repo_full_name}</span>
              <span>→ {scan.pr_branch}</span>
              {scan.pr_author && <span>by {scan.pr_author}</span>}
              {scan.head_sha && <span className="flex items-center gap-1"><GitCommit className="w-3.5 h-3.5" /><code>{scan.head_sha.substring(0, 8)}</code></span>}
            </div>
          </div>
          <button onClick={load} className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-bold transition cursor-pointer">
            Refresh
          </button>
        </div>
      </div>

      {/* Risk + Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col items-center justify-center">
          <RiskGauge score={scan.risk_score || 0} />
          <p className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wide mt-2">Risk Score</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-center">
          <p className="text-3xl font-black text-red-600">{scan.definite_count || 0}</p>
          <p className="text-[10px] font-extrabold text-red-500 uppercase tracking-wide mt-1">🔴 Definite Leaks</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-center">
          <p className="text-3xl font-black text-amber-600">{scan.potential_count || 0}</p>
          <p className="text-[10px] font-extrabold text-amber-500 uppercase tracking-wide mt-1">🟠 Potential Leaks</p>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-center">
          <p className="text-3xl font-black text-emerald-600">{scan.safe_count || 0}</p>
          <p className="text-[10px] font-extrabold text-emerald-500 uppercase tracking-wide mt-1">🟢 Safe</p>
        </div>
      </div>

      {/* Scanned Files */}
      {scan.scanned_files?.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-4">
          <p className="text-[11px] font-extrabold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FileCode className="w-3.5 h-3.5 text-emerald-600" /> Scanned Files ({scan.scanned_files.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {scan.scanned_files.map((f: string) => (
              <span key={f} className="px-2 py-1 bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-semibold text-slate-600">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Findings */}
      <div>
        <h2 className="text-base font-extrabold text-slate-900 mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4 text-emerald-600" />
          Findings
          {blockingFindings.length > 0 && (
            <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-extrabold rounded-lg border border-red-200">
              {blockingFindings.length} blocking
            </span>
          )}
        </h2>

        {findings.length === 0 ? (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-8 text-center">
            <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="text-sm font-extrabold text-emerald-800">No resource leaks detected</p>
            <p className="text-xs text-emerald-600 mt-1">All resources properly managed on every execution path.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {findings.map((f) => (
              <FindingCard key={f.id} finding={f} prScanId={prScanId} onFixGenerated={load} />
            ))}
          </div>
        )}
      </div>

      {/* Info box */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex gap-3 text-xs text-slate-600 font-semibold">
        <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <p>
          <strong>Security note:</strong> Classifications (DEFINITE/POTENTIAL/SAFE) are determined exclusively by LeakGuard's
          deterministic AST/CFG analyzer. AI provides explanations and fix suggestions only — it cannot change the classification
          or risk score. Only verified fixes (re-scanned by LeakGuard) can be committed.
        </p>
      </div>
    </div>
  );
}
