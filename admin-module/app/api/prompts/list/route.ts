import { NextRequest, NextResponse } from "next/server";
import {
  getPromptStats,
  getPromptVersions,
  getPromptAccessForUser,
} from "@/lib/database/prompts";
import { getSession } from "@/lib/auth";

export async function GET(req: NextRequest) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const { searchParams } = new URL(req.url);
    const projectId = searchParams.get("projectId");
    if (!projectId) {
      return NextResponse.json({ error: "Missing projectId" }, { status: 400 });
    }
    // Only admins or users with any access to this project can list
    if (session.role !== "admin") {
      const access = await getPromptAccessForUser(projectId, session.email);
      if (!access) {
        return NextResponse.json(
          { error: "Forbidden: No access to this project's prompts" },
          { status: 403 }
        );
      }
    }

    const [versions, stats] = await Promise.all([
      getPromptVersions(projectId),
      getPromptStats(projectId),
    ]);

    return NextResponse.json({ versions, stats });
  } catch (error) {
    return NextResponse.json(
      { error: "Error listing prompts" },
      { status: 500 }
    );
  }
}
