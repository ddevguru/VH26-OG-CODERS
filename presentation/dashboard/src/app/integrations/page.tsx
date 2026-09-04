"use client";

import React, { useEffect, useState } from "react";
import { Sliders, Plus, Lock, CheckCircle2, X } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { api, IntegrationItem } from "@/lib/api";

export default function IntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [integrations, setIntegrations] = useState<IntegrationItem[]>([]);
  const [showModal, setShowModal] = useState(false);

  const [name, setName] = useState("");
  const [integrationType, setIntegrationType] = useState("github");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [secretToken, setSecretToken] = useState("");

  const fetchIntegrations = async () => {
    try {
      setLoading(true);
      const res = await api.getIntegrations();
      setIntegrations(res.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.createIntegration({
        name,
        integration_type: integrationType,
        webhook_url: webhookUrl,
        api_secret_token: secretToken,
      });
      setShowModal(false);
      setName("");
      setWebhookUrl("");
      setSecretToken("");
      fetchIntegrations();
    } catch (err) {
      alert(`Failed to create integration: ${(err as Error).message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Sliders className="w-6 h-6 text-emerald-600" /> Integrations & Webhooks
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Connect LeakGuard with GitHub Actions, GitLab CI, Jenkins, Slack, and external webhooks.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Add Integration
        </button>
      </div>

      <DataTable
        columns={[
          {
            header: "Integration Name",
            accessor: (i: IntegrationItem) => <span className="font-bold text-slate-900 text-xs">{i.name}</span>,
          },
          {
            header: "Type",
            accessor: (i: IntegrationItem) => (
              <span className="font-mono-code text-[10px] text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 uppercase font-extrabold">
                {i.integration_type}
              </span>
            ),
          },
          {
            header: "Configuration (Sanitized)",
            accessor: (i: IntegrationItem) => (
              <div className="flex items-center gap-2 font-mono-code text-xs text-slate-600 font-semibold">
                <Lock className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span className="truncate max-w-xs">{JSON.stringify(i.config)}</span>
              </div>
            ),
          },
          {
            header: "Status",
            accessor: (i: IntegrationItem) => (
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                  i.is_active
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    : "bg-slate-100 text-slate-600 border border-slate-200"
                }`}
              >
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                {i.is_active ? "ACTIVE" : "INACTIVE"}
              </span>
            ),
          },
          {
            header: "Created Date",
            accessor: (i: IntegrationItem) => (
              <span className="text-xs text-slate-500 font-semibold">
                {new Date(i.created_at).toLocaleDateString()}
              </span>
            ),
          },
        ]}
        data={integrations}
        loading={loading}
        emptyText="No webhooks or integrations configured"
        emptySubtext="Add a Slack webhook or CI pipeline integration."
      />

      {/* Add Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-md p-6 space-y-4 shadow-2xl text-slate-900">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-lg font-extrabold text-slate-900">Configure Integration</h3>
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
                  Integration Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production Slack Alert"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">
                  Integration Type
                </label>
                <select
                  value={integrationType}
                  onChange={(e) => setIntegrationType(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                >
                  <option value="github">GitHub Actions</option>
                  <option value="gitlab">GitLab CI</option>
                  <option value="jenkins">Jenkins CI</option>
                  <option value="slack">Slack Notification</option>
                  <option value="webhook">Generic HTTP Webhook</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">
                  Webhook Target URL
                </label>
                <input
                  type="url"
                  placeholder="https://hooks.slack.com/services/..."
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">
                  Secret Auth Token
                </label>
                <input
                  type="password"
                  placeholder="••••••••••••"
                  value={secretToken}
                  onChange={(e) => setSecretToken(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                />
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
                  Save Integration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
