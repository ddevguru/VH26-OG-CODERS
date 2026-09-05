"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Shield, Lock, Mail, User, Building, ArrowRight, AlertCircle, Sparkles, UserCheck, Terminal } from "lucide-react";
import { api, UserProfile } from "@/lib/api";

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const cliPort = searchParams.get("cli_port");

  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeProfile, setActiveProfile] = useState<UserProfile | null>(null);
  const [cliSent, setCliSent] = useState(false);

  const sendCliAuthCallback = async (port: string, data: any) => {
    const token = localStorage.getItem("leakguard_token") || data?.access_token || "";
    const orgId = localStorage.getItem("leakguard_org_id") || data?.organization_id || "";
    const role = localStorage.getItem("leakguard_role") || data?.role || "Owner";
    const userEmail = data?.email || localStorage.getItem("leakguard_email") || email || "admin@leakguard.io";

    const payload = {
      access_token: token,
      organization_id: orgId,
      role: role,
      email: userEmail,
      action: "register",
    };

    try {
      await fetch(`http://127.0.0.1:${port}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setCliSent(true);
    } catch (e) {}

    try {
      await fetch(`http://localhost:${port}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setCliSent(true);
    } catch (e) {}
  };

  useEffect(() => {
    // Check if user is already logged in on web
    if (typeof window !== "undefined") {
      const currentToken = localStorage.getItem("leakguard_token");
      if (currentToken && !currentToken.startsWith("demo_") && !currentToken.startsWith("local_")) {
        api.getMe()
          .then(profile => {
            setActiveProfile(profile);
            if (cliPort) {
              sendCliAuthCallback(cliPort, profile);
            }
          })
          .catch(() => {});
      }
    }
  }, [cliPort]);

  const handleUseAccount = async () => {
    if (cliPort && activeProfile) {
      await sendCliAuthCallback(cliPort, activeProfile);
    }
    router.push("/");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.signup(email, password, fullName, orgName);
      const res = await api.login(email, password);
      if (cliPort) {
        await sendCliAuthCallback(cliPort, res);
      }
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Failed to create account. Please check inputs (password min 8 characters).");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-[#f8fafc]">
      <div className="max-w-md w-full space-y-6 bg-white border border-slate-200 shadow-xl rounded-3xl p-8 relative overflow-hidden text-slate-900">
        
        <div className="text-center relative">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-600 text-white shadow-md shadow-emerald-600/20 mb-3">
            <Shield className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Create Organization Account
          </h2>
          <p className="mt-1 text-xs text-slate-500 font-medium">
            Register your organization for automated static leak detection
          </p>
        </div>

        {/* CLI Port Banner if active */}
        {cliPort && (
          <div className="p-3.5 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center gap-3 text-xs">
            <Terminal className="w-5 h-5 text-indigo-600 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-bold text-indigo-950">CLI Activation Requested</p>
              <p className="text-[11px] text-indigo-700">Connecting authentication to CLI on port {cliPort}</p>
            </div>
            {cliSent && (
              <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-extrabold">
                ✓ Connected
              </span>
            )}
          </div>
        )}

        {/* Existing Account Card if logged in on Web */}
        {activeProfile && (
          <div className="p-4 rounded-2xl bg-emerald-50/90 border border-emerald-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider text-emerald-800 bg-emerald-100 border border-emerald-200 inline-flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-emerald-600" /> Web Session Active
              </span>
              <span className="text-[10px] text-slate-500 font-semibold">Already Logged In</span>
            </div>

            <div className="flex items-center gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
              <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center text-white font-extrabold text-sm shrink-0 shadow-xs">
                {activeProfile.email?.[0]?.toUpperCase() || "U"}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-900 truncate">
                  {activeProfile.full_name || activeProfile.email.split("@")[0]}
                </p>
                <p className="text-[11px] text-slate-500 font-medium truncate">
                  {activeProfile.email}
                </p>
              </div>
              <UserCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            </div>

            <button
              type="button"
              onClick={handleUseAccount}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-md shadow-emerald-600/20 transition active:scale-95 cursor-pointer"
            >
              <span>Use this account</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <div className="relative my-2">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-emerald-50 px-2 text-slate-500 font-bold">Or register new account</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-2xl bg-rose-50 border border-rose-200 p-3.5 text-xs text-rose-700 flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        <form className="space-y-3.5" onSubmit={handleSubmit}>
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
              Full Name
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <User className="h-4 w-4" />
              </div>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Alice Acme"
                className="block w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-xs font-medium transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
              Organization Name
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Building className="h-4 w-4" />
              </div>
              <input
                type="text"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Acme Security Enterprise"
                className="block w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-xs font-medium transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
              Work Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail className="h-4 w-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@leakguard.io"
                className="block w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-xs font-medium transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
              Master Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="h-4 w-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="•••••••• (Min 8 characters)"
                className="block w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white text-xs font-medium transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-md shadow-emerald-600/20 transition active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            <span>{loading ? "Creating Organization Account..." : "Create Account & Get API Key"}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="text-center text-xs text-slate-500">
          Already registered?{" "}
          <a href={cliPort ? `/login?activated=true&cli_port=${cliPort}` : "/login"} className="text-emerald-700 font-bold hover:underline">
            Sign in here
          </a>
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs font-bold text-slate-500">Loading Register...</div>}>
      <RegisterContent />
    </Suspense>
  );
}
