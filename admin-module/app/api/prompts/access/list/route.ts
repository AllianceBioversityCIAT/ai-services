import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { listPromptAccessUsers } from "@/lib/database/prompts";

export async function GET(req: NextRequest) {
  try {
    const session = await getSession();
    if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    if (session.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

    const { searchParams } = new URL(req.url);
    const projectId = searchParams.get("projectId");
    if (!projectId) {
      return NextResponse.json({ error: "Missing projectId" }, { status: 400 });
    }

    const access = await listPromptAccessUsers(projectId);
    return NextResponse.json({ access });
  } catch (error) {
    return NextResponse.json({ error: "Error listing access" }, { status: 500 });
  }
}

