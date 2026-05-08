import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE_URL =
  process.env.FASTAPI_INTERNAL_BASE_URL || "http://127.0.0.1:8000";

const INTERNAL_API_TOKEN = process.env.INTERNAL_API_TOKEN || "";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${FASTAPI_BASE_URL}/assistant/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-internal-api-token": INTERNAL_API_TOKEN,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const text = await res.text();

    return new NextResponse(text, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error: any) {
    return NextResponse.json(
      {
        detail: error?.message || "Failed to proxy assistant chat request.",
      },
      { status: 500 }
    );
  }
}