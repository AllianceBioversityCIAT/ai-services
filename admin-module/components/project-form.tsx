import React, { useState } from "react";

export default function ProjectForm({ onCreated }: { onCreated: () => void }) {
  const [values, setValues] = useState({
    name: "",
    description: "",
    product_id: "",
    status: "active",
  });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

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
      setValues({ name: "", description: "", product_id: "", status: "active" });
      onCreated();
    } else {
      setMsg(data.error || "Error al crear proyecto");
    }
    setLoading(false);
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 max-w-md mx-auto">
      <h3 className="text-lg font-semibold mb-4">Registrar Proyecto</h3>
      <div className="mb-2">
        <label>Nombre</label>
        <input type="text" value={values.name} onChange={e => setValues(v => ({ ...v, name: e.target.value }))} required className="border px-2 py-1 w-full" />
      </div>
      <div className="mb-2">
        <label>Descripción</label>
        <textarea value={values.description} onChange={e => setValues(v => ({ ...v, description: e.target.value }))} required className="border px-2 py-1 w-full" />
      </div>
      <div className="mb-2">
        <label>Producto</label>
        <input type="text" value={values.product_id} onChange={e => setValues(v => ({ ...v, product_id: e.target.value }))} className="border px-2 py-1 w-full" />
      </div>
      <div className="mb-2">
        <label>Estado</label>
        <select value={values.status} onChange={e => setValues(v => ({ ...v, status: e.target.value }))} className="border px-2 py-1 w-full">
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
        </select>
      </div>
      <div className="flex gap-2 mt-4">
        <button type="submit" disabled={loading} className="bg-primary text-white px-4 py-2 rounded">
          {loading ? "Guardando..." : "Registrar"}
        </button>
      </div>
      {msg && <div className="mt-2 text-sm text-blue-600">{msg}</div>}
    </form>
  );
}
