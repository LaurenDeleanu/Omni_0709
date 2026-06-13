"use client";

import { useUser } from "@/hooks/use-user";
import { useRouter } from "@/i18n/routing";
import { useEffect } from "react";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * AuthGuard — Protege rutas que requieren autenticación.
 *
 * Comportamiento:
 *  - Cargando → muestra spinner con animación.
 *  - Sin sesión → redirige a /login.
 *  - Con sesión → renderiza children.
 *
 * Uso: envolver el layout del dashboard con este componente.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const { user, isLoading } = useUser();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          {/* Spinner animado */}
          <div className="relative h-16 w-16">
            <div className="absolute inset-0 rounded-full border-4 border-muted" />
            <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-primary" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">SuccessCore HR</p>
            <p className="text-xs text-muted-foreground mt-1">Verificando sesión…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    // En proceso de redirección, no renderizar nada
    return null;
  }

  return <>{children}</>;
}
