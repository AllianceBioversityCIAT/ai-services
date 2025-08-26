"use client";
import { useState } from "react";
import { Trash2 } from "lucide-react";

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
    <div className="shadow-lg rounded-xl bg-white p-8 border border-border">
      <h3 className="text-2xl font-bold mb-6 text-primary">Registered Users</h3>
      <div className="overflow-x-auto">
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
                <tr key={u.email} className="border-b hover:bg-blue-50 transition">
                  <td className="p-3 font-semibold text-primary">{u.email}</td>
                  <td className="p-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold capitalize ${u.role === "admin" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700"}`}>
                      {u.role === "admin" ? <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> : <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" />}
                      {u.role}
                    </span>
                  </td>
                  <td className="p-3 text-gray-500">{new Date(u.createdAt).toLocaleString()}</td>
                  <td className="p-3 flex gap-2">
                    {u.email !== currentUserEmail && (
                      <button title="Delete" className="bg-red-100 hover:bg-red-200 text-red-700 p-2 rounded transition flex items-center" onClick={() => handleDelete(u.email)} disabled={loading}>
                          <Trash2 size={16} />
                        </button>
                    )}
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
