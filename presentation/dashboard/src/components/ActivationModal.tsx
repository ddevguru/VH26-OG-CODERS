"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, LogIn, UserPlus, X, CheckCircle2, ArrowRight, UserCheck, Sparkles, Terminal } from "lucide-react";
import { api, UserProfile } from "@/lib/api";

export const ActivationModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeProfile, setActiveProfile] = useState<UserProfile | null>(null);
  const [cliPort, setCliPort] = useState<string | null>(null);
  const [cliConnected, setCliConnected] = useState(false);

  const sendCliCallback = async (port: string, profile: any) => {
    const token = localStorage.getItem("leakguard_token") || "";
    const orgId = localStorage.getItem("leakguard_org_id") || "";
    const role = localStorage.getItem("leakguard_role") || "Owner";
    const email = profile?.email || localStorage.getItem("leakguard_email") || "dev@leakguard.io";

    const payload = {
      access_token: token,
      organization_id: orgId,
      role: role,
      email: email,
      action: "activate",
    };

    try {
      await fetch(`http://127.0.0.1:${port}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setCliConnected(true);
    } catch (e) {}

    try {
      await fetch(`http://localhost:${port}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setCliConnected(true);
    } catch (e) {}
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const port = params.get("cli_port");
      if (port) setCliPort(port);

      if (params.get("activated") === "true") {
        setIsOpen(true);
        // Check if user is logged in
        api.getMe()
          .then(profile => {
            setActiveProfile(profile);
            if (port) {
              sendCliCallback(port, profile);
            }
          })
          .catch(() => {});
      }
    }
  }, []);

  if (!isOpen) return null;

  const handleClose = async () => {
    if (cliPort && activeProfile) {
      await sendCliCallback(cliPort, activeProfile);
    }
    setIsOpen(false);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("activated");
      url.searchParams.delete("cli_port");
      window.history.replaceState({}, "", url.toString());
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-md animate-in fade-in duration-300">
      <div className="relative w-full max-w-lg overflow-hidden bg-white border border-slate-200 rounded-3xl shadow-2xl p-7 space-y-5 text-slate-900">
        
        {/* Close Button */}
        <button
          onClick={handleClose}
          className="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 transition cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header Badge & Icon */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-600 shadow-md shadow-emerald-600/20 flex items-center justify-center text-white shrink-0">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-widest text-emerald-800 bg-emerald-50 border border-emerald-200">
                ACTIVE GUARDRAIL
              </span>
              <span className="text-xs text-slate-500 font-medium">• CLI Installed</span>
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
              LeakGuard Activated!
            </h2>
          </div>
        </div>

        {/* CLI Port Banner if active */}
        {cliPort && (
          <div className="p-3.5 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center gap-3 text-xs">
            <Terminal className="w-5 h-5 text-indigo-600 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-bold text-indigo-950">CLI Integration Detected</p>
              <p className="text-[11px] text-indigo-700">Connecting CLI on port {cliPort}</p>
            </div>
            {cliConnected && (
              <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-extrabold">
                ✓ Connected
              </span>
            )}
          </div>
        )}

        {/* Info Box */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>GitHub Push Scan & Git Pre-Push Hook Configured</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed pl-6">
            Automatic resource leak detection is now enabled for your repository. Pre-push hooks will intercept and block any unclosed files, DB connections, or socket leaks before code hits GitHub.
          </p>
        </div>

        {/* Active Account Detected Banner */}
        {activeProfile ? (
          <div className="p-4 rounded-2xl bg-emerald-50/90 border border-emerald-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider text-emerald-800 bg-emerald-100 border border-emerald-200 inline-flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-emerald-600" /> Active Session Found
              </span>
              <span className="text-[10px] text-slate-500 font-semibold">Web Account Ready</span>
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
              onClick={handleClose}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-md shadow-emerald-600/20 transition active:scale-95 cursor-pointer"
            >
              <span>Use this account ({activeProfile.full_name || activeProfile.email})</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : null}

        {/* Interactive Action Options */}
        <div className="space-y-3 pt-1">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider text-center">
            {activeProfile ? "Or Choose Another Option" : "Choose an Option to Access Control Plane"}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Sign In Button */}
            <a
              href={cliPort ? `/login?activated=true&cli_port=${cliPort}` : "/login"}
              className="flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-md shadow-emerald-600/20 transition active:scale-95"
            >
              <LogIn className="w-4 h-4" />
              <span>Sign In (Existing)</span>
            </a>

            {/* Sign Up Button */}
            <a
              href={cliPort ? `/register?activated=true&cli_port=${cliPort}` : "/register"}
              className="flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-800 font-semibold text-xs transition active:scale-95"
            >
              <UserPlus className="w-4 h-4 text-emerald-600" />
              <span>Sign Up (New User)</span>
            </a>
          </div>

          {/* Direct Dashboard Link */}
          <button
            onClick={handleClose}
            className="w-full flex items-center justify-center gap-1.5 pt-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition cursor-pointer"
          >
            <span>Continue as Guest / Dismiss</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

      </div>
    </div>
  );
};
