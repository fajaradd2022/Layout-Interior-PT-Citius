"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft, KeyRound, Plug, Map, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/settings/users", label: "Users", icon: Users },
  { href: "/settings", label: "API", icon: KeyRound },
  { href: "/settings/mcp", label: "Instance-level MCP", icon: Plug },
];

export function SettingsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="flex w-64 shrink-0 flex-col border-r bg-card">
        <Link href="/" className="flex h-14 items-center gap-2 border-b px-4 text-base font-semibold hover:bg-muted">
          <ArrowLeft className="size-4" /> Settings
        </Link>
        <nav className="grid gap-0.5 p-2">
          {NAV.map((n) => {
            const Icon = n.icon;
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  active ? "bg-accent font-medium text-accent-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="size-4" /> {n.label}
              </Link>
            );
          })}
          <Link
            href="/"
            className="mt-2 flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Map className="size-4" /> Kembali ke Design Tool
          </Link>
        </nav>
        <div className="mt-auto px-4 py-3 text-xs text-[#00b386]">Layout Interior PT Citius</div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-5xl px-8 py-12">{children}</div>
      </main>
    </div>
  );
}
