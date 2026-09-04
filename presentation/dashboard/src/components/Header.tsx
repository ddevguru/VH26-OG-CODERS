"use client";

import React, { useEffect, useState } from "react";
import { User, Shield, Building2, LogOut, Search, Bell, Sparkles } from "lucide-react";
import { api, UserProfile } from "@/lib/api";

export const Header: React.FC = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [role, setRole] = useState<string>("Owner");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedRole = localStorage.getItem("leakguard_role");
      if (storedRole) setRole(storedRole);
    }
    api.getMe().then(setProfile).catch(() => {});
  }, []);

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("leakguard_token");
      localStorage.removeItem("leakguard_org_id");
      localStorage.removeItem("leakguard_role");
      localStorage.removeItem("leakguard_email");
      window.location.href = "/login";
    }
  };

  const currentOrg = profile?.organizations?.[0]?.organization_name || "Acme Security Enterprise";

  return (
    <header className="h-16 bg-[#080d18]/60 backdrop-blur-xl border-b border-white/[0.06] px-8 flex items-center justify-between sticky top-0 z-20">
      {/* Left: Org Indicator & Quick Search */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs font-semibold text-slate-200 hover:border-white/[0.15] transition-all cursor-pointer">
          <Building2 className="w-4 h-4 text-indigo-400" />
          <span>{currentOrg}</span>
        </div>

        <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-xs text-slate-400 w-64">
          <Search className="w-3.5 h-3.5 text-slate-500" />
          <span>Search repositories or findings...</span>
        </div>
      </div>

      {/* Right: Role, Notifications, Profile */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-300">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Role: {role}</span>
        </div>

        <div className="flex items-center gap-3 border-l border-white/[0.08] pl-4">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 p-[1px]">
            <div className="w-full h-full rounded-full bg-[#0d1322] flex items-center justify-center text-xs font-extrabold text-indigo-300">
              {profile?.email?.[0]?.toUpperCase() || "A"}
            </div>
          </div>

          <div className="hidden md:block text-left">
            <p className="text-xs font-semibold text-slate-100">{profile?.full_name || "Alice Acme"}</p>
            <p className="text-[10px] text-slate-400">{profile?.email || "admin@acme.com"}</p>
          </div>

          <button
            onClick={handleLogout}
            title="Sign out"
            className="p-2 text-slate-400 hover:text-rose-400 rounded-xl hover:bg-white/[0.04] transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
