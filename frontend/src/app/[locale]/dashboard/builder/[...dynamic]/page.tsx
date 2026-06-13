"use client";

import React, { useEffect, useState, use } from "react";
import { MetadataAPI } from "@/lib/api";
import { VisualEditor } from "@/components/builder/VisualEditor";
import { BuilderProvider, SchemaNode, generateId } from "@/components/builder/BuilderContext";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

function backendToSchemaNode(data: any, isRoot = true): SchemaNode {
  if (!data || Object.keys(data).length === 0) {
    return { id: isRoot ? "root" : generateId(), type: "page", props: { title: "Nueva Página" }, children: [] };
  }
  // If it's a Craft.js legacy node (ROOT), ignore it and start fresh
  if (data.ROOT) {
    return { id: isRoot ? "root" : generateId(), type: "page", props: { title: "Página (Migrada de Craft)" }, children: [] };
  }

  const { type, children, id, ...props } = data;
  return {
    id: id || (isRoot ? "root" : generateId()),
    type: type || (isRoot ? "page" : "layout"),
    props: props || {},
    children: children ? children.map((c: any) => backendToSchemaNode(c, false)) : undefined,
  };
}

export default function BuilderPage({ params }: { params: Promise<{ dynamic: string[] }> }) {
  const [initialSchema, setInitialSchema] = useState<SchemaNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resolvedParams = use(params);
  const moduleName = resolvedParams.dynamic[0];
  const pageName = resolvedParams.dynamic.length > 1 ? resolvedParams.dynamic[1] : "index";

  useEffect(() => {
    async function fetchMetadata() {
      try {
        setLoading(true);
        try {
          const data = await MetadataAPI.getPage(moduleName, pageName);
          setInitialSchema(backendToSchemaNode(data.schema_data));
        } catch (e: any) {
          if (e.status === 404) {
            // Not found, start fresh
            setInitialSchema({ id: "root", type: "page", props: { title: "Nueva Página" }, children: [] });
          } else {
            throw e;
          }
        }
      } catch (err: any) {
        const status = err.status;
        if (status === 401) {
          setError("No estás autenticado (401). Inicia sesión nuevamente.");
        } else if (status === 403) {
          setError("No tienes permisos de administrador (hr_admin / sys_admin) (403).");
        } else if (status === 404) {
          // Si no existe, creamos un canvas vacío para empezar a construir
          console.log(`[BuilderPage] Página ${moduleName}/${pageName} no existe. Iniciando lienzo en blanco.`);
          setInitialSchema({
            id: "root",
            type: "page",
            props: {
              title: `Página: ${moduleName}/${pageName}`,
              description: "Página nueva",
            },
            children: []
          });
        } else {
          setError(`Error al cargar la interfaz (HTTP ${status || "Network Error"}). Revisa la consola o asegúrate de que el backend esté corriendo.`);
        }
        console.error("[BuilderPage] Error fetching metadata:", err);
      } finally {
        setLoading(false);
      }
    }

    if (moduleName) {
      fetchMetadata();
    }
  }, [moduleName, pageName]);

  const handleSave = async (exportableSchema: any) => {
    try {
      const payload = {
        module_name: moduleName,
        page_name: pageName,
        description: "Página generada con Visual Builder",
        schema_data: exportableSchema
      };
      
      try {
        await MetadataAPI.create(payload);
        toast.success("Página creada exitosamente");
      } catch (e: any) {
        if (e.status === 400 || e.status === 409) {
          // Ya existe, usamos PUT
          await MetadataAPI.update(moduleName, pageName, payload);
          toast.success("Página actualizada exitosamente");
        } else {
          throw e;
        }
      }
    } catch (error) {
      console.error("Error saving:", error);
      toast.error("Error al guardar los cambios.");
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !initialSchema) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
        <h2 className="text-2xl font-bold text-destructive">Error</h2>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  return (
    <div className="-m-4 lg:-m-8">
      <BuilderProvider initialSchema={initialSchema}>
        <VisualEditor onSave={handleSave} />
      </BuilderProvider>
    </div>
  );
}
