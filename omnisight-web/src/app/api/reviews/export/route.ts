import { NextResponse } from "next/server";
import { requireSession } from "@/lib/server-api";

const FASTAPI_BASE_URL =
  process.env.FASTAPI_INTERNAL_BASE_URL || "http://127.0.0.1:8000";

const INTERNAL_API_TOKEN = process.env.INTERNAL_API_TOKEN || "";

export async function GET() {
  try {
    await requireSession();

    const res = await fetch(`${FASTAPI_BASE_URL}/reviews/export`, {
      method: "GET",
      headers: {
        "x-internal-api-token": INTERNAL_API_TOKEN,
      },
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json({ detail: text }, { status: res.status });
    }

    const blob = await res.blob();

    return new Response(blob, {
      status: 200,
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": 'attachment; filename="review_export.csv"',
      },
    });
  } catch (error: any) {
    return NextResponse.json(
      { detail: String(error?.message || error) },
      { status: 500 }
    );
  }
}