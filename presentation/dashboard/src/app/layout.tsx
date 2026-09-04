import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "LeakGuard Commercial SaaS Dashboard",
  description: "AST-Based Static Resource Leak Detection Control Plane",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0b0f17] text-gray-100 min-h-screen antialiased flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Header />
          <main className="p-8 flex-1 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
