import { NextResponse } from "next/server";
import { updateProject } from "@/lib/config";

export async function POST(req: Request) {
  const { id, updates } = await req.json();
  if (!id || !updates) {
    return NextResponse.json(
      { error: "Missing id or updates" },
      { status: 400 }
    );
  }
  try {
    await updateProject(id, updates);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: "Error updating project" },
      { status: 500 }
    );
  }
}
