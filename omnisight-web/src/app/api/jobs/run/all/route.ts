import { NextResponse } from "next/server";
import { requireSession, fastapiPost } from "@/lib/server-api";

export async function POST() {
  try {
    await requireSession();
    const data = await fastapiPost("/jobs/run/all", {});
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { detail: String(error?.message || error) },
      { status: 500 }
    );
  }
}