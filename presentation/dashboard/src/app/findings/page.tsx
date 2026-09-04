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
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <AlertTriangle className="w-6 h-6 text-amber-400" /> Resource Leak Findings
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Detailed inventory of unclosed files, sockets, database handles, and subprocesses detected across project paths.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 rounded-xl border border-gray-800/80 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-gray-400">
            <Filter className="w-4 h-4 text-indigo-400" /> Filters:
          </div>

          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setOffset(0);
            }}
            className="px-3 py-1.5 bg-gray-950 border border-gray-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
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
            className="px-3 py-1.5 bg-gray-950 border border-gray-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="RESOLVED">Resolved</option>
            <option value="SUPPRESSED">Suppressed</option>
          </select>
        </div>

        <div className="text-xs text-gray-400 font-semibold">
          Total Discovered: <span className="text-white font-bold">{total}</span>
        </div>
      </div>

      <DataTable
        columns={[
          {
            header: "Rule ID",
            accessor: (f: FindingItem) => (
              <span className="font-mono text-xs font-bold text-amber-400">{f.rule_id}</span>
            ),
          },
          {
            header: "Location",
            accessor: (f: FindingItem) => (
              <div className="font-mono text-xs text-gray-200">
                <span>{f.file_path}</span>
                <span className="text-emerald-400 font-bold ml-1">:{f.line_number}</span>
              </div>
            ),
          },
          {
            header: "Leak Title",
            accessor: (f: FindingItem) => <span className="font-medium text-white">{f.title}</span>,
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
                className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition-colors"
              >
                <Eye className="w-3.5 h-3.5" /> Inspect
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
        emptyText="No leak findings match criteria"
        emptySubtext="Clear active filters or run a scan to analyze project source code."
      />

      <FindingDetailModal
        finding={selectedFinding}
        onClose={() => setSelectedFinding(null)}
        onStatusUpdated={handleStatusUpdated}
      />
    </div>
  );
}
