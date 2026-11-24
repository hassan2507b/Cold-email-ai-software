"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Mail, BarChart3, Inbox, Send } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: "Send emails", icon: Send },
    { href: "/report", label: "Report", icon: BarChart3 },
    { href: "/emails", label: "Sent emails", icon: Inbox },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm transition-transform group-hover:scale-105">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <span className="font-semibold text-slate-900 tracking-tight text-base sm:text-lg block leading-tight">
              ColdMail AI
            </span>
            <span className="text-xs text-slate-500 font-normal">Automated outreach</span>
          </div>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-50 text-blue-700"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-500"}`} />
                <span className="hidden sm:inline">{item.label}</span>
                <span className="sm:hidden">{item.label.split(" ")[0]}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
