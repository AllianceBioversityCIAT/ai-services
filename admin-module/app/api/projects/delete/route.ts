import { NextResponse } from "next/server";
import { deleteProject } from "@/lib/database/projects";

export async function POST(req: Request) {
  const { id } = await req.json();
  if (!id) {
    return NextResponse.json({ error: "Missing project id" }, { status: 400 });
  }
  try {
    await deleteProject(id);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: "Error deleting project" },
      { status: 500 }
    );
  }
}
