"use client";
import { useState } from "react";

export default function ProductForm({ onCreated }: { onCreated?: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [status, setStatus] = useState("active");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    // TODO: upload image to S3 and get URL
    const res = await fetch("/api/products/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        description,
        image_url: imageUrl,
        status,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setMessage("Producto creado exitosamente");
      setName("");
      setDescription("");
      setImageUrl("");
      setStatus("active");
      if (onCreated) onCreated();
    } else {
      setMessage(data.error || "Error creating product");
    }
    setLoading(false);
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8 max-w-md mx-auto mb-8 border border-border">
      <h3 className="text-xl font-bold mb-6 text-primary">Crear Nuevo Producto</h3>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Nombre</label>
        <input type="text" value={name} onChange={e => setName(e.target.value)} required className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Descripción</label>
        <textarea value={description} onChange={e => setDescription(e.target.value)} required className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Imagen (URL)</label>
        <input type="text" value={imageUrl} onChange={e => setImageUrl(e.target.value)} className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Estado</label>
        <select value={status} onChange={e => setStatus(e.target.value)} className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary">
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
        </select>
      </div>
      <button type="submit" disabled={loading} className="bg-primary text-white px-5 py-2 rounded font-semibold shadow">
        {loading ? "Creando..." : "Crear Producto"}
      </button>
      {message && <div className="mt-3 text-sm text-blue-600">{message}</div>}
    </form>
  );
}
