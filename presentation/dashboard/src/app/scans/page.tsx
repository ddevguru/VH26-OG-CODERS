"use client";

import React, { useEffect, useState } from "react";
import { Activity, GitCommit, GitBranch, Clock, FileCode, CheckCircle2, XCircle, X } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ScanItem } from "@/lib/api";

export default function ScansPage() {
  const [loading, setLoading] = useState(true);
  const [scans, setScans] = useState<ScanItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [selectedScan, setSelectedScan] = useState<ScanItem | null>(null);

  const fetchScans = async (currentOffset = 0) => {
    try {
      setLoading(true);
      const res = await api.getScans(20, currentOffset);
      setScans(res.items || []);
      setTotal(res.total || 0);
    } catch (e: any) {
      if (e.message?.includes("401") || e.message?.includes("Unauthorized")) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("leakguard_token");
          window.location.href = "/login";
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScans(offset);
  }, [offset]);

  const handleScanClick = async (scan: ScanItem) => {
    try {
      const fullScan = await api.getScan(scan.id);
      setSelectedScan(fullScan);
    } catch (e) {
      setSelectedScan(scan);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
          <Activity className="w-6 h-6 text-emerald-600" /> Scan History
        </h1>
        <p className="text-xs text-slate-500 font-semibold mt-1">
          Historical log of AST static analysis scans executed via local CLI or CI/CD pipelines.
        </p>
      </div>

      <DataTable
        columns={[
          {
            header: "Commit SHA",
            accessor: (s: ScanItem) => (
              <button
                onClick={() => handleScanClick(s)}
                className="flex items-center gap-2 font-mono-code text-xs text-emerald-700 hover:underline font-bold"
              >
                <GitCommit className="w-4 h-4 text-emerald-600" />
                <span>{s.commit_sha || "HEAD"}</span>
              </button>
            ),
          },
          {
            header: "Branch",
            accessor: (s: ScanItem) => (
              <div className="flex items-center gap-1.5 font-mono-code text-xs text-slate-600 font-semibold">
                <GitBranch className="w-3.5 h-3.5 text-emerald-600" />
                <span>{s.branch || "main"}</span>
              </div>
            ),
          },
          {
            header: "Files Scanned",
            accessor: (s: ScanItem) => (
              <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                <FileCode className="w-3.5 h-3.5 text-slate-400" />
                <span>{s.scanned_files_count} files</span>
              </div>
            ),
          },
          {
            header: "Duration",
            accessor: (s: ScanItem) => (
              <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>{s.duration_seconds.toFixed(2)}s</span>
              </div>
            ),
          },
          {
            header: "Total Leaks",
            accessor: (s: ScanItem) => (
              <span
                className={`font-bold text-xs ${
                  s.total_findings > 0 ? "text-rose-700" : "text-emerald-800"
                }`}
              >
                {s.total_findings} findings
              </span>
            ),
          },
          {
            header: "Policy Result",
            accessor: (s: ScanItem) => (
              <div className="flex items-center gap-1.5">
                {s.policy_passed ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-200 uppercase">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> PASSED
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-50 text-rose-700 border border-rose-200 uppercase">
                    <XCircle className="w-3.5 h-3.5 text-rose-600" /> FAILED
                  </span>
                )}
              </div>
            ),
          },
          {
            header: "Scan Date",
            accessor: (s: ScanItem) => (
              <span className="text-xs text-slate-500 font-semibold">
                {new Date(s.created_at).toLocaleString()}
              </span>
            ),
          },
        ]}
        data={scans}
        loading={loading}
        total={total}
        limit={20}
        offset={offset}
        onPageChange={setOffset}
        emptyText="No scan records found"
        emptySubtext="Run 'leakguard upload --repo <name>' or execute a CI build to record static analysis scans."
      />

      {/* Scan Detail Modal */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-3xl p-6 space-y-4 shadow-2xl text-slate-900">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
                <Activity className="w-5 h-5 text-emerald-600" /> Scan Detail Overview
              </h3>
              <button
                onClick={() => setSelectedScan(null)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-2xl border border-slate-200 text-xs">
              <div>
                <span className="text-slate-500 block font-bold">Commit SHA</span>
                <span className="font-mono-code text-emerald-700 font-bold">{selectedScan.commit_sha}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-bold">Branch</span>
                <span className="font-mono-code text-slate-800 font-semibold">{selectedScan.branch}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-bold">Files Scanned</span>
                <span className="text-slate-900 font-extrabold">{selectedScan.scanned_files_count}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-bold">Duration</span>
                <span className="text-slate-900 font-extrabold">{selectedScan.duration_seconds.toFixed(2)}s</span>
              </div>
            </div>

            <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-700 pt-2">
              Associated Findings ({selectedScan.findings?.length || 0})
            </h4>
            <div className="max-h-60 overflow-y-auto space-y-2">
              {selectedScan.findings && selectedScan.findings.length > 0 ? (
                selectedScan.findings.map((f) => (
                  <div key={f.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-mono-code font-bold text-emerald-800 mr-2">{f.rule_id}</span>
                      <span className="text-slate-800 font-semibold">{f.file_path}:{f.line_number}</span>
                    </div>
                    <StatusBadge text={f.severity} type="severity" />
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 py-4 text-center bg-slate-50 rounded-xl border border-slate-200 font-semibold">
                  No leak findings detected during this scan.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

