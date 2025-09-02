import { NextResponse } from "next/server";
import { createProject } from "@/lib/database/projects";
import { getSession } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session || session.role !== "admin") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const body = await req.json();
    const project = await createProject(body);
    return NextResponse.json({ project });
  } catch (error) {
    return NextResponse.json(
      { error: "Error al crear proyecto" },
      { status: 500 }
    );
  }
}
