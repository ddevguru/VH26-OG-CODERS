"use client";

import React, { useEffect, useState } from "react";
import { History, Activity, Shield, User } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { api, AuditEventItem, formatDateTime } from "@/lib/api";


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
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
          <History className="w-6 h-6 text-emerald-600" /> Tenant Audit Trail
        </h1>
        <p className="text-xs text-slate-500 font-semibold mt-1">
          Immutable audit log tracking mutating actions, policy changes, member role updates, and scan ingestions.
        </p>
      </div>

      <DataTable
        columns={[
          {
            header: "Action",
            accessor: (e: AuditEventItem) => (
              <span className="font-mono-code text-[10px] font-extrabold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 uppercase">
                {e.action}
              </span>
            ),
          },
          {
            header: "Resource Type",
            accessor: (e: AuditEventItem) => (
              <span className="text-xs font-bold text-slate-900">{e.resource_type}</span>
            ),
          },
          {
            header: "Resource ID",
            accessor: (e: AuditEventItem) => (
              <span className="font-mono-code text-xs text-slate-600 font-medium">{e.resource_id || "—"}</span>
            ),
          },
          {
            header: "User ID",
            accessor: (e: AuditEventItem) => (
              <div className="flex items-center gap-1.5 font-mono-code text-xs text-slate-600 font-medium">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span>{e.user_id || "System"}</span>
              </div>
            ),
          },
          {
            header: "Event Details",
            accessor: (e: AuditEventItem) => (
              <span className="font-mono-code text-xs text-slate-500 font-medium truncate max-w-xs block">
                {JSON.stringify(e.details)}
              </span>
            ),
          },
          {
            header: "Timestamp",
            accessor: (e: AuditEventItem) => (
              <span className="text-xs text-slate-500 font-semibold">
                {formatDateTime(e.created_at)}
              </span>
            ),
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

