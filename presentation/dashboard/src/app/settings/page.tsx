"use client";

import React, { useEffect, useState } from "react";
import { Settings, Shield, Building2, Key, Copy, Check } from "lucide-react";
import { api, UserProfile } from "@/lib/api";

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [copied, setCopied] = useState(false);
  const [token, setToken] = useState("");
  const [orgId, setOrgId] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      setToken(localStorage.getItem("leakguard_token") || "leakguard-sample-token-12345");
      setOrgId(localStorage.getItem("leakguard_org_id") || "org-1234-5678");
    }
    api.getMe().then(setProfile).catch(() => {});
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
          <Settings className="w-6 h-6 text-emerald-600" /> Control Plane Settings
        </h1>
        <p className="text-xs text-slate-500 font-semibold mt-1">
          Manage your organization profile, API keys, authentication credentials, and CLI sync settings.
        </p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6 text-slate-900">
        {/* Organization Info */}
        <div className="space-y-4">
          <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">
            <Building2 className="w-5 h-5 text-emerald-600" /> Organization Profile
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-slate-500 block font-bold">Organization Name</span>
              <span className="text-slate-900 text-sm font-extrabold mt-1 block">
                {profile?.organizations?.[0]?.organization_name || "Acme Corp"}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block font-bold">Organization ID (Tenant)</span>
              <span className="font-mono-code text-emerald-700 text-xs font-bold mt-1 block">
                {orgId}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block font-bold">Current User Email</span>
              <span className="text-slate-900 font-bold mt-1 block">{profile?.email || "admin@acme.com"}</span>
            </div>

            <div>
              <span className="text-slate-500 block font-bold">Your RBAC Role</span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 mt-1 rounded-full text-[10px] font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-200 uppercase">
                <Shield className="w-3.5 h-3.5 text-emerald-600" />
                {profile?.organizations?.[0]?.role || "Owner"}
              </span>
            </div>
          </div>
        </div>

        {/* API Credentials */}
        <div className="space-y-4 pt-4 border-t border-slate-200">
          <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">
            <Key className="w-5 h-5 text-emerald-600" /> CLI & CI/CD API Bearer Token
          </h2>

          <p className="text-xs text-slate-600 font-medium leading-relaxed">
            Use this token to authenticate local CLI scans and CI/CD pipelines when running `leakguard upload`.
          </p>

          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 flex items-center justify-between font-mono-code text-xs text-emerald-800 font-bold">
            <span className="truncate max-w-lg">{token}</span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold transition-colors cursor-pointer shadow-xs"
            >
              {copied ? <Check className="w-4 h-4 text-white" /> : <Copy className="w-4 h-4" />}
              {copied ? "Copied!" : "Copy Token"}
            </button>
          </div>
        </div>

        {/* Local CLI Command Reference */}
        <div className="space-y-3 pt-4 border-t border-slate-200 text-xs">
          <h3 className="font-extrabold text-slate-900">CLI Sync Execution Snippet</h3>
          <pre className="bg-slate-900 p-4 rounded-xl border border-slate-800 text-xs font-mono-code text-emerald-400 overflow-x-auto">
{`# Run local scan and push metadata to control plane
leakguard upload . \\
  --repo "backend-service" \\
  --url "http://127.0.0.1:8000" \\
  --token "${token.substring(0, 20)}..."`}
          </pre>
        </div>
      </div>
    </div>
  );
}

