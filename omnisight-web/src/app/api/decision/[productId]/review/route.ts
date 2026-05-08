import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { fastapiPost } from "@/lib/server-api";

function canReview(role?: string | null) {
  return role === "admin" || role === "analyst";
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ productId: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    if (!canReview(session.user.role)) {
      return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
    }

    const { productId } = await params;
    const body = await req.json();

    const payload = {
      ...body,
      reviewer_name: session.user.name || session.user.email || "Unknown Reviewer",
    };

    const data = await fastapiPost(`/decision/${productId}/review`, payload);
    return NextResponse.json(data);
  } catch (error: any) {
    const message = String(error?.message || error);
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}