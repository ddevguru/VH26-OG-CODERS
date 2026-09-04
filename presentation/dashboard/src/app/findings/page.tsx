"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, Filter, Search, Eye } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { FindingDetailModal } from "@/components/FindingDetailModal";
import { api, FindingItem } from "@/lib/api";

export default function FindingsPage() {
  const [loading, setLoading] = useState(true);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedFinding, setSelectedFinding] = useState<FindingItem | null>(null);

  const fetchFindings = async (currentOffset = 0) => {
    try {
      setLoading(true);
      const res = await api.getFindings({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        limit: 20,
        offset: currentOffset,
      });
      setFindings(res.items || []);
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
    fetchFindings(offset);
  }, [offset, severityFilter, statusFilter]);

  const handleStatusUpdated = (updated: FindingItem) => {
    setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
    if (selectedFinding?.id === updated.id) {
      setSelectedFinding(updated);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
          <AlertTriangle className="w-6 h-6 text-amber-600" /> Resource Leak Findings
        </h1>
        <p className="text-xs text-slate-500 font-semibold mt-1">
          Detailed inventory of unclosed files, sockets, database handles, and subprocesses detected across project paths.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
            <Filter className="w-4 h-4 text-emerald-600" /> Filters:
          </div>

          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setOffset(0);
            }}
            className="px-3.5 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="ERROR">Error</option>
            <option value="WARNING">Warning</option>
            <option value="INFO">Info</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setOffset(0);
            }}
            className="px-3.5 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="RESOLVED">Resolved</option>
            <option value="SUPPRESSED">Suppressed</option>
          </select>
        </div>

        <span className="text-xs font-bold text-slate-500">
          Showing {findings.length} of {total} findings
        </span>
      </div>

      <DataTable
        columns={[
          {
            header: "Rule ID",
            accessor: (f: FindingItem) => (
              <span className="font-mono-code text-xs font-bold text-amber-800">{f.rule_id}</span>
            ),
          },
          {
            header: "Resource File Path",
            accessor: (f: FindingItem) => (
              <div>
                <div className="font-mono-code text-xs text-slate-900 font-bold">{f.file_path}:{f.line_number}</div>
                {f.title && <div className="text-[11px] text-slate-500 font-semibold truncate max-w-xs">{f.title}</div>}
              </div>
            ),
          },
          {
            header: "Severity",
            accessor: (f: FindingItem) => <StatusBadge text={f.severity} type="severity" />,
          },
          {
            header: "Confidence",
            accessor: (f: FindingItem) => <StatusBadge text={f.confidence} type="confidence" />,
          },
          {
            header: "Status",
            accessor: (f: FindingItem) => <StatusBadge text={f.status} type="status" />,
          },
          {
            header: "Action",
            accessor: (f: FindingItem) => (
              <button
                onClick={() => setSelectedFinding(f)}
                className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-xs font-bold text-emerald-800 transition cursor-pointer"
              >
                <Eye className="w-3.5 h-3.5 text-emerald-600" />
                <span>Inspect</span>
              </button>
            ),
          },
        ]}
        data={findings}
        loading={loading}
        total={total}
        limit={20}
        offset={offset}
        onPageChange={setOffset}
        emptyText="No leak findings detected"
        emptySubtext="Run a local CLI scan to verify your repository for unclosed file handles."
      />

      {/* Finding Detail Modal */}
      {selectedFinding && (
        <FindingDetailModal
          finding={selectedFinding}
          onClose={() => setSelectedFinding(null)}
          onStatusUpdated={handleStatusUpdated}
        />
      )}
    </div>
  );
}
