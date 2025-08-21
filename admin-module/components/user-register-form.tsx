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
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label>Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="border px-2 py-1 w-full"
        />
      </div>
      <div>
        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="border px-2 py-1 w-full"
        />
      </div>
      <div>
        <label>Rol</label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="border px-2 py-1 w-full"
        >
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <button
        type="submit"
        disabled={loading}
        className="bg-blue-600 text-white px-4 py-2 rounded"
      >
        {loading ? "Creando..." : "Registrar Usuario"}
      </button>
      {message && <div className="mt-2 text-sm text-red-600">{message}</div>}
    </form>
  );
}
