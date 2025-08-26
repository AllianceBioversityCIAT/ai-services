
"use client";
import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";

export default function ProductsTable({ products }: { products: any[] }) {
  const [editing, setEditing] = useState<any | null>(null);
  const [editValues, setEditValues] = useState<Record<string, any>>({});
  const [editLoading, setEditLoading] = useState(false);
  const [editMsg, setEditMsg] = useState("");

  function openEdit(product: any) {
    setEditing(product);
    setEditValues({
      name: product.name,
      description: product.description,
      image_url: product.image_url || "",
      status: product.status,
    });
    setEditMsg("");
  }

  function closeEdit() {
    setEditing(null);
    setEditValues({});
    setEditMsg("");
  }

  async function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEditLoading(true);
    setEditMsg("");
    const res = await fetch("/api/products/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: editing.id || editing.PK.split('#')[1], updates: editValues }),
    });
    const data = await res.json();
    if (res.ok) {
      setEditMsg("Producto actualizado");
      window.location.reload();
    } else {
      setEditMsg(data.error || "Error al actualizar producto");
    }
    setEditLoading(false);
  }
  async function handleDelete(id: string) {
    await fetch("/api/products/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    window.location.reload();
  }

  return (
    <div className="shadow-lg rounded-xl bg-white p-8 border border-border">
      <h3 className="text-2xl font-bold mb-6 text-primary">Registered Products</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border rounded-lg">
          <thead>
            <tr className="bg-muted">
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">Description</th>
              <th className="p-3 text-left">Status</th>
              <th className="p-3 text-left">Created At</th>
              <th className="p-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-3 text-center text-muted-foreground">
                  No products found.
                </td>
              </tr>
            ) : (
              products.map((p) => (
                <tr key={p.PK} className="border-b hover:bg-blue-50 transition">
                  <td className="p-3 font-semibold text-primary">{p.name}</td>
                  <td className="p-3 text-gray-700">{p.description}</td>
                  <td className="p-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold capitalize ${p.status === "active" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700"}`}>
                      {p.status === "active" ? <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> : <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" />}
                      {p.status}
                    </span>
                  </td>
                  <td className="p-3 text-gray-500">{new Date(p.created_at).toLocaleString()}</td>
                  <td className="p-3 flex gap-2">
                    <button title="Edit" className="bg-blue-100 hover:bg-blue-200 text-blue-700 p-2 rounded transition flex items-center" onClick={() => openEdit(p)}>
                      <Pencil size={16} />
                    </button>
                    <button title="Delete" className="bg-red-100 hover:bg-red-200 text-red-700 p-2 rounded transition flex items-center" onClick={() => handleDelete(p.id || p.PK.split('#')[1])}>
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Improved edit modal */}
      {editing && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 animate-fadein">
          <form onSubmit={handleEditSubmit} className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md border border-border">
            <h3 className="text-xl font-bold mb-4 text-primary">Edit Product</h3>
            <div className="mb-3">
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" value={editValues.name} onChange={e => setEditValues((v: Record<string, any>) => ({ ...v, name: e.target.value }))} required className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="mb-3">
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea value={editValues.description} onChange={e => setEditValues((v: Record<string, any>) => ({ ...v, description: e.target.value }))} required className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="mb-3">
              <label className="block text-sm font-medium mb-1">Image (URL)</label>
              <input type="text" value={editValues.image_url} onChange={e => setEditValues((v: Record<string, any>) => ({ ...v, image_url: e.target.value }))} className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="mb-3">
              <label className="block text-sm font-medium mb-1">Status</label>
              <select value={editValues.status} onChange={e => setEditValues((v: Record<string, any>) => ({ ...v, status: e.target.value }))} className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary">
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div className="flex gap-2 mt-6">
              <button type="submit" disabled={editLoading} className="bg-primary text-white px-5 py-2 rounded font-semibold shadow">
                {editLoading ? "Saving..." : "Save"}
              </button>
              <button type="button" onClick={closeEdit} className="bg-gray-200 px-5 py-2 rounded font-semibold">Cancel</button>
            </div>
            {editMsg && <div className="mt-3 text-sm text-blue-600">{editMsg}</div>}
          </form>
        </div>
      )}
    </div>
  );
}
