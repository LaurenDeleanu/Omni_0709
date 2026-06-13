import { useState, useEffect, useCallback } from "react";
import { Step } from "@/shared";
import { getDefaultConfig } from "../utils/configDefaults";
import { toast } from "sonner";

const API_BASE = process.env.NEXT_PUBLIC_API_URL
  ? process.env.NEXT_PUBLIC_API_URL.replace("/api/v1", "")
  : "http://localhost:8080";

async function apiFetch(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...opts.headers },
  });
  if (res.ok) return res.json();
  throw new Error(`API error ${res.status}`);
}

export interface VariableDescriptor {
  name: string;
  type: string;
  stepId: string;
  stepLabel: string;
}

export function usePipelineState(botId: string) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const fetchSteps = useCallback(async () => {
    setIsLoading(true);
    try {
      const d = await apiFetch(`/api/bots/${botId}/steps`);
      setSteps(d.steps || []);
    } catch (e) {
      console.error(e);
      toast.error("Error al conectar con el servidor");
    } finally {
      setIsLoading(false);
    }
  }, [botId]);

  useEffect(() => {
    fetchSteps();
  }, [fetchSteps]);

  const addStep = async (type: string, label?: string, customConfig?: any, position?: { x: number; y: number }) => {
    setIsSaving(true);
    try {
      const stepLabel = label || type;
      const configStr = getDefaultConfig(type);
      const parsedConfig = customConfig ? { ...customConfig } : JSON.parse(configStr);
      if (position) parsedConfig.position = position;

      await apiFetch(`/api/bots/${botId}/steps`, {
        method: "POST",
        body: JSON.stringify({ type, label: stepLabel, config: JSON.stringify(parsedConfig) }),
      });
      toast.success(`Paso "${stepLabel}" creado`);
      await fetchSteps();
    } catch (e) {
      console.error(e);
      toast.error("Error de red al crear el paso");
    } finally {
      setIsSaving(false);
    }
  };

  const updateStep = async (stepId: string, data: Partial<Step>) => {
    setIsSaving(true);
    setSteps(prev => prev.map(s => s.id === stepId ? { ...s, ...data } : s));
    try {
      await apiFetch(`/api/bots/${botId}/steps/${stepId}`, { method: "PATCH", body: JSON.stringify(data) });
    } catch (e) {
      console.error(e);
      toast.error("Error al guardar el paso");
      await fetchSteps();
    } finally {
      setIsSaving(false);
    }
  };

  const deleteStep = async (stepId: string) => {
    if (!confirm("¿Estás seguro de que deseas eliminar este paso? Esto romperá las conexiones activas.")) return;
    setIsSaving(true);
    try {
      // Cleanup connections first
      const stepsToCleanup = steps.map(s => {
        let config: any = {};
        try { config = typeof s.config === "string" ? JSON.parse(s.config) : s.config; } catch {}
        let dirty = false;

        if (config.nextStepId === stepId) {
          config.nextStepId = false;
          dirty = true;
        }

        if (config.branches && Array.isArray(config.branches)) {
          const originalLen = config.branches.length;
          config.branches = config.branches.filter((b: any) => b.goToStepId !== stepId);
          if (config.branches.length !== originalLen) {
            dirty = true;
          }
        }

        if (config.branchAStepId === stepId) {
          config.branchAStepId = "";
          dirty = true;
        }

        if (config.branchBStepId === stepId) {
          config.branchBStepId = "";
          dirty = true;
        }

        if (config.errorStepId === stepId) {
          config.errorStepId = "";
          dirty = true;
        }

        return dirty ? { id: s.id, config: JSON.stringify(config) } : null;
      }).filter(Boolean) as { id: string; config: string }[];

      // Perform cleanups sequentially
    for (const cleanup of stepsToCleanup) {
      await apiFetch(`/api/bots/${botId}/steps/${cleanup.id}`, {
        method: "PATCH",
        body: JSON.stringify({ config: cleanup.config })
      });
    }

    await apiFetch(`/api/bots/${botId}/steps/${stepId}`, { method: "DELETE" });
    toast.success("Paso eliminado con éxito");
    await fetchSteps();
    } catch (e) {
      console.error(e);
      toast.error("Error de red al eliminar el paso");
    } finally {
      setIsSaving(false);
    }
  };

  const duplicateStep = async (stepId: string) => {
    setIsSaving(true);
    try {
      const res = await apiFetch(`/api/bots/${botId}/steps/${stepId}/duplicate`, { method: "POST" });
      if (res.ok) {
        toast.success("Paso duplicado correctamente");
        await fetchSteps();
      } else {
        toast.error("Error al duplicar el paso");
      }
    } catch (e) {
      console.error(e);
      toast.error("Error al duplicar el paso");
    } finally {
      setIsSaving(false);
    }
  };

  const reorderSteps = async (newOrder: { id: string; order: number }[]) => {
    setIsSaving(true);
    try {
      const res = await apiFetch(`/api/bots/${botId}/steps`, { method: "PUT", body: JSON.stringify({ steps: newOrder }) });
      if (res.ok) {
        await fetchSteps();
      } else {
        toast.error("Error al reordenar pasos");
      }
    } catch (e) {
      console.error(e);
      toast.error("Error al reordenar pasos");
    } finally {
      setIsSaving(false);
    }
  };

  // Exposes all custom variable names collected across all steps
  const getCollectedVariables = (): VariableDescriptor[] => {
    const vars: VariableDescriptor[] = [];
    steps.forEach(s => {
      let cfg: any = {};
      try {
        cfg = typeof s.config === "string" ? JSON.parse(s.config) : s.config;
      } catch {}
      
      // If COLLECT_FIELD
      if (s.type === "COLLECT_FIELD" && cfg.field) {
        vars.push({
          name: cfg.field,
          type: cfg.validationType || "text",
          stepId: s.id,
          stepLabel: s.label || s.name
        });
      }
      
      // If AI responder responses
      if ((s.type === "AI_RESPONDER" || s.type === "AUTONOMOUS_AGENT") && cfg.field) {
        vars.push({
          name: cfg.field,
          type: "ai_response",
          stepId: s.id,
          stepLabel: s.label || s.name
        });
      }

      // If Choice List choices
      if (s.type === "CHOICE_LIST" && cfg.field) {
        vars.push({
          name: cfg.field,
          type: "single_choice",
          stepId: s.id,
          stepLabel: s.label || s.name
        });
      }

      // If File Upload
      if (s.type === "FILE_UPLOAD" && cfg.field) {
        vars.push({
          name: cfg.field,
          type: "file",
          stepId: s.id,
          stepLabel: s.label || s.name
        });
        if (cfg.ocrEnabled) {
          vars.push({
            name: `${cfg.field}_ocr`,
            type: "text",
            stepId: s.id,
            stepLabel: `${s.label || s.name} (OCR Extracted)`
          });
        }
      }

      // If Booking dates
      if (s.type === "BOOKING" && cfg.field) {
        vars.push({
          name: cfg.field,
          type: "datetime",
          stepId: s.id,
          stepLabel: s.label || s.name
        });
      }

      // If dynamic payments
      if (s.type === "PAYMENT" && cfg.field) {
        vars.push({
          name: cfg.field,
          type: "boolean",
          stepId: s.id,
          stepLabel: s.label || s.name
        });
      }

      // If API calls
      if (s.type === "API_CALL" && cfg.saveToField) {
        vars.push({
          name: cfg.saveToField,
          type: "json_extracted",
          stepId: s.id,
          stepLabel: s.label || s.name
        });
      }
    });
    
    // De-duplicate variables
    const seen = new Set<string>();
    return vars.filter(v => {
      if (seen.has(v.name)) return false;
      seen.add(v.name);
      return true;
    });
  };

  return {
    steps,
    isLoading,
    isSaving,
    addStep,
    updateStep,
    deleteStep,
    duplicateStep,
    reorderSteps,
    getCollectedVariables,
    fetchSteps
  };
}
