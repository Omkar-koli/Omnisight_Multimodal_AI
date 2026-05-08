import { NextResponse } from "next/server";
import { requireSession, fastapiGet } from "@/lib/server-api";

export async function GET() {
  try {
    await requireSession();
    const data = await fastapiGet("/freshness/summary");
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ detail: String(error?.message || error) }, { status: 500 });
  }
}