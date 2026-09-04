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
    <aside className="w-64 bg-[#0d1322] border-r border-gray-800/80 flex flex-col justify-between h-screen sticky top-0">
      <div>
        <div className="p-5 flex items-center gap-3 border-b border-gray-800/80">
          <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-wide">LeakGuard</h1>
            <p className="text-xs text-gray-400 font-medium">SaaS Control Plane</p>
          </div>
        </div>

        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/30 shadow-sm"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/40"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-gray-400"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-gray-800/80 text-xs text-gray-400 text-center">
        <p className="font-medium">LeakGuard v0.1.0 Commercial</p>
        <p className="text-gray-400">AST Static Resource Analysis</p>
      </div>
    </aside>
  );
};
