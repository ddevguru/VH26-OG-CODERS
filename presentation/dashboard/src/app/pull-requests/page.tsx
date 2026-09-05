"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  GitPullRequest, Shield, AlertTriangle, CheckCircle, Clock,
  ExternalLink, RefreshCw, Plus, GitBranch, Zap
} from "lucide-react";
import { api } from "@/lib/api";

const STATUS_CONFIG = {
  FAIL: { color: "text-red-600 bg-red-50 border-red-200", emoji: "❌", label: "FAIL" },
  WARNING: { color: "text-amber-600 bg-amber-50 border-amber-200", emoji: "⚠️", label: "WARNING" },
  PASS: { color: "text-emerald-600 bg-emerald-50 border-emerald-200", emoji: "✅", label: "PASS" },
  UNKNOWN: { color: "text-slate-500 bg-slate-50 border-slate-200", emoji: "⏳", label: "PENDING" },
};

const RISK_COLOR = (score: number) => {
  if (score >= 80) return "text-red-600 bg-red-50 border-red-200";
  if (score >= 60) return "text-orange-600 bg-orange-50 border-orange-200";
  if (score >= 40) return "text-amber-600 bg-amber-50 border-amber-200";
  if (score >= 20) return "text-yellow-600 bg-yellow-50 border-yellow-200";
  return "text-emerald-600 bg-emerald-50 border-emerald-200";
};

export default function PullRequestsPage() {
  const [prs, setPrs] = useState<any[]>([]);
  const [repos, setRepos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectRepo, setConnectRepo] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectMsg, setConnectMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [prData, repoData] = await Promise.all([
        api.getGitHubPRs().catch(() => ({ items: [] })),
        api.getGitHubRepos().catch(() => []),
      ]);
      setPrs(prData.items || []);
      setRepos(repoData || []);
    } catch (e) {
      setPrs([]);
      setRepos([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connectRepo.trim()) return;
    setConnecting(true);
    try {
      const res = await api.connectGitHubRepo(connectRepo.trim());
      setConnectMsg(`✅ Connected: ${connectRepo}. Webhook active!`);
      setConnectRepo("");
      load();
    } catch (err: any) {
      setConnectMsg(`❌ ${err.message || "Failed to connect"}`);
    } finally {
      setConnecting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-slate-200/80 pb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <GitPullRequest className="w-6 h-6 text-emerald-600" />
            GitHub PR Reviews
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            CodeRabbit-style resource leak detection for every pull request. Powered by LeakGuard deterministic analysis.
          </p>
        </div>
        <button
          onClick={load}
          className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold flex items-center gap-2 transition cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Connect Repo */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <h2 className="text-sm font-extrabold text-slate-900 mb-1 flex items-center gap-2">
          <Plus className="w-4 h-4 text-emerald-600" /> Connect GitHub Repository
        </h2>
        <p className="text-xs text-slate-500 mb-4">
          Enter your repository in <code className="bg-slate-100 px-1 rounded">owner/repo</code> format.
          Then configure the webhook in GitHub settings.
        </p>

        {/* List of Connected Repositories */}
        {repos.length > 0 && (
          <div className="mb-4 p-3 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-[11px] font-extrabold text-slate-700 block mb-2">Connected Repositories ({repos.length}):</span>
            <div className="flex flex-wrap gap-2">
              {repos.map((r) => (
                <span key={r.id || r.repo_full_name} className="px-3 py-1 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold rounded-lg flex items-center gap-1.5 shadow-xs">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  {r.repo_full_name}
                  <span className="text-[10px] text-emerald-600 font-normal">({r.default_branch || "main"})</span>
                </span>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleConnect} className="flex items-center gap-3">
          <input
            type="text"
            value={connectRepo}
            onChange={(e) => setConnectRepo(e.target.value)}
            placeholder="myorg/myrepo"
            className="flex-1 px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <button
            type="submit"
            disabled={connecting}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-sm transition cursor-pointer disabled:opacity-50"
          >
            {connecting ? "Connecting..." : "Connect"}
          </button>
        </form>
        {connectMsg && (
          <p className={`mt-3 text-xs font-semibold whitespace-pre-wrap ${connectMsg.startsWith("✅") ? "text-emerald-700" : "text-red-600"}`}>
            {connectMsg}
          </p>
        )}
      </div>

      {/* PR List */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-extrabold text-slate-900">Pull Request Scans</h2>
          <span className="text-xs font-bold text-slate-500">Total: <span className="text-slate-900 font-extrabold">{prs.length}</span></span>
        </div>

        {loading ? (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center">
            <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs text-slate-500 font-semibold">Loading PR scans...</p>
          </div>
        ) : prs.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center">
            <GitPullRequest className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-extrabold text-slate-700">No PR scans yet</p>
            <p className="text-xs text-slate-400 mt-1">Connect a GitHub repository and open a pull request to see results here.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {prs.map((pr) => {
              const statusCfg = STATUS_CONFIG[pr.pr_status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.UNKNOWN;
              return (
                <Link
                  key={pr.id}
                  href={`/pull-requests/${pr.id}`}
                  className="block bg-white border border-slate-200 rounded-2xl p-5 hover:border-emerald-300 hover:shadow-md transition group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded-lg text-[10px] font-extrabold border uppercase ${statusCfg.color}`}>
                          {statusCfg.emoji} {statusCfg.label}
                        </span>
                        <span className="text-xs font-extrabold text-slate-900 truncate">
                          PR #{pr.pr_number} — {pr.pr_title || "Untitled PR"}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-slate-500 font-semibold mt-1">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3 h-3" />
                          {pr.repo_full_name}
                        </span>
                        <span>→ {pr.pr_branch || "unknown"}</span>
                        {pr.pr_author && <span>by {pr.pr_author}</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {/* Risk Score */}
                      <div className={`px-3 py-1.5 rounded-xl border text-center ${RISK_COLOR(pr.risk_score || 0)}`}>
                        <div className="text-sm font-black">{pr.risk_score || 0}</div>
                        <div className="text-[9px] font-extrabold uppercase tracking-wide">{pr.risk_label || "NONE"}</div>
                      </div>

                      {/* Finding counts */}
                      <div className="flex items-center gap-1.5 text-[10px] font-bold">
                        {pr.definite_count > 0 && (
                          <span className="px-2 py-1 rounded-lg bg-red-50 text-red-600 border border-red-200">
                            🔴 {pr.definite_count}
                          </span>
                        )}
                        {pr.potential_count > 0 && (
                          <span className="px-2 py-1 rounded-lg bg-amber-50 text-amber-600 border border-amber-200">
                            🟠 {pr.potential_count}
                          </span>
                        )}
                        {pr.safe_count > 0 && (
                          <span className="px-2 py-1 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200">
                            🟢 {pr.safe_count}
                          </span>
                        )}
                      </div>

                      <ExternalLink className="w-4 h-4 text-slate-300 group-hover:text-emerald-500 transition" />
                    </div>
                  </div>

                  {/* Files scanned */}
                  {pr.scanned_files?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {pr.scanned_files.slice(0, 5).map((f: string) => (
                        <span key={f} className="px-2 py-0.5 bg-slate-50 border border-slate-200 rounded text-[10px] font-semibold text-slate-600">
                          {f.split("/").pop()}
                        </span>
                      ))}
                      {pr.scanned_files.length > 5 && (
                        <span className="px-2 py-0.5 bg-slate-50 border border-slate-200 rounded text-[10px] font-semibold text-slate-500">
                          +{pr.scanned_files.length - 5} more
                        </span>
                      )}
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {/* Setup Guide */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <h3 className="text-xs font-extrabold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-emerald-600" /> Quick Setup Guide
        </h3>
        <ol className="space-y-2 text-xs font-semibold text-slate-600">
          <li className="flex gap-3"><span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-black text-[10px] flex items-center justify-center shrink-0">1</span>Set <code className="bg-slate-100 px-1 rounded">GITHUB_TOKEN</code> env var (fine-grained PAT with PR write access)</li>
          <li className="flex gap-3"><span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-black text-[10px] flex items-center justify-center shrink-0">2</span>Set <code className="bg-slate-100 px-1 rounded">GITHUB_WEBHOOK_SECRET</code> to a random secret string</li>
          <li className="flex gap-3"><span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-black text-[10px] flex items-center justify-center shrink-0">3</span>Start ngrok: <code className="bg-slate-100 px-1 rounded">ngrok http 8000</code></li>
          <li className="flex gap-3"><span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-black text-[10px] flex items-center justify-center shrink-0">4</span>Connect repo above and add the webhook URL to GitHub → Settings → Webhooks</li>
          <li className="flex gap-3"><span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-black text-[10px] flex items-center justify-center shrink-0">5</span>Open a PR — LeakGuard bot will automatically post the review!</li>
        </ol>
      </div>
    </div>
  );
}
