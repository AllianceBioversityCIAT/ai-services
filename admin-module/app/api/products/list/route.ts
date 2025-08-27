import { NextRequest, NextResponse } from "next/server";
import { listProducts } from "@/lib/database/products";

export async function GET(req: NextRequest) {
  try {
    const products = await listProducts();
    return NextResponse.json({ products });
  } catch (error) {
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
