import { NextResponse } from "next/server";
import { updateProject } from "@/lib/database/projects";
import { getSession } from "@/lib/auth";
import { getPromptAccessForUser } from "@/lib/database/prompts";

export async function POST(req: Request) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { id, updates } = await req.json();
  if (!id || !updates) {
    return NextResponse.json(
      { error: "Missing id or updates" },
      { status: 400 }
    );
  }
  try {
    if (session.role !== "admin") {
      const access = await getPromptAccessForUser(id, session.email);
      if (!access) {
        return NextResponse.json({ error: "Forbidden" }, { status: 403 });
      }
    }
    await updateProject(id, updates);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: "Error updating project" },
      { status: 500 }
    );
  }
}
