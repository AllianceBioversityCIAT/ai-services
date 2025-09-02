import { NextResponse } from "next/server";
import { markPromptAsStable } from "@/lib/database/prompts";
import { getSession } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { projectId, createdAt } = await req.json();
    if (!projectId || !createdAt) {
      return NextResponse.json(
        { error: "Missing projectId or createdAt" },
        { status: 400 }
      );
    }

    // Only admins can mark stable for now
    if (session.role !== "admin") {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    await markPromptAsStable(projectId, createdAt, true);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: "Error marking prompt as stable" },
      { status: 500 }
    );
  }
}

