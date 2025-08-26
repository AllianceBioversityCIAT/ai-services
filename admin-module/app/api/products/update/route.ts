import { NextRequest, NextResponse } from "next/server";
import { updateProduct } from "@/lib/config";

export async function POST(req: NextRequest) {
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
