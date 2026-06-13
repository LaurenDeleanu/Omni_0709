"use client";

import { useEffect, useState, use } from "react";
import { usePathname } from "@/i18n/routing";
import { MetadataAPI, PageMetadata } from "@/lib/api";
import { DynamicRenderer } from "@/components/dynamic/DynamicRenderer";
import { Loader2 } from "lucide-react";

export default function DynamicPage({ params }: { params: Promise<{ dynamic: string[] }> }) {
  const [metadata, setMetadata] = useState<PageMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resolvedParams = use(params);
  const moduleName = resolvedParams.dynamic[0];
  const pageName = resolvedParams.dynamic.length > 1 ? resolvedParams.dynamic[1] : "index";

  useEffect(() => {
    async function fetchMetadata() {
      try {
        setLoading(true);
        const data = await MetadataAPI.getPage(moduleName, pageName);
        setMetadata(data);
      } catch (err: any) {
        const status = err.response?.status;
        if (status === 404) {
          setError("Página dinámica no encontrada. Por favor, asegúrate de que el módulo y página existen en la base de datos.");
        } else if (status === 401) {
          setError("No estás autenticado. Por favor, inicia sesión para acceder a esta página.");
        } else if (status === 403) {
          setError("No tienes permisos para ver esta página.");
        } else {
          setError(`Error al cargar la interfaz dinámica (${status ?? "red"}). Verifica que el backend esté corriendo en http://localhost:8080.`);
        }
        console.error("[DynamicPage] Error cargando metadata:", err.response?.status, err.message);
      } finally {
        setLoading(false);
      }
    }

    if (moduleName) {
      fetchMetadata();
    }
  }, [moduleName, pageName]);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !metadata) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
        <h2 className="text-2xl font-bold text-destructive">Error 404</h2>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <DynamicRenderer schema={metadata.schema_data} />
    </div>
  );
}
