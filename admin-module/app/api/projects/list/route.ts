import { NextResponse } from "next/server";
import { listProjects } from "@/lib/config";

export async function GET() {
  try {
    const projects = await listProjects();
    return NextResponse.json({ projects });
  } catch (error) {
    return NextResponse.json({ error: "Error al listar proyectos" }, { status: 500 });
  }
}
