import React, { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";

export default function ProjectsTable({
  projects,
  onDelete,
}: {
  projects: any[];
  onDelete?: (id: string) => void;
}) {
  const [confirmId, setConfirmId] = useState<string | null>(null);

  function handleConfirm() {
    if (confirmId && onDelete) {
      onDelete(confirmId);
      setConfirmId(null);
    }
  }

  return (
    <div className="shadow-lg rounded-xl bg-white p-8 border border-border">
      <h3 className="text-2xl font-bold mb-6 text-primary">
        Registered Projects
      </h3>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border rounded-lg">
          <thead>
            <tr className="bg-muted">
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">Description</th>
              <th className="p-3 text-left">Product</th>
              <th className="p-3 text-left">Status</th>
              <th className="p-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="p-3 text-center text-muted-foreground"
                >
                  No projects found.
                </td>
              </tr>
            ) : (
              projects.map((p) => (
                <tr key={p.PK} className="border-b hover:bg-blue-50 transition">
                  <td className="p-3 font-semibold text-primary">{p.name}</td>
                  <td className="p-3 text-gray-700">{p.description}</td>
                  <td className="p-3 text-gray-700">{p.product_name || "-"}</td>
                  <td className="p-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold capitalize ${
                        p.status === "active"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {p.status === "active" ? (
                        <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" />
                      )}
                      {p.status}
                    </span>
                  </td>
                  <td className="p-3 flex gap-2">
                    <button
                      title="Edit"
                      className="bg-blue-100 hover:bg-blue-200 text-blue-700 p-2 rounded transition flex items-center"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      title="Delete"
                      className="bg-red-100 hover:bg-red-200 text-red-700 p-2 rounded transition flex items-center"
                      onClick={() => setConfirmId(p.PK.split("#")[1])}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {/* Confirmation Modal */}
      {confirmId && (
        <>
          {/* Overlay */}
          <div className="fixed inset-0 z-50 bg-black/40" />

          {/* Contenido del modal */}
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full border">
              <h4 className="text-lg font-bold mb-4 text-primary">
                ¿Delete Project?
              </h4>
              <p className="mb-6 text-gray-700">
                This action cannot be undone. Are you sure you want to delete
                this project?
              </p>
              <div className="flex justify-end gap-3">
                <button
                  className="px-4 py-2 rounded bg-muted text-primary font-semibold"
                  onClick={() => setConfirmId(null)}
                >
                  Cancel
                </button>
                <button
                  className="px-4 py-2 rounded bg-red-600 text-white font-semibold"
                  onClick={handleConfirm}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
