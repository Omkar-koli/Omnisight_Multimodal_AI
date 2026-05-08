import { NextResponse } from "next/server";
import { requireSession, fastapiPost } from "@/lib/server-api";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ jobName: string }> }
) {
  try {
    await requireSession();
    const { jobName } = await params;
    const data = await fastapiPost(`/jobs/scheduler/resume/${jobName}`, {});
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { detail: String(error?.message || error) },
      { status: 500 }
    );
  }
}