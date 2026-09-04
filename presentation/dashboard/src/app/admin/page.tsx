"use client";

import React, { useEffect, useState } from "react";
import {
  Users,
  Shield,
  Activity,
  FolderGit2,
  AlertTriangle,
  Server,
  Key,
  Database,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { MetricCard } from "@/components/MetricCard";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

export default function AdminPage() {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"users" | "scans">("users");
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [scans, setScans] = useState<any[]>([]);
  const [error, setError] = useState("");

  async function loadAdminData() {
    try {
      setLoading(true);
      setError("");
      const [sRes, uRes, scRes] = await Promise.all([
        api.getAdminStats().catch(() => null),
        api.getAdminUsers(20, 0).catch(() => ({ items: [] })),
        api.getAdminScans(20, 0).catch(() => ({ items: [] })),
      ]);

      setStats(sRes || {
        total_users: 1,
        total_organizations: 1,
        total_repositories: 1,
        total_scans: 0,
        total_findings: 0,
        open_leaks: 0,
        system_status: "healthy",
      });
      setUsers(uRes.items || []);
      setScans(scRes.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to fetch admin data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAdminData();
  }, []);

  return (
    <div className="space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Admin System Control Panel</h1>
            <span className="bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold px-2.5 py-0.5 rounded-full">
              Global Admin
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            System-wide statistics, multi-tenant user access logs, and global static scan monitoring.
          </p>
        </div>
        <button
          onClick={loadAdminData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 border border-gray-800 hover:bg-gray-800 text-sm font-semibold text-gray-200 rounded-xl transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Refresh Data
        </button>
      </div>

      {error && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400 text-sm">
          {error} (Showing fallback / local control plane data)
        </div>
      )}

      {/* Admin Metric Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Total Registered Users"
          value={stats?.total_users ?? 0}
          subtitle="System-wide user accounts"
          icon={Users}
          trend="Active"
          trendType="positive"
        />
        <MetricCard
          title="Organizations"
          value={stats?.total_organizations ?? 0}
          subtitle="Active tenant organizations"
          icon={Shield}
          trend="Multi-Tenant"
          trendType="positive"
        />
        <MetricCard
          title="Total Scans Run"
          value={stats?.total_scans ?? 0}
          subtitle="CI/CD and CLI scan runs"
          icon={Activity}
          trend="Live Logs"
          trendType="positive"
        />
        <MetricCard
          title="Total Leaks Flagged"
          value={stats?.total_findings ?? 0}
          subtitle={`${stats?.open_leaks ?? 0} open findings`}
          icon={AlertTriangle}
          trend={stats?.open_leaks > 0 ? "Leaks Active" : "Clean"}
          trendType={stats?.open_leaks > 0 ? "negative" : "positive"}
        />
      </div>

      {/* Tabs Selection */}
      <div className="flex border-b border-gray-800 space-x-6">
        <button
          onClick={() => setActiveTab("users")}
          className={`pb-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "users"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          Registered Users & Roles ({users.length})
        </button>
        <button
          onClick={() => setActiveTab("scans")}
          className={`pb-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "scans"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          All System Scans ({scans.length})
        </button>
      </div>

      {/* Tab 1: System Users Table */}
      {activeTab === "users" && (
        <div>
          <DataTable
            columns={[
              {
                header: "User Email",
                accessor: (u: any) => (
                  <div>
                    <span className="font-semibold text-white text-sm">{u.email}</span>
                    {u.full_name && <div className="text-xs text-gray-500">{u.full_name}</div>}
                  </div>
                ),
              },
              {
                header: "Organization(s)",
                accessor: (u: any) => (
                  <span className="text-xs text-indigo-300 font-medium">
                    {u.organizations && u.organizations.length > 0
                      ? u.organizations.join(", ")
                      : "Default Org"}
                  </span>
                ),
              },
              {
                header: "Role",
                accessor: (u: any) => (
                  <span className="bg-indigo-500/20 text-indigo-300 text-xs font-semibold px-2 py-0.5 rounded-full border border-indigo-500/30">
                    {u.role || "Developer"}
                  </span>
                ),
              },
              {
                header: "Status",
                accessor: (u: any) => (
                  <StatusBadge text={u.is_active ? "ACTIVE" : "INACTIVE"} type="status" />
                ),
              },
              {
                header: "Joined Date",
                accessor: (u: any) => (
                  <span className="text-xs text-gray-400">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "System Default"}
                  </span>
                ),
              },
            ]}
            data={users}
            loading={loading}
            emptyText="No registered users found"
            emptySubtext="Users will appear here once registered via Web Portal or CLI."
          />
        </div>
      )}

      {/* Tab 2: System Scans Table */}
      {activeTab === "scans" && (
        <div>
          <DataTable
            columns={[
              {
                header: "Repository",
                accessor: (s: any) => (
                  <span className="font-semibold text-white">{s.repository_name || "Unknown Repo"}</span>
                ),
              },
              {
                header: "Commit / Branch",
                accessor: (s: any) => (
                  <span className="font-mono text-xs text-indigo-300">
                    {s.branch || "main"} ({s.commit_sha ? s.commit_sha.substring(0, 7) : "HEAD"})
                  </span>
                ),
              },
              {
                header: "Files Scanned",
                accessor: (s: any) => `${s.scanned_files_count || 0} files`,
              },
              {
                header: "Total Findings",
                accessor: (s: any) => (
                  <span className={s.total_findings > 0 ? "text-amber-400 font-bold" : "text-emerald-400 font-medium"}>
                    {s.total_findings || 0} Leaks
                  </span>
                ),
              },
              {
                header: "Policy Check",
                accessor: (s: any) => (
                  <StatusBadge text={s.policy_passed ? "PASSED" : "FAILED"} type="status" />
                ),
              },
            ]}
            data={scans}
            loading={loading}
            emptyText="No system scans recorded yet"
            emptySubtext="Run 'python -m leakguard scan .' to generate scan history."
          />
        </div>
      )}
    </div>
  );
}
