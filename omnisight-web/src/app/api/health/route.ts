import { NextResponse } from "next/server";
import { fastapiGet } from "@/lib/server-api";

export async function GET() {
  try {
    const data = await fastapiGet("/health");
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { detail: String(error?.message || error) },
      { status: 500 }
    );
  }
}