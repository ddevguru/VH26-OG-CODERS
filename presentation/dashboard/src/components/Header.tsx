"use client";

import React, { useEffect, useState } from "react";
import { User, Shield, Building2, LogOut } from "lucide-react";
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
      window.location.reload();
    }
  };

  const currentOrg = profile?.organizations?.[0]?.organization_name || "Acme Security";

  return (
    <header className="h-16 bg-[#0d1322]/80 backdrop-blur-md border-b border-gray-800/80 px-6 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-sm">
          <Building2 className="w-4 h-4 text-indigo-400" />
          <span className="font-semibold text-gray-200">{currentOrg}</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-950/60 border border-indigo-800/40 text-xs font-semibold text-indigo-300">
          <Shield className="w-3.5 h-3.5 text-indigo-400" />
          <span>Role: {role}</span>
        </div>

        <div className="flex items-center gap-3 border-l border-gray-800 pl-4">
          <div className="w-8 h-8 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-xs font-bold text-gray-300">
            {profile?.email?.[0]?.toUpperCase() || "A"}
          </div>
          <div className="hidden md:block text-left">
            <p className="text-xs font-semibold text-gray-200">{profile?.full_name || "Alice Acme"}</p>
            <p className="text-[10px] text-gray-400">{profile?.email || "admin@acme.com"}</p>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="p-1.5 text-gray-400 hover:text-red-400 rounded-lg hover:bg-gray-800/50 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
