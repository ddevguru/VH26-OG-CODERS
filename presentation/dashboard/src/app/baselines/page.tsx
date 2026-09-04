"use client";

import React, { useEffect, useState } from "react";
import { BookmarkCheck, Shield, FileCode, CheckCircle } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { api, BaselineItem, SuppressionItem } from "@/lib/api";

export default function BaselinesPage() {
  const [loading, setLoading] = useState(true);
  const [baselines, setBaselines] = useState<BaselineItem[]>([]);
  const [suppressions, setSuppressions] = useState<SuppressionItem[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [bData, sData] = await Promise.all([
          api.getBaselines().catch(() => []),
          api.getSuppressions().catch(() => []),
        ]);
        setBaselines(bData || []);
        setSuppressions(sData || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-8">
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
          <BookmarkCheck className="w-6 h-6 text-emerald-600" /> Baselines & Suppressions
        </h1>
        <p className="text-xs text-slate-500 font-semibold mt-1">
          Manage repository baseline fingerprint snapshots and active finding suppression rules.
        </p>
      </div>

      <div className="space-y-6">
        <div>
          <h2 className="text-base font-extrabold text-slate-900 mb-3 flex items-center gap-2">
            <BookmarkCheck className="w-5 h-5 text-emerald-600" /> Repository Baselines
          </h2>
          <DataTable
            columns={[
              {
                header: "Baseline Name",
                accessor: (b: BaselineItem) => <span className="font-bold text-slate-900 text-xs">{b.name}</span>,
              },
              {
                header: "Repository ID",
                accessor: (b: BaselineItem) => (
                  <span className="font-mono-code text-xs text-emerald-700 font-bold">{b.repo_id}</span>
                ),
              },
              {
                header: "Fingerprints Tracked",
                accessor: (b: BaselineItem) => (
                  <span className="font-extrabold text-emerald-800 text-xs">
                    {b.fingerprints?.length || 0} fingerprints
                  </span>
                ),
              },
              {
                header: "Created Date",
                accessor: (b: BaselineItem) => (
                  <span className="text-xs text-slate-500 font-semibold">
                    {new Date(b.created_at).toLocaleDateString()}
                  </span>
                ),
              },
            ]}
            data={baselines}
            loading={loading}
            emptyText="No repository baselines registered"
            emptySubtext="Run 'leakguard scan --update-baseline' to save baseline snapshots."
          />
        </div>

        <div>
          <h2 className="text-base font-extrabold text-slate-900 mb-3 flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-600" /> Active Suppressions
          </h2>
          <DataTable
            columns={[
              {
                header: "Finding Fingerprint",
                accessor: (s: SuppressionItem) => (
                  <span className="font-mono-code text-xs text-amber-800 font-bold">
                    {s.finding_fingerprint}
                  </span>
                ),
              },
              {
                header: "Reason / Justification",
                accessor: (s: SuppressionItem) => (
                  <span className="text-slate-700 text-xs font-medium">{s.reason || "Accepted legacy finding"}</span>
                ),
              },
              {
                header: "Suppression Date",
                accessor: (s: SuppressionItem) => (
                  <span className="text-xs text-slate-500 font-semibold">
                    {new Date(s.created_at).toLocaleDateString()}
                  </span>
                ),
              },
            ]}
            data={suppressions}
            loading={loading}
            emptyText="No active suppressions"
            emptySubtext="Suppressed findings will be excluded from CI build failure checks."
          />
        </div>
      </div>
    </div>
  );
}
