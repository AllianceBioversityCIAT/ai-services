"use client";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import { Shield, LogOut } from "lucide-react";

export default function Navbar({ isAdmin }: { isAdmin: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const items = useMemo(
    () => [
      { label: "Dashboard", href: "/dashboard" },
      { label: "Products", href: "/products" },
      { label: "Projects", href: "/projects" },
      ...(isAdmin ? [{ label: "User Management", href: "/users" }] : []),
    ],
    [isAdmin]
  );

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      const res = await fetch("/api/auth/logout", { method: "POST" });
      if (!res.ok) throw new Error("Logout failed");
      router.push("/login");
    } catch {
      setIsLoggingOut(false);
    }
  }

  // Activa por segmento raíz (p.ej. "/products" activo en "/products", "/products/123")
  const isActive = (href: string) => {
    const currentRoot = `/${pathname.split("/")[1] ?? ""}`;
    return currentRoot === href;
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-card/80 backdrop-blur">
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <span className="text-sm font-semibold text-foreground">
            Admin Module
          </span>
        </div>

        <nav className="flex items-center gap-1">
          {items.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={[
                  "inline-flex items-center px-3 h-9 rounded-md text-sm font-medium transition-colors",
                  "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                  active
                    ? "bg-primary/15 text-primary ring-1 ring-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/60",
                ].join(" ")}
              >
                {item.label}
              </Link>
            );
          })}

          <div className="w-px h-5 mx-2 bg-border" />

          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            aria-busy={isLoggingOut}
            title="Cerrar sesión"
            className={[
              "inline-flex items-center gap-2 px-3 h-9 rounded-md text-sm font-medium",
              "border border-destructive/40 text-destructive",
              "hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-destructive",
              "disabled:opacity-50",
            ].join(" ")}
          >
            {isLoggingOut ? (
              <>
                <span className="inline-block size-3 animate-spin rounded-full border-2 border-destructive/60 border-t-transparent" />
                Cerrando...
              </>
            ) : (
              <>
                <LogOut className="h-4 w-4" />
                Salir
              </>
            )}
          </button>
        </nav>
      </div>
    </header>
  );
}
