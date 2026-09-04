"use client";

import React, { useEffect, useState } from "react";
import { BookOpen, Plus, Tag, Shield, AlertCircle, X } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { api, RuleItem } from "@/lib/api";

export default function RulesPage() {
  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);

  const [ruleId, setRuleId] = useState("");
  const [ruleName, setRuleName] = useState("");
  const [category, setCategory] = useState("file");
  const [defaultSeverity, setDefaultSeverity] = useState("HIGH");
  const [defaultConfidence, setDefaultConfidence] = useState("HIGH");
  const [description, setDescription] = useState("");

  const fetchRules = async () => {
    try {
      setLoading(true);
      const res = await api.getRules();
      setRules(res.items || []);
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80, pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-emerald-600" /> Resource Lifetime Rules
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Standard and custom static analysis rules defining resource acquisition and release patterns.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Create Custom Rule
        </button>
      </div>

      <DataTable
        columns={[
          {
            header: "Rule ID",
            accessor: (r: RuleItem) => (
              <span className="font-mono-code text-xs font-bold text-emerald-800">{r.rule_id}</span>
            ),
          },
          {
            header: "Rule Name",
            accessor: (r: RuleItem) => <span className="font-bold text-slate-900 text-xs">{r.name}</span>,
          },
          {
            header: "Category",
            accessor: (r: RuleItem) => (
              <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                <Tag className="w-3.5 h-3.5 text-emerald-600" />
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
                className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full border uppercase ${
                  r.is_custom
                    ? "bg-purple-50 text-purple-800 border-purple-200"
                    : "bg-emerald-50 text-emerald-800 border-emerald-200"
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
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-md p-6 space-y-4 shadow-2xl text-slate-900">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-lg font-extrabold text-slate-900">Create Custom Resource Rule</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreateRule} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Rule ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CUST-DB-001"
                  value={ruleId}
                  onChange={(e) => setRuleId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-mono-code placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Rule Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Unclosed Redis Lock Handle"
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Category</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-bold mb-1">Severity</label>
                  <select
                    value={defaultSeverity}
                    onChange={(e) => setDefaultSeverity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 font-bold mb-1">Confidence</label>
                  <select
                    value={defaultConfidence}
                    onChange={(e) => setDefaultConfidence(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Description</label>
                <textarea
                  rows={3}
                  placeholder="Explain why this resource handle must be closed..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 font-semibold text-slate-700 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 font-extrabold text-white shadow-md shadow-emerald-600/20 cursor-pointer"
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
