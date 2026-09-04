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
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <BookmarkCheck className="w-6 h-6 text-indigo-400" /> Baselines & Suppressions
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Manage repository baseline fingerprint snapshots and active finding suppression rules.
        </p>
      </div>

      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
            <BookmarkCheck className="w-5 h-5 text-indigo-400" /> Repository Baselines
          </h2>
          <DataTable
            columns={[
              {
                header: "Baseline Name",
                accessor: (b: BaselineItem) => <span className="font-bold text-white">{b.name}</span>,
              },
              {
                header: "Repository ID",
                accessor: (b: BaselineItem) => (
                  <span className="font-mono text-xs text-indigo-400">{b.repo_id}</span>
                ),
              },
              {
                header: "Fingerprints Tracked",
                accessor: (b: BaselineItem) => (
                  <span className="font-semibold text-emerald-400">
                    {b.fingerprints?.length || 0} fingerprints
                  </span>
                ),
              },
              {
                header: "Created At",
                accessor: (b: BaselineItem) => new Date(b.created_at).toLocaleDateString(),
              },
            ]}
            data={baselines}
            loading={loading}
            emptyText="No repository baselines registered"
            emptySubtext="Run 'leakguard scan --update-baseline' to save baseline snapshots."
          />
        </div>

        <div>
          <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-400" /> Active Suppressions
          </h2>
          <DataTable
            columns={[
              {
                header: "Finding Fingerprint",
                accessor: (s: SuppressionItem) => (
                  <span className="font-mono text-xs text-amber-400 font-bold">
                    {s.finding_fingerprint}
                  </span>
                ),
              },
              {
                header: "Reason / Justification",
                accessor: (s: SuppressionItem) => (
                  <span className="text-gray-300">{s.reason || "Accepted legacy finding"}</span>
                ),
              },
              {
                header: "Suppressed By User ID",
                accessor: (s: SuppressionItem) => (
                  <span className="font-mono text-xs text-gray-400">{s.suppressed_by_user_id || "System"}</span>
                ),
              },
              {
                header: "Date",
                accessor: (s: SuppressionItem) => new Date(s.created_at).toLocaleDateString(),
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
