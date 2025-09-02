import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { revokePromptAccess } from "@/lib/database/prompts";

export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    if (session.role !== "admin")
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });

    const { projectId, userEmail } = await req.json();
    if (!projectId || !userEmail) {
      return NextResponse.json(
        { error: "Missing projectId or userEmail" },
        { status: 400 }
      );
    }
    const ok = await revokePromptAccess(projectId, userEmail);
    if (!ok) return NextResponse.json({ error: "Failed to revoke access" }, { status: 500 });
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: "Error revoking access" }, { status: 500 });
  }
}

