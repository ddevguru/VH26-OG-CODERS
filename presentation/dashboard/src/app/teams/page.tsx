"use client";

import React, { useEffect, useState } from "react";
import { Users, UserPlus, Shield, Mail, X, CheckCircle, UserCheck } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { api } from "@/lib/api";

export default function TeamsPage() {
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);

  // Invite Modal State
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("Developer");
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  const loadData = async () => {
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
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    try {
      setSubmitting(true);
      const newMember = await api.inviteMember(email, fullName, role);
      setSuccessMsg(`✓ Teammate ${email} invited successfully with ${role} role!`);
      
      // Update local table state
      setMembers((prev) => [newMember, ...prev.filter((m) => m.email !== newMember.email)]);
      
      setTimeout(() => {
        setIsInviteOpen(false);
        setSuccessMsg("");
        setEmail("");
        setFullName("");
        setRole("Developer");
      }, 1500);
    } catch (err: any) {
      alert(`Invite Error: ${err.message || "Failed to invite member"}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      const updated = await api.updateMemberRole(userId, newRole);
      setMembers((prev) => prev.map((m) => (m.user_id === userId ? { ...m, role: updated.role } : m)));
    } catch (err: any) {
      alert(`Role Update Error: ${err.message || "Failed to update role"}`);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header with Invite Teammate Action */}
      <div className="border-b border-slate-200/80 pb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-emerald-600" /> Teams & Organization Members
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Manage team access controls, invite teammates, and assign Role-Based Access Control (RBAC) permissions.
          </p>
        </div>

        <button
          onClick={() => setIsInviteOpen(true)}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-extrabold text-xs flex items-center gap-2 shadow-md shadow-emerald-600/20 transition cursor-pointer active:scale-98"
        >
          <UserPlus className="w-4 h-4" />
          <span>Invite Teammate</span>
        </button>
      </div>

      <div className="space-y-6">
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-extrabold text-slate-900">Organization Members & RBAC Roles</h2>
            <span className="text-xs font-bold text-slate-500">
              Total Members: <span className="text-slate-900 font-extrabold">{members.length}</span>
            </span>
          </div>

          <DataTable
            columns={[
              {
                header: "Member Name",
                accessor: (m: any) => (
                  <div className="flex items-center gap-2.5">
                    <div className="w-8.5 h-8.5 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-600 p-[1px] shadow-2xs">
                      <div className="w-full h-full rounded-full bg-emerald-50 text-emerald-900 font-black text-xs flex items-center justify-center">
                        {m.email?.[0]?.toUpperCase()}
                      </div>
                    </div>
                    <div>
                      <span className="font-extrabold text-slate-900 text-xs block">{m.full_name || m.email.split("@")[0]}</span>
                      <span className="text-[10px] text-slate-400 font-semibold">User ID: {m.user_id?.substring(0, 8)}...</span>
                    </div>
                  </div>
                ),
              },
              {
                header: "Email Address",
                accessor: (m: any) => (
                  <div className="flex items-center gap-1.5 text-xs text-slate-700 font-semibold">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <span>{m.email}</span>
                  </div>
                ),
              },
              {
                header: "Assigned RBAC Role",
                accessor: (m: any) => (
                  <select
                    value={m.role}
                    onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                    className="px-3 py-1 rounded-xl bg-slate-50 border border-slate-200 text-xs font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-2xs cursor-pointer"
                  >
                    <option value="Owner">Owner</option>
                    <option value="Admin">Admin</option>
                    <option value="Security">Security</option>
                    <option value="Developer">Developer</option>
                    <option value="Viewer">Viewer</option>
                  </select>
                ),
              },
              {
                header: "Joined Date",
                accessor: (m: any) => (
                  <span className="text-xs text-slate-500 font-semibold">
                    {m.created_at ? new Date(m.created_at).toLocaleDateString() : "Just now"}
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

      {/* Invite Teammate Modal */}
      {isInviteOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-200/80 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 border border-emerald-200 text-emerald-800 flex items-center justify-center font-extrabold shadow-2xs">
                  <UserPlus className="w-5 h-5 text-emerald-700" />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-slate-900 tracking-tight">Invite Teammate</h3>
                  <p className="text-xs text-slate-500 font-semibold">Add a developer or security engineer to your team.</p>
                </div>
              </div>

              <button
                onClick={() => setIsInviteOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-700 rounded-xl hover:bg-slate-100 transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleInviteSubmit} className="p-6 space-y-4 text-xs">
              {successMsg && (
                <div className="p-3.5 rounded-xl bg-emerald-100 border border-emerald-300 text-emerald-900 font-extrabold flex items-center gap-2 text-xs">
                  <CheckCircle className="w-4 h-4 text-emerald-700" />
                  <span>{successMsg}</span>
                </div>
              )}

              <div>
                <label className="block text-slate-700 font-extrabold mb-1.5">Teammate Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="alex.developer@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-2xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-extrabold mb-1.5">Full Name (Optional)</label>
                <input
                  type="text"
                  placeholder="Alex Rivera"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-2xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-extrabold mb-1.5">Assigned RBAC Role *</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-2xs bg-white cursor-pointer"
                >
                  <option value="Owner">Owner - Full Organization & Billing Control</option>
                  <option value="Admin">Admin - Repositories, Rules & Integrations</option>
                  <option value="Security">Security - Policies, Suppressions & Audits</option>
                  <option value="Developer">Developer - Scans & Finding Remediation</option>
                  <option value="Viewer">Viewer - Read-Only Access</option>
                </select>
              </div>

              {/* Form Buttons */}
              <div className="pt-4 border-t border-slate-200/80 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsInviteOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition cursor-pointer disabled:opacity-50 flex items-center gap-2"
                >
                  <UserCheck className="w-4 h-4" />
                  <span>{submitting ? "Inviting Teammate..." : "Send Invitation & Add Member"}</span>
                </button>
              </div>
            </form>

          </div>
        </div>
      )}
    </div>
  );
}

