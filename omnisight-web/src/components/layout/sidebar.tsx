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
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary shadow-sm">
            <Boxes className="h-4 w-4 text-primary-foreground" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-bold tracking-tight text-sidebar-foreground">
              OmniSight
            </div>
            <div className="text-[10px] text-muted-foreground">
              Intelligence Platform
            </div>
          </div>
        </div>

        {/* Close button — mobile only */}
        {isMobile && onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
        <div className="mb-2 mt-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Main Menu
        </div>

        {navItems.map(({ href, icon: Icon, label }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0 transition-transform duration-150 group-hover:scale-110",
                  active ? "text-primary-foreground" : ""
                )}
              />
              <span className="flex-1">{label}</span>
              {active && (
                <span className="h-1.5 w-1.5 rounded-full bg-primary-foreground/60" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer badge */}
      <div className="border-t border-sidebar-border p-4">
        <div className="rounded-xl bg-primary/8 border border-primary/15 px-3 py-2.5">
          <div className="text-xs font-semibold text-foreground">OmniSight v2</div>
          <div className="mt-0.5 text-[10px] text-muted-foreground">
            Multimodal AI · Qdrant · Ollama
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-[10px] text-emerald-600 font-medium">All systems operational</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
