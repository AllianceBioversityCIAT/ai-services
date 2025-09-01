import { NextRequest, NextResponse } from "next/server";
import { getPromptStats, getPromptVersions } from "@/lib/database/prompts";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const projectId = searchParams.get("projectId");
    if (!projectId) {
      return NextResponse.json({ error: "Missing projectId" }, { status: 400 });
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

