"use client";

import React, { useEffect, useState } from "react";
import { Sliders, Plus, CheckCircle2, Lock } from "lucide-react";
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
      const data = await api.getIntegrations();
      setIntegrations(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleCreateIntegration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.createIntegration(name, integrationType, {
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Sliders className="w-6 h-6 text-indigo-400" /> Integrations & Webhooks
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Connect LeakGuard with GitHub Actions, GitLab CI, Jenkins, Slack, and external webhooks.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all"
        >
          <Plus className="w-4 h-4" /> Add Integration
        </button>
      </div>

      <DataTable
        columns={[
          {
            header: "Integration Name",
            accessor: (i: IntegrationItem) => <span className="font-bold text-white">{i.name}</span>,
          },
          {
            header: "Type",
            accessor: (i: IntegrationItem) => (
              <span className="font-mono text-xs text-indigo-300 uppercase font-semibold">
                {i.integration_type}
              </span>
            ),
          },
          {
            header: "Configuration (Sanitized)",
            accessor: (i: IntegrationItem) => (
              <div className="flex items-center gap-2 font-mono text-xs text-gray-400">
                <Lock className="w-3.5 h-3.5 text-emerald-400" />
                <span>{JSON.stringify(i.config)}</span>
              </div>
            ),
          },
          {
            header: "Status",
            accessor: (i: IntegrationItem) => (
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                  i.is_active
                    ? "bg-emerald-950/70 text-emerald-400 border border-emerald-800/60"
                    : "bg-gray-800 text-gray-400 border border-gray-700"
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> {i.is_active ? "ACTIVE" : "INACTIVE"}
              </span>
            ),
          },
          {
            header: "Created At",
            accessor: (i: IntegrationItem) => new Date(i.created_at).toLocaleDateString(),
          },
        ]}
        data={integrations}
        loading={loading}
        emptyText="No integrations configured"
        emptySubtext="Add webhooks or GitHub Action integrations to receive automated scan notifications."
      />

      {/* Add Integration Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1626] border border-gray-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Configure Integration</h3>
            <form onSubmit={handleCreateIntegration} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Integration Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production Slack Alerts"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-semibold mb-1">Integration Type</label>
                <select
                  value={integrationType}
                  onChange={(e) => setIntegrationType(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                >
                  <option value="github">GitHub Actions</option>
                  <option value="gitlab">GitLab CI</option>
                  <option value="jenkins">Jenkins</option>
                  <option value="slack">Slack Notification</option>
                  <option value="webhook">Generic Webhook</option>
                </select>
              </div>

              <div>
                <label className="block text-gray-400 font-semibold mb-1">Webhook URL</label>
                <input
                  type="url"
                  placeholder="https://hooks.slack.com/services/..."
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-semibold mb-1">Secret API Token</label>
                <input
                  type="password"
                  placeholder="Secret token for payload signing"
                  value={secretToken}
                  onChange={(e) => setSecretToken(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white"
                />
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
