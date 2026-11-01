"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Plus, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, match: (p: string) => p === "/" || p.startsWith("/runs") },
  { href: "/new", label: "New analysis", icon: Plus, match: (p: string) => p.startsWith("/new") },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 flex h-dvh w-16 shrink-0 flex-col border-r border-slate-200 bg-white lg:w-60">
      <Link href="/" className="flex h-14 items-center gap-2.5 border-b border-slate-200 px-4" aria-label="Evidence Pipeline home">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-indigo-600 text-white">
          <ShieldCheck className="size-4.5" aria-hidden />
        </span>
        <span className="hidden text-sm font-semibold tracking-tight text-slate-900 lg:block">Evidence Pipeline</span>
      </Link>
      <nav aria-label="Main" className="flex flex-col gap-1 p-2 lg:p-3">
        {NAV.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              title={item.label}
              className={cn(
                "flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                active ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
              )}
            >
              <Icon className="size-4.5 shrink-0" aria-hidden />
              <span className="hidden lg:inline">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto hidden border-t border-slate-200 p-4 text-xs leading-relaxed text-slate-500 lg:block">
        Public-profile evidence only. Every figure traces back to a frozen, hash-verified snapshot.
      </div>
    </aside>
  );
}
