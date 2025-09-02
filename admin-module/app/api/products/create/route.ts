import { NextResponse } from "next/server";
import { createProduct } from "@/lib/database/products";
import { getSession } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session || session.role !== "admin") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const body = await req.json();
    const { name, description, image_url, status } = body || {};
    if (!name || !description) {
      return NextResponse.json({ error: "Missing fields" }, { status: 400 });
    }
    const product = await createProduct({
      name,
      description,
      image_url,
      status: status || "active",
    });
    return NextResponse.json({ product });
  } catch (error) {
    return NextResponse.json(
      { error: "Error al crear producto" },
      { status: 500 }
    );
  }
}
