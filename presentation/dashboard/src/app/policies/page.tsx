"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, Plus, X } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { api, PolicyItem } from "@/lib/api";

export default function PoliciesPage() {
  const [loading, setLoading] = useState(true);
  const [policies, setPolicies] = useState<PolicyItem[]>([]);
  const [showModal, setShowModal] = useState(false);

  const [name, setName] = useState("");
  const [minSeverity, setMinSeverity] = useState("HIGH");
  const [minConfidence, setMinConfidence] = useState("HIGH");
  const [failOnLeak, setFailOnLeak] = useState(true);

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      const res = await api.getPolicies();
      setPolicies(res.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.createPolicy({
        name,
        min_severity: minSeverity,
        min_confidence: minConfidence,
        fail_on_leak: failOnLeak,
      });
      setShowModal(false);
      setName("");
      fetchPolicies();
    } catch (err) {
      alert(`Failed to create policy: ${(err as Error).message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-600" /> Security Blocking Policies
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Configure scan pass/fail evaluation policies and severity thresholds for CI/CD gates.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Create Policy
        </button>
      </div>

      <DataTable
        columns={[
          {
            header: "Policy Name",
            accessor: (p: PolicyItem) => (
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-xs">{p.name}</span>
                {p.is_default && (
                  <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 uppercase">
                    DEFAULT
                  </span>
                )}
              </div>
            ),
          },
          {
            header: "Minimum Severity",
            accessor: (p: PolicyItem) => <StatusBadge text={p.min_severity} type="severity" />,
          },
          {
            header: "Minimum Confidence",
            accessor: (p: PolicyItem) => <StatusBadge text={p.min_confidence} type="confidence" />,
          },
          {
            header: "Fail CI On Leak",
            accessor: (p: PolicyItem) => (
              <span
                className={`font-bold text-xs ${
                  p.fail_on_leak ? "text-rose-700" : "text-slate-500"
                }`}
              >
                {p.fail_on_leak ? "YES (Block Build)" : "NO (Warning Only)"}
              </span>
            ),
          },
          {
            header: "Created Date",
            accessor: (p: PolicyItem) => (
              <span className="text-xs text-slate-500 font-semibold">
                {new Date(p.created_at).toLocaleDateString()}
              </span>
            ),
          },
        ]}
        data={policies}
        loading={loading}
        emptyText="No security policies created"
        emptySubtext="Create a policy to enforce build blocking rules on resource leaks."
      />

      {/* Create Policy Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-md p-6 space-y-4 shadow-2xl text-slate-900">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-lg font-extrabold text-slate-900">Create Security Policy</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-bold mb-1">
                  Policy Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Strict Production Blocking"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-bold mb-1">
                    Minimum Severity
                  </label>
                  <select
                    value={minSeverity}
                    onChange={(e) => setMinSeverity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                  >
                    <option value="CRITICAL">Critical Only</option>
                    <option value="HIGH">High & Above</option>
                    <option value="MEDIUM">Medium & Above</option>
                    <option value="LOW">All Severities</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-700 font-bold mb-1">
                    Minimum Confidence
                  </label>
                  <select
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                  >
                    <option value="HIGH">High Confidence</option>
                    <option value="MEDIUM">Medium & Above</option>
                    <option value="LOW">All Confidence</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="failOnLeak"
                  checked={failOnLeak}
                  onChange={(e) => setFailOnLeak(e.target.checked)}
                  className="w-4 h-4 rounded text-emerald-600 border-slate-300 focus:ring-emerald-500"
                />
                <label htmlFor="failOnLeak" className="text-slate-800 font-bold cursor-pointer">
                  Fail Build / Push on Matching Leaks
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 font-semibold text-slate-700 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 font-extrabold text-white shadow-md shadow-emerald-600/20 cursor-pointer"
                >
                  Save Policy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
