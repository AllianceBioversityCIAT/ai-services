
"use client";
import ProductsTable from "@/components/products-table";

import ProductForm from "@/components/product-form";
import { useState, useEffect } from "react";

export default function ProductsPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchProducts() {
    setLoading(true);
    const res = await fetch("/api/products/list");
    const data = await res.json();
    setProducts(data.products || []);
    setLoading(false);
  }

  useEffect(() => {
    fetchProducts();
  }, []);

  return (
    <div className="container mx-auto py-8">
      <h2 className="text-2xl font-bold mb-6">Product Management</h2>
      <div className="max-w-xl mx-auto">
        <div className="mb-8">
          <ProductForm onCreated={fetchProducts} />
        </div>
        <ProductsTable products={products} />
      </div>
      {loading && (
        <div className="text-center py-8 text-muted-foreground">Loading products...</div>
      )}
    </div>
  );
}
