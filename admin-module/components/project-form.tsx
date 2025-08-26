import React, { useState, useEffect } from "react";

export default function ProjectForm({ onCreated }: { onCreated: () => void }) {
  const [values, setValues] = useState({
    name: "",
    description: "",
    product_id: "",
    status: "active",
  });
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

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
    setMsg("");
    const res = await fetch("/api/projects/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    const data = await res.json();
    if (res.ok) {
      setMsg("Proyecto creado");
      setValues({
        name: "",
        description: "",
        product_id: "",
        status: "active",
      });
      onCreated();
    } else {
      setMsg(data.error || "Error al crear proyecto");
    }
    setLoading(false);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-xl shadow-lg p-8 max-w-md mx-auto mb-8 border border-border"
    >
      <h3 className="text-xl font-bold mb-6 text-primary">
        Crear Nuevo Proyecto
      </h3>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Nombre</label>
        <input
          type="text"
          value={values.name}
          onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
          required
          className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Descripción</label>
        <textarea
          value={values.description}
          onChange={(e) =>
            setValues((v) => ({ ...v, description: e.target.value }))
          }
          required
          className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Producto</label>
        <select
          value={values.product_id}
          onChange={(e) =>
            setValues((v) => ({ ...v, product_id: e.target.value }))
          }
          required
          className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">Selecciona un producto</option>
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
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Estado</label>
        <select
          value={values.status}
          onChange={(e) => setValues((v) => ({ ...v, status: e.target.value }))}
          className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
        </select>
      </div>
      <button
        type="submit"
        disabled={loading}
        className="bg-primary text-white px-5 py-2 rounded font-semibold shadow"
      >
        {loading ? "Guardando..." : "Registrar Proyecto"}
      </button>
      {msg && <div className="mt-3 text-sm text-blue-600">{msg}</div>}
    </form>
  );
}
