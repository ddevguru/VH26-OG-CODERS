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
    <header className="h-16 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-8 flex items-center justify-between sticky top-0 z-20 shadow-2xs">
      {/* Left: Org Indicator & Quick Search */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs font-bold text-slate-800 hover:border-emerald-300 transition-all cursor-pointer">
          <Building2 className="w-4 h-4 text-emerald-600" />
          <span>{currentOrg}</span>
        </div>

        <div className="hidden lg:flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-500 w-64">
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span>Search repositories or findings...</span>
        </div>
      </div>

      {/* Right: Role, Notifications, Profile */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800">
          <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
          <span>Role: {role}</span>
        </div>

        <div className="flex items-center gap-3 border-l border-slate-200/80 pl-4">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-600 p-[1px] shadow-2xs">
            <div className="w-full h-full rounded-full bg-emerald-50 flex items-center justify-center text-xs font-extrabold text-emerald-800">
              {profile?.email?.[0]?.toUpperCase() || "A"}
            </div>
          </div>

          <div className="hidden md:block text-left">
            <p className="text-xs font-bold text-slate-900">{profile?.full_name || "Alice Acme"}</p>
            <p className="text-[10px] text-slate-500 font-semibold">{profile?.email || "admin@acme.com"}</p>
          </div>

          <button
            onClick={handleLogout}
            title="Sign out"
            className="p-2 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};

