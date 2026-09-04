"use client";

import React, { useEffect, useState } from "react";
import { Activity, GitCommit, GitBranch, Clock, FileCode, CheckCircle2, XCircle } from "lucide-react";
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
    } catch (e) {
      console.error(e);
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
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Activity className="w-6 h-6 text-indigo-400" /> Scan History
        </h1>
        <p className="text-sm text-gray-400 mt-1">
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
                className="flex items-center gap-2 font-mono text-xs text-indigo-400 hover:underline font-bold"
              >
                <GitCommit className="w-4 h-4 text-indigo-500" />
                <span>{s.commit_sha || "HEAD"}</span>
              </button>
            ),
          },
          {
            header: "Branch",
            accessor: (s: ScanItem) => (
              <div className="flex items-center gap-1.5 font-mono text-xs text-gray-300">
                <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
                <span>{s.branch || "main"}</span>
              </div>
            ),
          },
          {
            header: "Files Scanned",
            accessor: (s: ScanItem) => (
              <div className="flex items-center gap-1.5 text-xs text-gray-300">
                <FileCode className="w-3.5 h-3.5 text-gray-400" />
                <span>{s.scanned_files_count} files</span>
              </div>
            ),
          },
          {
            header: "Duration",
            accessor: (s: ScanItem) => (
              <div className="flex items-center gap-1.5 text-xs text-gray-300">
                <Clock className="w-3.5 h-3.5 text-gray-400" />
                <span>{s.duration_seconds.toFixed(2)}s</span>
              </div>
            ),
          },
          {
            header: "Total Leaks",
            accessor: (s: ScanItem) => (
              <span
                className={`font-semibold text-xs ${
                  s.total_findings > 0 ? "text-red-400" : "text-emerald-400"
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
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/70 text-emerald-400 border border-emerald-800/60">
                    <CheckCircle2 className="w-3.5 h-3.5" /> PASSED
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/70 text-red-400 border border-red-800/60">
                    <XCircle className="w-3.5 h-3.5" /> FAILED
                  </span>
                )}
              </div>
            ),
          },
          {
            header: "Scan Date",
            accessor: (s: ScanItem) => new Date(s.created_at).toLocaleString(),
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
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1626] border border-gray-800 rounded-2xl w-full max-w-3xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-400" /> Scan Detail Overview
              </h3>
              <button
                onClick={() => setSelectedScan(null)}
                className="text-gray-400 hover:text-white text-xs font-semibold px-2 py-1 bg-gray-800 rounded-lg"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-900/60 p-4 rounded-xl border border-gray-800 text-xs">
              <div>
                <span className="text-gray-400 block font-semibold">Commit SHA</span>
                <span className="font-mono text-indigo-400 font-bold">{selectedScan.commit_sha}</span>
              </div>
              <div>
                <span className="text-gray-400 block font-semibold">Branch</span>
                <span className="font-mono text-gray-200">{selectedScan.branch}</span>
              </div>
              <div>
                <span className="text-gray-400 block font-semibold">Files Scanned</span>
                <span className="text-gray-200 font-bold">{selectedScan.scanned_files_count}</span>
              </div>
              <div>
                <span className="text-gray-400 block font-semibold">Duration</span>
                <span className="text-gray-200 font-bold">{selectedScan.duration_seconds.toFixed(2)}s</span>
              </div>
            </div>

            <h4 className="text-sm font-bold text-white pt-2">Associated Findings ({selectedScan.findings?.length || 0})</h4>
            <div className="max-h-60 overflow-y-auto space-y-2">
              {selectedScan.findings && selectedScan.findings.length > 0 ? (
                selectedScan.findings.map((f) => (
                  <div key={f.id} className="p-3 bg-gray-950 rounded-lg border border-gray-800 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-mono font-bold text-amber-400 mr-2">{f.rule_id}</span>
                      <span className="text-gray-200 font-medium">{f.file_path}:{f.line_number}</span>
                    </div>
                    <StatusBadge text={f.severity} type="severity" />
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-400 py-4 text-center bg-gray-950/50 rounded-lg border border-gray-800/50">
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
