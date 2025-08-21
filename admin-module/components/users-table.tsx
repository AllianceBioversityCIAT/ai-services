"use client";
import { useState } from "react";

export default function UsersTable({
  users,
  currentUserEmail,
}: {
  users: any[];
  currentUserEmail: string;
}) {
  const [loading, setLoading] = useState(false);

  async function handleDelete(email: string) {
    setLoading(true);
    await fetch("/api/users/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    window.location.reload();
  }

  return (
    <table className="min-w-full text-sm border rounded-lg">
      <thead>
        <tr className="bg-muted">
          <th className="p-3 text-left">Email</th>
          <th className="p-3 text-left">Role</th>
          <th className="p-3 text-left">Created At</th>
          <th className="p-3 text-left">Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.length === 0 ? (
          <tr>
            <td colSpan={4} className="p-3 text-center text-muted-foreground">
              No users found.
            </td>
          </tr>
        ) : (
          users.map((u) => (
            <tr key={u.email} className="border-b hover:bg-muted/50 transition">
              <td className="p-3 font-medium">{u.email}</td>
              <td className="p-3">
                <span
                  className={`px-2 py-1 rounded text-xs font-semibold capitalize ${
                    u.role === "admin"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {u.role}
                </span>
              </td>
              <td className="p-3">{new Date(u.createdAt).toLocaleString()}</td>
              <td className="p-3">
                {u.email !== currentUserEmail && (
                  <button
                    onClick={() => handleDelete(u.email)}
                    className="text-red-600 hover:underline font-semibold"
                    disabled={loading}
                  >
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}
