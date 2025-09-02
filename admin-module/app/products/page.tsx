import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { listProducts } from "../../lib/database/products";
import ProductsPageClient from "./products-page-client";

export default async function ProductsPage() {
  const user = await getSession();
  if (!user) {
    redirect("/login");
    return null;
  }

  const products = await listProducts();
  const isAdmin = user.role === "admin";
  return <ProductsPageClient initialProducts={products} isAdmin={isAdmin} />;
}
