import { NextResponse } from "next/server";
import { requireSession, fastapiGet } from "@/lib/server-api";

export async function GET() {
  try {
    await requireSession();
    const data = await fastapiGet("/dashboard/review-stats");
    return NextResponse.json(data);
  } catch (error: any) {
    const message = String(error?.message || error);
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}