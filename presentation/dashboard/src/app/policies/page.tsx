"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, Plus, CheckCircle2 } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { api, PolicyItem } from "@/lib/api";

export default function PoliciesPage() {
  const [loading, setLoading] = useState(true);
  const [policies, setPolicies] = useState<PolicyItem[]>([]);
  const [showModal, setShowModal] = useState(false);

  const [name, setName] = useState("");
  const [minSeverity, setMinSeverity] = useState("HIGH");
  const [minConfidence, setMinConfidence] = useState("MEDIUM");
  const [failOnLeak, setFailOnLeak] = useState(true);

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      const data = await api.getPolicies();
      setPolicies(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, []);

  const handleCreatePolicy = async (e: React.FormEvent) => {
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-indigo-400" /> Security Blocking Policies
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Configure scan pass/fail evaluation policies and severity thresholds for CI/CD gates.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all"
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
                <span className="font-bold text-white">{p.name}</span>
                {p.is_default && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800">
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
                className={`font-semibold text-xs ${
                  p.fail_on_leak ? "text-red-400" : "text-gray-400"
                }`}
              >
                {p.fail_on_leak ? "YES (Blocking)" : "NO (Advisory)"}
              </span>
            ),
          },
          {
            header: "Created At",
            accessor: (p: PolicyItem) => new Date(p.created_at).toLocaleDateString(),
          },
        ]}
        data={policies}
        loading={loading}
        emptyText="No custom policies configured"
        emptySubtext="Default Security Policy is active for all repository scans."
      />

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1626] border border-gray-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Create Security Policy</h3>
            <form onSubmit={handleCreatePolicy} className="space-y-4 text-xs">
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Policy Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Strict Production Gate"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Min Severity</label>
                  <select
                    value={minSeverity}
                    onChange={(e) => setMinSeverity(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>

                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Min Confidence</label>
                  <select
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                  >
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="failOnLeak"
                  checked={failOnLeak}
                  onChange={(e) => setFailOnLeak(e.target.checked)}
                  className="rounded border-gray-800 bg-gray-950 text-indigo-600 focus:ring-0"
                />
                <label htmlFor="failOnLeak" className="text-gray-300 font-semibold cursor-pointer">
                  Fail build if policy threshold is violated
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 font-semibold text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold text-white shadow-md shadow-indigo-600/30"
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
