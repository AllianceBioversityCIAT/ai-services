import React, { useState, useEffect } from "react";

export default function ProjectForm({ onCreated }: { onCreated: () => void }) {
  const [values, setValues] = useState({
    name: "",
    description: "",
    product_id: "",
    swaggerURL: "",
    status: "active",
  });
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function fetchProducts() {
      const res = await fetch("/api/products/list");
      const data = await res.json();
      setProducts(data.products || []);
    }
    fetchProducts();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    const res = await fetch("/api/projects/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });

    const data = await res.json();
    if (res.ok) {
      setMessage("Project created successfully");
      setValues({
        name: "",
        description: "",
        product_id: "",
        swaggerURL: "",
        status: "active",
      });
      onCreated();
    } else {
      setMessage(data.error || "Error creating project");
    }
    setLoading(false);
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-medium mb-6 text-foreground">
        Create New Project
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Name
          </label>
          <input
            type="text"
            value={values.name}
            onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
            required
            className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
            placeholder="Enter project name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Description
          </label>
          <textarea
            value={values.description}
            onChange={(e) =>
              setValues((v) => ({ ...v, description: e.target.value }))
            }
            required
            rows={3}
            className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring resize-none"
            placeholder="Enter project description"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Product
          </label>
          <select
            value={values.product_id}
            onChange={(e) =>
              setValues((v) => ({ ...v, product_id: e.target.value }))
            }
            required
            className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
          >
            <option value="">Select a product</option>
            {products.map((prod: any) => (
              <option
                key={prod.id || prod.PK}
                value={prod.id || prod.PK.split("#")[1]}
              >
                {prod.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Swagger URL
          </label>
          <input
            type="url"
            value={values.swaggerURL}
            onChange={(e) =>
              setValues((v) => ({ ...v, swaggerURL: e.target.value }))
            }
            required
            className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
            placeholder="https://example.com/swagger"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Status
          </label>
          <select
            value={values.status}
            onChange={(e) =>
              setValues((v) => ({ ...v, status: e.target.value }))
            }
            className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-md text-sm font-medium hover:bg-primary/90 focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Creating..." : "Create Project"}
        </button>

        {message && (
          <div
            className={`text-sm p-3 rounded-md ${
              message.includes("Error")
                ? "bg-destructive/10 text-destructive border border-destructive/20"
                : "bg-emerald-50 text-emerald-700 border border-emerald-200"
            }`}
          >
            {message}
          </div>
        )}
      </form>
    </div>
  );
}
