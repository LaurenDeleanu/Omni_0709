"use client";

import { useUser } from "@/hooks/use-user";
import { useState, useRef, useEffect } from "react";
import { LogOut, ChevronDown, User, Settings } from "lucide-react";
import { Link } from "@/i18n/routing";

/**
 * UserAvatar — Componente de cabecera con avatar, nombre y menú de logout.
 * Se muestra en el header del dashboard cuando el usuario está autenticado.
 */
export function UserAvatar() {
  const { user, isLoading } = useUser();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const handleLogout = (e: React.MouseEvent) => {
    if (typeof window !== "undefined" && localStorage.getItem("local_access_token")) {
      e.preventDefault();
      localStorage.removeItem("local_access_token");
      localStorage.removeItem("local_user");
      window.location.href = "/login";
    }
  };

  // Cerrar al hacer click fuera
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
        <div className="h-4 w-24 rounded bg-muted animate-pulse hidden sm:block" />
      </div>
    );
  }

  if (!user) return null;

  const initials = user.name
    ? user.name.split(" ").map((n: string) => n[0]).slice(0, 2).join("").toUpperCase()
    : "U";

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-muted/60 transition-colors group"
        aria-label="Menú de usuario"
      >
        {/* Avatar */}
        {user.picture ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.picture}
            alt={user.name || "Avatar"}
            className="h-8 w-8 rounded-full object-cover ring-2 ring-primary/20"
          />
        ) : (
          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">
            {initials}
          </div>
        )}

        {/* Nombre */}
        <div className="hidden sm:flex flex-col items-start leading-none">
          <span className="text-sm font-medium text-foreground truncate max-w-[120px]">
            {user.name || user.email}
          </span>
          <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">
            {user.email}
          </span>
        </div>

        <ChevronDown
          className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown menu */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-border/60 bg-background/95 backdrop-blur shadow-xl z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-border/40">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Cuenta
            </p>
            <p className="text-sm font-medium text-foreground mt-0.5 truncate">
              {user.name}
            </p>
            <p className="text-xs text-muted-foreground truncate">{user.email}</p>
          </div>

          {/* Menu items */}
          <div className="p-1.5">
            <Link
              href="/dashboard/settings"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm text-foreground hover:bg-muted/60 transition-colors"
            >
              <Settings className="h-4 w-4 text-muted-foreground" />
              Configuración
            </Link>

            <Link
              href="/dashboard/profile"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm text-foreground hover:bg-muted/60 transition-colors"
            >
              <User className="h-4 w-4 text-muted-foreground" />
              Mi perfil (Portal ESS)
            </Link>
          </div>

          {/* Logout */}
          <div className="p-1.5 border-t border-border/40">
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- /auth/logout is an Auth0 v4 middleware route, not a Next page; full-page navigation is required */}
            <a
              href="/auth/logout"
              onClick={handleLogout}
              className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Cerrar sesión
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
