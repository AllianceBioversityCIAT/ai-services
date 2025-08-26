import React from "react";

export default function ProjectsTable({ projects }: { projects: any[] }) {
  return (
    <div className="shadow-lg rounded-lg bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Listado de Proyectos</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border rounded-lg">
          <thead>
            <tr className="bg-muted">
              <th className="p-3 text-left">Nombre</th>
              <th className="p-3 text-left">Descripción</th>
              <th className="p-3 text-left">Producto</th>
              <th className="p-3 text-left">Estado</th>
              <th className="p-3 text-left">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {projects.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-3 text-center text-muted-foreground">
                  No hay proyectos registrados.
                </td>
              </tr>
            ) : (
              projects.map((p) => (
                <tr key={p.PK} className="border-b hover:bg-muted/50 transition">
                  <td className="p-3 font-medium">{p.name}</td>
                  <td className="p-3">{p.description}</td>
                  <td className="p-3">{p.product_name || "-"}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold capitalize ${p.status === "active" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700"}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="p-3">
                    <button className="text-blue-600 hover:underline font-semibold mr-2">Editar</button>
                    <button className="text-red-600 hover:underline font-semibold">Eliminar</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
