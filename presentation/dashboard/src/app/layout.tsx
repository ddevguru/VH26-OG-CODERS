import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "LeakGuard — Static Resource Lifetime Analysis",
  description: "Enterprise AST-Based Static Resource Lifetime & Control-Flow Leak Protection",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="bg-[#f8fafc] text-slate-900 min-h-screen antialiased flex selection:bg-emerald-500/20 selection:text-emerald-800">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 bg-ambient-glow">
          <Header />
          <main className="p-8 max-w-[1600px] w-full mx-auto flex-1 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}

