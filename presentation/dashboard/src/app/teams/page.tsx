"use client";

import React, { useEffect, useState } from "react";
import { Users, UserPlus, Shield, Mail } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

export default function TeamsPage() {
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [mRes, tRes] = await Promise.all([
          api.getMembers().catch(() => ({ items: [] })),
          api.getTeams().catch(() => []),
        ]);
        setMembers(mRes.items || []);
        setTeams(tRes || []);
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
          <Users className="w-6 h-6 text-indigo-400" /> Teams & Organization Members
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Manage team access controls and Role-Based Access Control (RBAC) roles.
        </p>
      </div>

      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-bold text-white mb-3">Organization Members & RBAC Roles</h2>
          <DataTable
            columns={[
              {
                header: "Member Name",
                accessor: (m: any) => (
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-indigo-950 text-indigo-300 font-bold text-xs flex items-center justify-center border border-indigo-800">
                      {m.email?.[0]?.toUpperCase()}
                    </div>
                    <span className="font-bold text-white">{m.full_name || m.email.split("@")[0]}</span>
                  </div>
                ),
              },
              {
                header: "Email Address",
                accessor: (m: any) => (
                  <div className="flex items-center gap-1.5 text-xs text-gray-300">
                    <Mail className="w-3.5 h-3.5 text-gray-400" />
                    <span>{m.email}</span>
                  </div>
                ),
              },
              {
                header: "Assigned RBAC Role",
                accessor: (m: any) => (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-950/70 text-indigo-300 border border-indigo-800/60">
                    <Shield className="w-3.5 h-3.5 text-indigo-400" /> {m.role}
                  </span>
                ),
              },
              {
                header: "Joined Date",
                accessor: (m: any) => new Date(m.created_at).toLocaleDateString(),
              },
            ]}
            data={members}
            loading={loading}
            emptyText="No organization members"
            emptySubtext="Invite developers and security engineers to your organization."
          />
        </div>

        {/* RBAC Permission Matrix Reference Card */}
        <div className="glass-card p-5 rounded-xl border border-gray-800 space-y-3">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Role-Based Access Control (RBAC) Matrix</h3>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 text-xs">
            <div className="p-3 bg-gray-900/60 rounded-lg border border-gray-800">
              <span className="font-bold text-indigo-400 block mb-1">Owner</span>
              <p className="text-gray-400">Full tenant control, billing, organization deletion, role updates.</p>
            </div>
            <div className="p-3 bg-gray-900/60 rounded-lg border border-gray-800">
              <span className="font-bold text-blue-400 block mb-1">Admin</span>
              <p className="text-gray-400">Repositories, projects, custom rules, integrations, policies.</p>
            </div>
            <div className="p-3 bg-gray-900/60 rounded-lg border border-gray-800">
              <span className="font-bold text-amber-400 block mb-1">Security</span>
              <p className="text-gray-400">Policies, baselines, suppressions, scans, audit logs.</p>
            </div>
            <div className="p-3 bg-gray-900/60 rounded-lg border border-gray-800">
              <span className="font-bold text-emerald-400 block mb-1">Developer</span>
              <p className="text-gray-400">Scan ingestion, finding status updates, baseline updates.</p>
            </div>
            <div className="p-3 bg-gray-900/60 rounded-lg border border-gray-800">
              <span className="font-bold text-gray-400 block mb-1">Viewer</span>
              <p className="text-gray-400">Read-only access to scans, findings, reports, and dashboards.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
