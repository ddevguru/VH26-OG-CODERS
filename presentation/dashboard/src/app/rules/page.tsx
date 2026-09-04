"use client";

import React, { useEffect, useState } from "react";
import { BookOpen, Plus, ShieldCheck, Tag } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { api, RuleItem } from "@/lib/api";

export default function RulesPage() {
  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);

  const [ruleId, setRuleId] = useState("");
  const [ruleName, setRuleName] = useState("");
  const [category, setCategory] = useState("File System");
  const [defaultSeverity, setDefaultSeverity] = useState("HIGH");
  const [defaultConfidence, setDefaultConfidence] = useState("HIGH");
  const [description, setDescription] = useState("");

  const fetchRules = async () => {
    try {
      setLoading(true);
      const data = await api.getRules();
      setRules(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleId || !ruleName) return;
    try {
      await api.createRule({
        rule_id: ruleId,
        name: ruleName,
        category,
        default_severity: defaultSeverity,
        default_confidence: defaultConfidence,
        description,
        is_custom: true,
      });
      setShowAddModal(false);
      fetchRules();
    } catch (err) {
      alert(`Failed to create rule: ${(err as Error).message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-indigo-400" /> Resource Lifetime Rules
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Standard and custom static analysis rules defining resource acquisition and release patterns.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all"
        >
          <Plus className="w-4 h-4" /> Create Custom Rule
        </button>
      </div>

      <DataTable
        columns={[
          {
            header: "Rule ID",
            accessor: (r: RuleItem) => (
              <span className="font-mono text-xs font-bold text-amber-400">{r.rule_id}</span>
            ),
          },
          {
            header: "Rule Name",
            accessor: (r: RuleItem) => <span className="font-bold text-white">{r.name}</span>,
          },
          {
            header: "Category",
            accessor: (r: RuleItem) => (
              <div className="flex items-center gap-1.5 text-xs text-gray-300">
                <Tag className="w-3.5 h-3.5 text-indigo-400" />
                <span>{r.category}</span>
              </div>
            ),
          },
          {
            header: "Default Severity",
            accessor: (r: RuleItem) => <StatusBadge text={r.default_severity} type="severity" />,
          },
          {
            header: "Default Confidence",
            accessor: (r: RuleItem) => <StatusBadge text={r.default_confidence} type="confidence" />,
          },
          {
            header: "Rule Origin",
            accessor: (r: RuleItem) => (
              <span
                className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                  r.is_custom
                    ? "bg-purple-950/60 text-purple-300 border-purple-800/40"
                    : "bg-blue-950/60 text-blue-300 border-blue-800/40"
                }`}
              >
                {r.is_custom ? "Custom Rule" : "Standard Engine"}
              </span>
            ),
          },
        ]}
        data={rules}
        loading={loading}
        emptyText="No rules available"
        emptySubtext="Rules are seeded on backend startup."
      />

      {/* Add Custom Rule Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1626] border border-gray-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Create Custom Resource Rule</h3>
            <form onSubmit={handleCreateRule} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Rule ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CUST-DB-001"
                  value={ruleId}
                  onChange={(e) => setRuleId(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-semibold mb-1">Rule Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Unclosed Redis Lock Handle"
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-semibold mb-1">Category</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Severity</label>
                  <select
                    value={defaultSeverity}
                    onChange={(e) => setDefaultSeverity(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-400 font-semibold mb-1">Confidence</label>
                  <select
                    value={defaultConfidence}
                    onChange={(e) => setDefaultConfidence(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                  >
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-gray-400 font-semibold mb-1">Description</label>
                <textarea
                  rows={3}
                  placeholder="Explain why this resource handle must be closed..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 font-semibold text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold text-white shadow-md shadow-indigo-600/30"
                >
                  Create Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
