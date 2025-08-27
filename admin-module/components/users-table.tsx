"use client";
import { useState } from "react";
import { Trash2 } from "lucide-react";
import TableSkeleton from "./table-skeleton";

export default function UsersTable({
  users,
  currentUserEmail,
  onUserDeleted,
  loading = false,
}: {
  users: any[];
  currentUserEmail: string;
  onUserDeleted?: () => void;
  loading?: boolean;
}) {
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  async function handleDelete(email: string) {
    setDeleteLoading(true);
    await fetch("/api/users/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    setConfirmDelete(null);
    setDeleteLoading(false);
    if (onUserDeleted) onUserDeleted();
  }

  return (
    <div className="bg-card border border-border rounded-lg">
      <div className="p-6 border-b border-border">
        <h3 className="text-lg font-medium text-foreground">Users</h3>
        <p className="text-sm text-muted-foreground mt-1">
          {users.length} user{users.length !== 1 ? "s" : ""} registered
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-6 text-sm font-medium text-muted-foreground">
                Email
              </th>
              <th className="text-left py-3 px-6 text-sm font-medium text-muted-foreground">
                Role
              </th>
              <th className="text-left py-3 px-6 text-sm font-medium text-muted-foreground">
                Created
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
            ) : users.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="text-center py-12 text-muted-foreground"
                >
                  <div className="flex flex-col items-center space-y-2">
                    <div className="text-sm">No users found</div>
                    <div className="text-xs">
                      Register your first user to get started
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr
                  key={user.email}
                  className="border-b border-border hover:bg-muted/50 transition-colors"
                >
                  <td className="py-3 px-6">
                    <div className="font-medium text-foreground">
                      {user.email}
                    </div>
                  </td>
                  <td className="py-3 px-6">
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        user.role === "admin"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {user.role}
                    </span>
                  </td>
                  <td className="py-3 px-6">
                    <div className="text-sm text-muted-foreground">
                      {new Date(user.createdAt).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="py-3 px-6">
                    <div className="flex items-center justify-end">
                      {user.email !== currentUserEmail && (
                        <button
                          onClick={() => setConfirmDelete(user.email)}
                          disabled={loading}
                          className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg shadow-lg w-full max-w-sm mx-4">
            <div className="p-6">
              <h3 className="text-lg font-medium text-foreground mb-2">
                Delete User
              </h3>
              <p className="text-sm text-muted-foreground mb-6">
                This action cannot be undone. Are you sure you want to delete
                this user?
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setConfirmDelete(null)}
                  className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => confirmDelete && handleDelete(confirmDelete)}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 disabled:opacity-50 transition-colors"
                >
                  {loading ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
