"use client";
import { useState } from "react";

export default function UserRegisterForm({ isAdmin }: { isAdmin: boolean }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isAdmin) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    const res = await fetch("/api/users/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        passwordHash: password, // Hash en backend
        role,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setMessage("Usuario creado exitosamente");
      setEmail("");
      setPassword("");
      setRole("user");
    } else {
      setMessage(data.error || "Error al crear usuario");
    }
    setLoading(false);
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8 max-w-md mx-auto mb-8 border border-border">
      <h3 className="text-xl font-bold mb-6 text-primary">Register New User</h3>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Email</label>
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Password</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Role</label>
        <select value={role} onChange={e => setRole(e.target.value)} className="border px-3 py-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-primary">
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <button type="submit" disabled={loading} className="bg-primary text-white px-5 py-2 rounded font-semibold shadow">
        {loading ? "Creating..." : "Register User"}
      </button>
      {message && <div className="mt-3 text-sm text-blue-600">{message}</div>}
    </form>
  );
}
