"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Navbar from "@/components/navbar";

export default function NavbarWrapper() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();

  // Rutas donde NO debe aparecer el navbar
  const publicRoutes = ["/", "/login", "/register"];
  const shouldHideNavbar = publicRoutes.includes(pathname);

  useEffect(() => {
    async function checkSession() {
      try {
        const res = await fetch("/api/auth/session");
        const data = await res.json();
        setUser(data.user);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    checkSession();
  }, [pathname]); // Re-ejecutar cuando cambie la ruta

  // No mostrar navbar si estamos en rutas públicas o no hay usuario
  if (shouldHideNavbar || !user || loading) {
    return null;
  }

  return <Navbar isAdmin={user.role === "admin"} />;
}
