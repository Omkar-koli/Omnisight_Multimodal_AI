import { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { MobileNav } from "./mobile-nav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[260px_1fr]">
        {/* Desktop sidebar */}
        <div className="hidden lg:flex lg:flex-col">
          <Sidebar />
        </div>

        {/* Main content column */}
        <div className="flex min-h-screen flex-col">
          <Topbar mobileNav={<MobileNav />} />
          <main className="flex-1 p-4 md:p-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
