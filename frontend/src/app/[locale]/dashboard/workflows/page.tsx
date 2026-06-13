"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import PipelineView from "@/components/admin/views/WorkflowCanvas/PipelineView";
import { useState } from "react";
import { Network, Loader2 } from "lucide-react";

export default function WorkflowsPage() {
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);

  // 1. Fetch all agents
  const { data: agents, isLoading } = useQuery({
    queryKey: ["agentsList"],
    queryFn: async () => { const res = await fetchClient("/agents"); return res.items ?? res; },
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Cargando flujos de automatización...</p>
      </div>
    );
  }

  // Si no hay agentes en absoluto
  if (!agents || agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] max-w-md mx-auto text-center gap-6">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <Network className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">Constructor de Flujos de Automatización</h2>
          <p className="text-sm text-muted-foreground mt-2">
            No tienes ningún agente de IA creado aún. Por favor crea un agente en el "Estudio de Agentes" antes de diseñar flujos.
          </p>
        </div>
      </div>
    );
  }

  const selectedAgentId = activeAgentId || agents[0]?.id;

  return (
    <div className="space-y-6 h-[calc(100vh-10rem)]">
      {/* Cabecera con selector */}
      <div className="flex items-center justify-between border-b border-border/50 pb-4">
        <div className="flex items-center gap-4">
          <select
            value={selectedAgentId}
            onChange={(e) => setActiveAgentId(e.target.value)}
            className="bg-card border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary font-medium"
          >
            {agents.map((a: any) => (
              <option key={a.id} value={a.id}>
                🤖 {a.name} ({(a.agent_type || a.agentType || "conversational").toUpperCase()})
              </option>
            ))}
          </select>
          <span className="text-xs text-muted-foreground">
            Asocia y enruta flujos visuales a este agente
          </span>
        </div>
      </div>

      {/* Renderizar panel del Canvas de Flujos */}
      <div className="border border-border rounded-xl overflow-hidden h-full">
        <PipelineView
          botId={selectedAgentId}
          userTier="ENTERPRISE"
          onUpgradeClick={() => {}}
          dynamicModels={[]}
        />
      </div>
    </div>
  );
}
