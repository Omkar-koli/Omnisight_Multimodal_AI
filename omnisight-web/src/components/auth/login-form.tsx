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
    <div className="w-full max-w-md rounded-2xl border bg-card p-6 shadow-sm">
      <h1 className="mb-2 text-2xl font-semibold">Sign in to OmniSight</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Demo credentials are enabled for local enterprise prototype access.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          className="w-full rounded-md border px-3 py-2"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          className="w-full rounded-md border px-3 py-2"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-black px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>

        {error ? <div className="text-sm text-red-500">{error}</div> : null}
      </form>

      <div className="mt-6 text-xs text-muted-foreground">
        Admin: admin@omnisight.local / Admin123!
        <br />
        Analyst: analyst@omnisight.local / Analyst123!
        <br />
        Viewer: viewer@omnisight.local / Viewer123!
      </div>
    </div>
  );
}