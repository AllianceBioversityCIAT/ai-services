import { NextResponse } from "next/server";
import { createProject } from "@/lib/config";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const project = await createProject(body);
    return NextResponse.json({ project });
  } catch (error) {
    return NextResponse.json({ error: "Error al crear proyecto" }, { status: 500 });
  }
}
