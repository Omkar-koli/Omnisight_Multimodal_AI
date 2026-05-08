import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/app-shell";
import { AuthSessionProvider } from "@/components/auth/session-provider";
import { AssistantChatWidget } from "@/components/assistant/assistant-chat-widget";

export const metadata: Metadata = {
  title: "OmniSight",
  description: "Enterprise inventory decision intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthSessionProvider>
          <AppShell>
            {children}
            <AssistantChatWidget />
          </AppShell>
        </AuthSessionProvider>
      </body>
    </html>
  );
}