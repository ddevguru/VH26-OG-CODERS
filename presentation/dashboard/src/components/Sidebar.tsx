"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderGit2,
  Activity,
  AlertTriangle,
  BookOpen,
  ShieldCheck,
  BookmarkCheck,
  Users,
  Sliders,
  History,
  Settings,
  ShieldAlert,
  Zap,
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Repositories", href: "/repositories", icon: FolderGit2 },
  { name: "Scans", href: "/scans", icon: Activity },
  { name: "Findings", href: "/findings", icon: AlertTriangle },
  { name: "Rules", href: "/rules", icon: BookOpen },
  { name: "Policies", href: "/policies", icon: ShieldCheck },
  { name: "Baselines", href: "/baselines", icon: BookmarkCheck },
  { name: "Teams", href: "/teams", icon: Users },
  { name: "Integrations", href: "/integrations", icon: Sliders },
  { name: "Audit Logs", href: "/audit-log", icon: History },
  { name: "Settings", href: "/settings", icon: Settings },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-[#080d18]/90 backdrop-blur-xl border-r border-white/[0.06] flex flex-col justify-between h-screen sticky top-0 z-30 select-none">
      <div>
        {/* Brand Header */}
        <div className="px-6 py-5 flex items-center justify-between border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 p-[1px] shadow-[0_0_20px_rgba(99,102,241,0.35)]">
              <div className="w-full h-full bg-[#090d16] rounded-[11px] flex items-center justify-center text-indigo-400">
                <ShieldAlert className="w-5 h-5 text-indigo-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h1 className="font-extrabold text-base text-white tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-400">
                  LeakGuard
                </h1>
                <span className="px-1.5 py-0.5 text-[9px] font-extrabold tracking-widest text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 rounded uppercase">
                  PRO
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">SaaS Control Plane</p>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1 mt-2">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group relative flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                  isActive
                    ? "glass-nav-active text-white shadow-lg shadow-indigo-500/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]"
                }`}
              >
                <Icon className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isActive ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-300"}`} />
                <span>{item.name}</span>

                {isActive && (
                  <div className="absolute right-2.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.9)]" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Status */}
      <div className="p-4 border-t border-white/[0.06] bg-white/[0.01]">
        <div className="glass-card p-3 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <div className="absolute -inset-0.5 rounded-full bg-emerald-500/50 animate-ping" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-slate-200">Engine Active</p>
              <p className="text-[10px] text-slate-400">AST Static Mode</p>
            </div>
          </div>
          <Zap className="w-3.5 h-3.5 text-emerald-400" />
        </div>
      </div>
    </aside>
  );
};
