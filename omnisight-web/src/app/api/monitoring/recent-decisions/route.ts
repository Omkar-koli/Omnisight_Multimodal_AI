import { NextRequest, NextResponse } from "next/server";
import { requireSession, fastapiGet } from "@/lib/server-api";

export async function GET(req: NextRequest) {
  try {
    await requireSession();
    const searchParams = req.nextUrl.searchParams;
    const qs = searchParams.toString();
    const path = qs
      ? `/monitoring/recent-decisions?${qs}`
      : "/monitoring/recent-decisions";

    const data = await fastapiGet(path);
    return NextResponse.json(data);
  } catch (error: any) {
    const message = String(error?.message || error);
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}