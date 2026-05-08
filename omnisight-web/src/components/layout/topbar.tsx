import { ReactNode } from "react";
import { auth } from "@/auth";
import { LogoutButton } from "@/components/auth/logout-button";

export async function Topbar({ mobileNav }: { mobileNav?: ReactNode }) {
  const session = await auth();
  const initials = (session?.user?.name ?? "?")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/95 backdrop-blur-sm px-4 md:px-6">
      {/* Mobile hamburger slot */}
      {mobileNav}

      {/* Title block */}
      <div className="flex-1 min-w-0">
        <h1 className="truncate text-sm font-semibold text-foreground leading-tight">
          Enterprise Inventory Intelligence
        </h1>
        <p className="hidden text-xs text-muted-foreground sm:block leading-tight mt-0.5">
          Multimodal restocking decisions powered by rules, retrieval, and AI
        </p>
      </div>

      {/* Right slot */}
      <div className="flex items-center gap-3">
        {/* Status indicator */}
        <div className="hidden items-center gap-1.5 rounded-full border bg-emerald-50 px-2.5 py-1 sm:flex dark:bg-emerald-950/30">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 pulse-dot" />
          <span className="text-[10px] font-medium text-emerald-700 dark:text-emerald-400">
            Live
          </span>
        </div>

        {/* User info */}
        <div className="hidden text-right sm:block">
          <div className="text-xs font-semibold text-foreground leading-tight">
            {session?.user?.name ?? "Unknown User"}
          </div>
          <div className="text-[10px] text-muted-foreground leading-tight capitalize">
            {session?.user?.role ?? "viewer"}
          </div>
        </div>

        {/* Avatar */}
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold shadow-sm">
          {initials}
        </div>

        <LogoutButton />
      </div>
    </header>
  );
}
