import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { grantPromptAccess, PromptAccessRole } from "@/lib/database/prompts";

export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    if (session.role !== "admin")
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });

    const { projectId, userEmail, role } = await req.json();
    if (!projectId || !userEmail) {
      return NextResponse.json(
        { error: "Missing projectId or userEmail" },
        { status: 400 }
      );
    }
    const roleValue: PromptAccessRole = role === "viewer" ? "viewer" : "editor";
    const ok = await grantPromptAccess(projectId, userEmail, roleValue);
    if (!ok) return NextResponse.json({ error: "Failed to grant access" }, { status: 500 });
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: "Error granting access" }, { status: 500 });
  }
}

