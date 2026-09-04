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
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Settings className="w-6 h-6 text-indigo-400" /> Control Plane Settings
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Manage your organization profile, API keys, authentication credentials, and CLI sync settings.
        </p>
      </div>

      <div className="glass-card p-6 rounded-2xl border border-gray-800 space-y-6">
        {/* Organization Info */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
            <Building2 className="w-5 h-5 text-indigo-400" /> Organization Profile
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-gray-400 block font-semibold">Organization Name</span>
              <span className="text-gray-200 text-sm font-bold mt-1 block">
                {profile?.organizations?.[0]?.organization_name || "Acme Corp"}
              </span>
            </div>

            <div>
              <span className="text-gray-400 block font-semibold">Organization ID (Tenant)</span>
              <span className="font-mono text-indigo-300 text-xs font-semibold mt-1 block">
                {orgId}
              </span>
            </div>

            <div>
              <span className="text-gray-400 block font-semibold">Current User Email</span>
              <span className="text-gray-200 font-medium mt-1 block">{profile?.email || "admin@acme.com"}</span>
            </div>

            <div>
              <span className="text-gray-400 block font-semibold">Your RBAC Role</span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 mt-1 rounded-full text-xs font-semibold bg-indigo-950/70 text-indigo-300 border border-indigo-800">
                <Shield className="w-3.5 h-3.5 text-indigo-400" />
                {profile?.organizations?.[0]?.role || "Owner"}
              </span>
            </div>
          </div>
        </div>

        {/* API Credentials */}
        <div className="space-y-4 pt-4 border-t border-gray-800">
          <h2 className="text-base font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
            <Key className="w-5 h-5 text-emerald-400" /> CLI & CI/CD API Bearer Token
          </h2>

          <p className="text-xs text-gray-400 leading-relaxed">
            Use this token to authenticate local CLI scans and CI/CD pipelines when running `leakguard upload`.
          </p>

          <div className="bg-gray-950 p-3 rounded-xl border border-gray-800 flex items-center justify-between font-mono text-xs text-emerald-400">
            <span className="truncate max-w-lg">{token}</span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              {copied ? "Copied!" : "Copy Token"}
            </button>
          </div>
        </div>

        {/* Local CLI Command Reference */}
        <div className="space-y-3 pt-4 border-t border-gray-800 text-xs">
          <h3 className="font-bold text-white">CLI Sync Execution Snippet</h3>
          <pre className="bg-gray-950 p-4 rounded-xl border border-gray-800 text-xs font-mono text-gray-300 overflow-x-auto">
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
