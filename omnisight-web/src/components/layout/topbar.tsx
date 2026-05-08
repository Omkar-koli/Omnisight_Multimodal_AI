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
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/90 backdrop-blur-sm px-4 md:px-6">
      {mobileNav}

      <div className="flex-1 min-w-0">
        <h1 className="truncate text-sm font-semibold leading-tight text-foreground">
          Inventory Decision Workspace
        </h1>
        <p className="hidden mt-0.5 text-xs leading-tight text-muted-foreground sm:block">
          Multimodal restocking signals · rules + retrieval + AI
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-1.5 rounded-full border border-primary/30 bg-primary/8 px-2.5 py-1 sm:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-primary pulse-dot" />
          <span className="text-[10px] font-medium uppercase tracking-wider text-primary">
            Live
          </span>
        </div>

        <div className="hidden text-right sm:block">
          <div className="text-xs font-semibold leading-tight text-foreground">
            {session?.user?.name ?? "Unknown User"}
          </div>
          <div className="text-[10px] uppercase tracking-wider leading-tight text-muted-foreground">
            {session?.user?.role ?? "viewer"}
          </div>
        </div>

        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-foreground text-background text-xs font-semibold">
          {initials}
        </div>

        <LogoutButton />
      </div>
    </header>
  );
}
