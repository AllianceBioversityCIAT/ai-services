"use client";
import { useState } from "react";
import ProductsTable from "@/components/products-table";
import ProductForm from "@/components/product-form";

export default function ProductsPageClient({
  initialProducts,
}: {
  initialProducts: any[];
}) {
  const [products, setProducts] = useState(initialProducts); //
  const [loading, setLoading] = useState(false);

  async function fetchProducts() {
    setLoading(true);
    const res = await fetch("/api/products/list");
    const data = await res.json();
    setProducts(data.products || []);
    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-foreground">Products</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your product catalog
          </p>
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Form Sidebar */}
          <div className="lg:col-span-1">
            <ProductForm onCreated={fetchProducts} />
          </div>

          {/* Table Main Content */}
          <div className="lg:col-span-2">
            <ProductsTable
              products={products}
              onRefresh={fetchProducts}
              loading={loading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
