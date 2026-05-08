import { NextResponse } from "next/server";
import { requireSession, fastapiGet } from "@/lib/server-api";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ productId: string }> }
) {
  try {
    await requireSession();
    const { productId } = await params;
    const data = await fastapiGet(`/decision/${productId}`);
    return NextResponse.json(data);
  } catch (error: any) {
    const message = String(error?.message || error);

    if (message.includes("Unauthorized")) {
      return NextResponse.json({ detail: message }, { status: 401 });
    }

    return NextResponse.json({ detail: message }, { status: 500 });
  }
}