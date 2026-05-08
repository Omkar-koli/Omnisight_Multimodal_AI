"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";

export function LoginForm() {
  const [email, setEmail] = useState("admin@omnisight.local");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
      callbackUrl: "/",
    });

    setLoading(false);

    if (result?.error) {
      setError("Invalid email or password.");
      return;
    }

    window.location.href = "/";
  }

  return (
    <div className="w-full max-w-md rounded-xl border bg-card p-6 shadow-sm">
      <div className="mb-6">
        <div className="mb-3 inline-flex h-8 w-8 items-center justify-center rounded-md bg-foreground text-background text-sm font-semibold">
          O
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Sign in to OmniSight
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enterprise demo workspace.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>

        {error ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        ) : null}
      </form>

      <div className="mt-6 space-y-1 border-t pt-4 text-[11px] text-muted-foreground">
        <div>
          <span className="font-medium text-foreground">Admin</span> ·
          admin@omnisight.local / Admin123!
        </div>
        <div>
          <span className="font-medium text-foreground">Analyst</span> ·
          analyst@omnisight.local / Analyst123!
        </div>
        <div>
          <span className="font-medium text-foreground">Viewer</span> ·
          viewer@omnisight.local / Viewer123!
        </div>
      </div>
    </div>
  );
}
