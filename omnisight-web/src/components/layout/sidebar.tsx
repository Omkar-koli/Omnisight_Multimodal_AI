"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  LayoutDashboard,
  PackageSearch,
  ClipboardList,
  Activity,
  RefreshCcw,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/products", icon: PackageSearch, label: "Products" },
  { href: "/monitoring", icon: Activity, label: "Monitoring" },
  { href: "/reviews", icon: ClipboardList, label: "Reviews" },
  { href: "/jobs", icon: RefreshCcw, label: "Jobs" },
];

interface SidebarProps {
  onClose?: () => void;
  isMobile?: boolean;
}

export function Sidebar({ onClose, isMobile }: SidebarProps) {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <aside className="flex h-full flex-col bg-sidebar border-r border-sidebar-border">
      {/* Brand */}
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background">
            <Boxes className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight text-sidebar-foreground">
              OmniSight
            </div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Decision Intelligence
            </div>
          </div>
        </div>

        {isMobile && onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground"
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-3">
        <div className="mb-2 mt-1 px-3 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          Workspace
        </div>

        <div className="space-y-0.5">
          {navItems.map(({ href, icon: Icon, label }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={cn(
                  "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-foreground/95 text-background"
                    : "text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="flex-1">{label}</span>
                {active ? (
                  <span className="h-1 w-1 rounded-full bg-primary" />
                ) : null}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-4">
        <div className="rounded-md border bg-card px-3 py-2.5">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-primary pulse-dot" />
            <span className="text-[11px] font-medium text-foreground">
              OmniSight v2
            </span>
          </div>
          <div className="mt-1 text-[10px] text-muted-foreground">
            Multimodal · Qdrant · Ollama
          </div>
        </div>
      </div>
    </aside>
  );
}
