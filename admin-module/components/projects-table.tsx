import React, { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import TableSkeleton from "./table-skeleton";

export default function ProjectsTable({
  projects,
  onDelete,
  onEdit,
  loading = false,
}: {
  projects: any[];
  onDelete?: (id: string) => void;
  onEdit?: () => void;
  loading?: boolean;
}) {
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [editing, setEditing] = useState<any | null>(null);
  const [editValues, setEditValues] = useState<Record<string, any>>({});
  const [editLoading, setEditLoading] = useState(false);

  function handleConfirm() {
    if (confirmId && onDelete) {
      onDelete(confirmId);
      setConfirmId(null);
    }
  }

  function openEdit(project: any) {
    setEditing(project);
    setEditValues({
      name: project.name,
      description: project.description,
      status: project.status,
    });
  }

  function closeEdit() {
    setEditing(null);
    setEditValues({});
  }

  async function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEditLoading(true);
    await fetch("/api/projects/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: editing.PK.split("#")[1],
        updates: editValues,
      }),
    });
    setEditLoading(false);
    closeEdit();
    if (onEdit) onEdit();
  }

  return (
    <div className="bg-card border border-border rounded-lg">
      <div className="p-6 border-b border-border">
        <h3 className="text-lg font-medium text-foreground">Projects</h3>
        <p className="text-sm text-muted-foreground mt-1">
          {projects.length} project{projects.length !== 1 ? "s" : ""} registered
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-6 text-sm font-medium text-muted-foreground">
                Name
              </th>
              <th className="text-left py-3 px-6 text-sm font-medium text-muted-foreground">
                Description
              </th>
              <th className="text-left py-3 px-6 text-sm font-medium text-muted-foreground">
                Product
              </th>
              <th className="text-left py-3 px-6 text-sm font-medium text-muted-foreground">
                Status
              </th>
              <th className="text-right py-3 px-6 text-sm font-medium text-muted-foreground">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableSkeleton
                columns={5}
                rows={5}
                widths={["w-32", "w-48", "w-16", "w-20", "w-24"]}
              />
            ) : projects.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="text-center py-12 text-muted-foreground"
                >
                  <div className="flex flex-col items-center space-y-2">
                    <div className="text-sm">No projects found</div>
                    <div className="text-xs">
                      Create your first project to get started
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              projects.map((project) => (
                <tr
                  key={project.PK}
                  className="border-b border-border hover:bg-muted/50 transition-colors"
                >
                  <td className="py-3 px-6">
                    <div className="font-medium text-foreground">
                      {project.name}
                    </div>
                  </td>
                  <td className="py-3 px-6">
                    <div className="text-sm text-muted-foreground max-w-xs truncate">
                      {project.description}
                    </div>
                  </td>
                  <td className="py-3 px-6">
                    <div className="text-sm text-muted-foreground">
                      {project.product_name || "-"}
                    </div>
                  </td>
                  <td className="py-3 px-6">
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        project.status === "active"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {project.status}
                    </span>
                  </td>
                  <td className="py-3 px-6">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => openEdit(project)}
                        className="p-2 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/50 transition-colors"
                        title="Edit project"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        onClick={() => setConfirmId(project.PK.split("#")[1])}
                        className="p-2 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-destructive/40 transition-colors"
                        title="Delete project"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation Modal */}
      {confirmId && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg shadow-lg w-full max-w-sm mx-4">
            <div className="p-6">
              <h3 className="text-lg font-medium text-foreground mb-2">
                Delete Project
              </h3>
              <p className="text-sm text-muted-foreground mb-6">
                This action cannot be undone. Are you sure you want to delete
                this project?
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setConfirmId(null)}
                  className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  className="px-4 py-2 text-sm font-medium bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editing && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg shadow-lg w-full max-w-md mx-4">
            <form onSubmit={handleEditSubmit}>
              <div className="p-6 border-b border-border">
                <h3 className="text-lg font-medium text-foreground">
                  Edit Project
                </h3>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Name
                  </label>
                  <input
                    type="text"
                    value={editValues.name}
                    onChange={(e) =>
                      setEditValues((v) => ({ ...v, name: e.target.value }))
                    }
                    required
                    className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Description
                  </label>
                  <textarea
                    value={editValues.description}
                    onChange={(e) =>
                      setEditValues((v) => ({
                        ...v,
                        description: e.target.value,
                      }))
                    }
                    required
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Status
                  </label>
                  <select
                    value={editValues.status}
                    onChange={(e) =>
                      setEditValues((v) => ({ ...v, status: e.target.value }))
                    }
                    className="w-full px-3 py-2 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="p-6 border-t border-border flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={closeEdit}
                  className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editLoading}
                  className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {editLoading ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
