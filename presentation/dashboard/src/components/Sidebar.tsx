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
    <aside className="w-64 bg-white border-r border-slate-200/80 flex flex-col justify-between h-screen sticky top-0 z-30 select-none shadow-2xs">
      <div>
        {/* Brand Header */}
        <div className="px-6 py-5 flex items-center justify-between border-b border-slate-200/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 p-[1px] shadow-sm shadow-emerald-600/20">
              <div className="w-full h-full bg-emerald-50 rounded-[11px] flex items-center justify-center text-emerald-700">
                <ShieldAlert className="w-5 h-5 text-emerald-600" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h1 className="font-extrabold text-base text-slate-900 tracking-tight">
                  LeakGuard
                </h1>
                <span className="px-1.5 py-0.5 text-[9px] font-extrabold tracking-widest text-emerald-800 bg-emerald-100 border border-emerald-200 rounded uppercase">
                  PRO
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-semibold">SaaS Control Plane</p>
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
                className={`group relative flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                  isActive
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200/80 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                <Icon className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isActive ? "text-emerald-600" : "text-slate-400 group-hover:text-slate-600"}`} />
                <span>{item.name}</span>

                {isActive && (
                  <div className="absolute right-2.5 w-1.5 h-1.5 rounded-full bg-emerald-600 shadow-xs" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Status */}
      <div className="p-4 border-t border-slate-200/80 bg-slate-50/50">
        <div className="bg-white p-3 rounded-xl border border-slate-200/80 flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <div className="absolute -inset-0.5 rounded-full bg-emerald-500/50 animate-ping" />
            </div>
            <div>
              <p className="text-[11px] font-extrabold text-slate-900">Engine Active</p>
              <p className="text-[10px] text-slate-500 font-semibold">AST Static Mode</p>
            </div>
          </div>
          <Zap className="w-3.5 h-3.5 text-emerald-600" />
        </div>
      </div>
    </aside>
  );
};

