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
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
          <Users className="w-6 h-6 text-emerald-600" /> Teams & Organization Members
        </h1>
        <p className="text-xs text-slate-500 font-semibold mt-1">
          Manage team access controls and Role-Based Access Control (RBAC) roles.
        </p>
      </div>

      <div className="space-y-6">
        <div>
          <h2 className="text-base font-extrabold text-slate-900 mb-3">Organization Members & RBAC Roles</h2>
          <DataTable
            columns={[
              {
                header: "Member Name",
                accessor: (m: any) => (
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 font-extrabold text-xs flex items-center justify-center border border-emerald-200">
                      {m.email?.[0]?.toUpperCase()}
                    </div>
                    <span className="font-bold text-slate-900 text-xs">{m.full_name || m.email.split("@")[0]}</span>
                  </div>
                ),
              },
              {
                header: "Email Address",
                accessor: (m: any) => (
                  <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <span>{m.email}</span>
                  </div>
                ),
              },
              {
                header: "Assigned RBAC Role",
                accessor: (m: any) => (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-200 uppercase">
                    <Shield className="w-3.5 h-3.5 text-emerald-600" /> {m.role}
                  </span>
                ),
              },
              {
                header: "Joined Date",
                accessor: (m: any) => (
                  <span className="text-xs text-slate-500 font-semibold">
                    {new Date(m.created_at).toLocaleDateString()}
                  </span>
                ),
              },
            ]}
            data={members}
            loading={loading}
            emptyText="No organization members"
            emptySubtext="Invite developers and security engineers to your organization."
          />
        </div>

        {/* RBAC Permission Matrix Reference Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-xs font-extrabold text-slate-900 uppercase tracking-wider">Role-Based Access Control (RBAC) Matrix</h3>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="font-extrabold text-emerald-800 block mb-1">Owner</span>
              <p className="text-slate-600 text-[11px]">Full tenant control, billing, organization deletion, role updates.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="font-extrabold text-teal-800 block mb-1">Admin</span>
              <p className="text-slate-600 text-[11px]">Repositories, projects, custom rules, integrations, policies.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="font-extrabold text-indigo-800 block mb-1">Security</span>
              <p className="text-slate-600 text-[11px]">Policies, baselines, suppressions, scans, audit logs.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="font-extrabold text-amber-800 block mb-1">Developer</span>
              <p className="text-slate-600 text-[11px]">Scan ingestion, finding status updates, baseline updates.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="font-extrabold text-slate-700 block mb-1">Viewer</span>
              <p className="text-slate-600 text-[11px]">Read-only access to scans, findings, reports, and dashboards.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

