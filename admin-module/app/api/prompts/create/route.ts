import { NextResponse } from "next/server";
import { createPromptVersion, getLatestPrompt } from "@/lib/database/prompts";
import { getSession } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { projectId, prompt_text, version, description, parameters } = body || {};
    if (!projectId || !prompt_text) {
      return NextResponse.json(
        { error: "Missing projectId or prompt_text" },
        { status: 400 }
      );
    }

    // Authorization: admins can create; non-admins only if they "own" latest prompt
    // If no prompts exist yet, allow creation by any authenticated user.
    const latest = await getLatestPrompt(projectId);
    if (latest && session.role !== "admin" && latest.created_by !== session.email) {
      return NextResponse.json(
        { error: "Forbidden: You cannot edit this prompt" },
        { status: 403 }
      );
    }

    const ver = version || new Date().toISOString();
    const item = await createPromptVersion({
      project_id: projectId,
      version: ver,
      prompt_text,
      is_stable: false,
      created_by: session.email,
      description: description || "",
      parameters: parameters || {},
    });

    return NextResponse.json({ prompt: item });
  } catch (error) {
    return NextResponse.json(
      { error: "Error creating prompt version" },
      { status: 500 }
    );
  }
}

