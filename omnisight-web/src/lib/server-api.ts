import { auth } from "@/auth";

const FASTAPI_BASE_URL =
  process.env.FASTAPI_INTERNAL_BASE_URL || "http://127.0.0.1:8000";

const INTERNAL_API_TOKEN = process.env.INTERNAL_API_TOKEN || "";

function buildHeaders(extra?: HeadersInit): HeadersInit {
  return {
    "Content-Type": "application/json",
    "x-internal-api-token": INTERNAL_API_TOKEN,
    ...(extra || {}),
  };
}

function parseJsonSafe(text: string) {
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function requireSession() {
  const session = await auth();
  if (!session?.user) {
    throw new Error("Unauthorized");
  }
  return session;
}

export async function fastapiGet<T = any>(path: string): Promise<T> {
  const res = await fetch(`${FASTAPI_BASE_URL}${path}`, {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store",
  });

  const text = await res.text();

  if (!res.ok) {
    throw new Error(`FastAPI GET failed (${path}) [${res.status}]: ${text}`);
  }

  return parseJsonSafe(text) as T;
}

export async function fastapiPost<T = any>(
  path: string,
  body: unknown
): Promise<T> {
  const res = await fetch(`${FASTAPI_BASE_URL}${path}`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const text = await res.text();

  if (!res.ok) {
    throw new Error(`FastAPI POST failed (${path}) [${res.status}]: ${text}`);
  }

  return parseJsonSafe(text) as T;
}