import { NextResponse } from "next/server";
import { createProduct } from "@/lib/config";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const product = await createProduct(body);
    return NextResponse.json({ product });
  } catch (error) {
    return NextResponse.json({ error: "Error al crear producto" }, { status: 500 });
  }
}
