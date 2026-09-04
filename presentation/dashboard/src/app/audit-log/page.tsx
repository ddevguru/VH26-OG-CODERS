"use client";

import React, { useEffect, useState } from "react";
import { History, Activity, Shield, User } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { api, AuditEventItem } from "@/lib/api";

export default function AuditLogPage() {
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  const fetchAuditLogs = async (currentOffset = 0) => {
    try {
      setLoading(true);
      const res = await api.getAuditLogs(20, currentOffset);
      setEvents(res.items || []);
      setTotal(res.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs(offset);
  }, [offset]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <History className="w-6 h-6 text-indigo-400" /> Tenant Audit Trail
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Immutable audit log tracking mutating actions, policy changes, member role updates, and scan ingestions.
        </p>
      </div>

      <DataTable
        columns={[
          {
            header: "Action",
            accessor: (e: AuditEventItem) => (
              <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-950/60 px-2 py-1 rounded border border-indigo-800/40">
                {e.action}
              </span>
            ),
          },
          {
            header: "Resource Type",
            accessor: (e: AuditEventItem) => (
              <span className="text-xs font-semibold text-gray-200">{e.resource_type}</span>
            ),
          },
          {
            header: "Resource ID",
            accessor: (e: AuditEventItem) => (
              <span className="font-mono text-xs text-gray-400">{e.resource_id || "—"}</span>
            ),
          },
          {
            header: "User ID",
            accessor: (e: AuditEventItem) => (
              <div className="flex items-center gap-1.5 font-mono text-xs text-gray-400">
                <User className="w-3.5 h-3.5 text-gray-500" />
                <span>{e.user_id || "System"}</span>
              </div>
            ),
          },
          {
            header: "Event Details",
            accessor: (e: AuditEventItem) => (
              <span className="font-mono text-xs text-gray-400">{JSON.stringify(e.details)}</span>
            ),
          },
          {
            header: "Timestamp",
            accessor: (e: AuditEventItem) => new Date(e.created_at).toLocaleString(),
          },
        ]}
        data={events}
        loading={loading}
        total={total}
        limit={20}
        offset={offset}
        onPageChange={setOffset}
        emptyText="No audit log events recorded"
        emptySubtext="Mutating actions (scan ingestion, policy updates, integration changes) will be automatically recorded here."
      />
    </div>
  );
}
