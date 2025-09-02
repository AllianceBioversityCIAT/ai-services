import { NextRequest, NextResponse } from "next/server";
import { updateProduct } from "@/lib/database/products";
import { getSession } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || session.role !== "admin") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { id, updates } = await req.json();
  if (!id || !updates) {
    return NextResponse.json({ error: "Missing product id or updates" }, { status: 400 });
  }
  try {
    await updateProduct(id, updates);
    return NextResponse.json({ message: "Producto actualizado" });
  } catch (error) {
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
