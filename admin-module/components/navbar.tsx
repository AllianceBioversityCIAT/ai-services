"use client";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Shield } from "lucide-react";

export default function Navbar({ isAdmin }: { isAdmin: boolean }) {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const pathname = usePathname();

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (response.ok) {
        router.push("/login");
      } else {
        setIsLoggingOut(false);
      }
    } catch (error) {
      setIsLoggingOut(false);
    }
  };

  // Detectar ruta activa para resaltar el botón
  // pathname ya está disponible
  return (
    <nav className="border-b border-border bg-card w-full">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6" style={{ color: "#1a2a6c" }} />
          <span className="text-xl font-bold" style={{ color: "#1a2a6c" }}>
            Admin Module
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            style={{
              background: pathname === "/dashboard" ? "#1a2a6c" : "#fff",
              color: pathname === "/dashboard" ? "#fff" : "#1a2a6c",
              boxShadow:
                pathname === "/dashboard"
                  ? "0 2px 8px rgba(26,42,108,0.12)"
                  : "none",
              border: "1px solid #d1d9e6",
            }}
            className="px-4 py-2 rounded font-medium transition"
            onClick={() => router.push("/dashboard")}
          >
            Dashboard
          </button>
          {isAdmin && (
            <button
              style={{
                background: pathname === "/users" ? "#1a2a6c" : "#fff",
                color: pathname === "/users" ? "#fff" : "#1a2a6c",
                boxShadow:
                  pathname === "/users"
                    ? "0 2px 8px rgba(26,42,108,0.12)"
                    : "none",
                border: "1px solid #d1d9e6",
              }}
              className="px-4 py-2 rounded font-medium transition"
              onClick={() => router.push("/users")}
            >
              User Management
            </button>
          )}
          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            style={{
              background: "#fff",
              color: "#1a2a6c",
              border: "1px solid #d1d9e6",
            }}
            className="px-4 py-2 rounded font-medium transition"
          >
            {isLoggingOut ? "Logging out..." : "Logout"}
          </button>
        </div>
      </div>
    </nav>
  );
}
