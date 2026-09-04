"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Lock, Mail, ArrowRight, AlertCircle, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    // Clear any legacy or invalid demo tokens when landing on login page
    if (typeof window !== "undefined") {
      const currentToken = localStorage.getItem("leakguard_token");
      if (!currentToken || currentToken.startsWith("demo_") || currentToken.startsWith("local_")) {
        localStorage.removeItem("leakguard_token");
        localStorage.removeItem("leakguard_org_id");
        localStorage.removeItem("leakguard_role");
        localStorage.removeItem("leakguard_email");
      }
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.login(email, password);
      router.push("/");
    } catch (err: any) {
      // If login fails (e.g. account not created yet), attempt auto-signup on server
      try {
        const username = email.split("@")[0] || "User";
        const safePassword = password.length >= 8 ? password : `${password}12345678`;
        await api.signup(email, safePassword, username, `${username}'s Org`);
        await api.login(email, safePassword);
        router.push("/");
        return;
      } catch (signupErr: any) {
        setError(err.message || signupErr.message || "Failed to log in. Please check your credentials.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 glass-card p-10 rounded-3xl border border-white/[0.08] shadow-2xl relative overflow-hidden">
        {/* Glow Background Elements */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-indigo-500/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-purple-500/15 rounded-full blur-3xl pointer-events-none" />

        <div className="text-center relative">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 p-[1px] shadow-[0_0_25px_rgba(99,102,241,0.3)] mb-4">
            <div className="w-full h-full bg-[#060911] rounded-[15px] flex items-center justify-center text-indigo-400">
              <Shield className="w-8 h-8" />
            </div>
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-400">
            LeakGuard Control Plane
          </h2>
          <p className="mt-1.5 text-xs text-slate-400 font-medium">
            Enter your credentials to access static leak detection telemetry
          </p>
        </div>

        {error && (
          <div className="rounded-2xl bg-rose-500/10 border border-rose-500/20 p-4 text-xs text-rose-400 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@leakguard.io"
                  className="block w-full pl-10 pr-4 py-3 bg-[#060911] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-xs font-medium transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-10 pr-4 py-3 bg-[#060911] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-xs font-medium transition-all"
                />
              </div>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3.5 px-4 border border-indigo-500/30 text-xs font-bold rounded-xl text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 transition shadow-lg shadow-indigo-600/25 disabled:opacity-50"
            >
              {loading ? "Authenticating..." : "Sign In to Control Plane"}
              <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </form>

        <div className="text-center pt-2 border-t border-white/[0.06]">
          <p className="text-xs text-slate-400">
            Don't have an account?{" "}
            <a href="/register" className="text-indigo-400 hover:text-indigo-300 font-bold underline">
              Register New Organization
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
