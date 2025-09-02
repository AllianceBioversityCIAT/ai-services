"use client";
import React, { useEffect, useMemo, useState } from "react";

type AccessItem = {
  project_id: string;
  user_email: string;
  role: "editor" | "viewer";
  created_at: string;
};

type SafeUser = { email: string; role: "admin" | "user"; createdAt: string };

export default function PromptAccessManager({ projectId, initial }: { projectId: string; initial: AccessItem[] }) {
  const [rows, setRows] = useState<AccessItem[]>(initial);
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState<"editor" | "viewer">("editor");
  const [users, setUsers] = useState<SafeUser[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<string>("");
  const canSubmit = useMemo(() => selectedEmail.trim().length > 3, [selectedEmail]);
  const assignableUsers = useMemo(
    () => users.filter((u) => !rows.some((r) => r.user_email === u.email)),
    [users, rows]
  );

  async function refresh() {
    setLoading(true);
    const res = await fetch(`/api/prompts/access/list?projectId=${encodeURIComponent(projectId)}`);
    const data = await res.json();
    setRows(data.access || []);
    setLoading(false);
  }

  async function handleGrant(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    const res = await fetch(`/api/prompts/access/grant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projectId, userEmail: selectedEmail.trim(), role }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.error || "Failed to grant access");
      return;
    }
    setSelectedEmail("");
    setRole("editor");
    refresh();
  }

  async function handleRevoke(user_email: string) {
    const res = await fetch(`/api/prompts/access/revoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projectId, userEmail: user_email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.error || "Failed to revoke access");
      return;
    }
    refresh();
  }

  useEffect(() => {
    setRows(initial);
  }, [initial]);

  useEffect(() => {
    // Load users (admin-only endpoint). Filter to role "user".
    (async () => {
      const res = await fetch("/api/users");
      if (!res.ok) return;
      const data = await res.json();
      const list = (data.users || []) as SafeUser[];
      setUsers(list.filter((u) => u.role === "user"));
    })();
  }, []);

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-foreground">Access Management</h3>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-border text-sm text-foreground hover:bg-muted"
        >
          Refresh
        </button>
      </div>

      <form onSubmit={handleGrant} className="grid gap-3 sm:grid-cols-3">
        <select
          value={selectedEmail}
          onChange={(e) => setSelectedEmail(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">Select user…</option>
          {assignableUsers.map((u) => (
            <option key={u.email} value={u.email}>
              {u.email}
            </option>
          ))}
        </select>
        <select
          value={role}
          onChange={(e) => setRole((e.target.value as any) || "editor")}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="editor">Editor</option>
          <option value="viewer">Viewer</option>
        </select>
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center justify-center px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          Grant access
        </button>
      </form>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th className="text-left py-2 px-3 font-medium">User</th>
              <th className="text-left py-2 px-3 font-medium">Role</th>
              <th className="text-left py-2 px-3 font-medium">Granted</th>
              <th className="text-right py-2 px-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-muted-foreground">Loading...</td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-muted-foreground">No users with access</td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.user_email} className="border-b border-border">
                  <td className="py-2 px-3 text-foreground">{r.user_email}</td>
                  <td className="py-2 px-3 text-muted-foreground">{r.role}</td>
                  <td className="py-2 px-3 text-muted-foreground">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="py-2 px-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleRevoke(r.user_email)}
                        className="px-3 py-1.5 rounded-md text-red-600 hover:bg-red-50"
                        title="Revoke access"
                      >
                        Revoke
                      </button>
                    </div>
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
