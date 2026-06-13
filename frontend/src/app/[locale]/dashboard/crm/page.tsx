"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import CRMView from "@/components/admin/views/CRM/CRMView";
import { useState } from "react";
import { TrendingUp, Loader2 } from "lucide-react";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function CRMPage() {
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);

  // Fetch agents
  const { data: agents, isLoading } = useQuery({
    queryKey: ["agentsList"],
    queryFn: async () => { const res = await fetchClient("/agents"); return res.items ?? res; },
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Cargando tablero CRM...</p>
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] max-w-md mx-auto text-center gap-6">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <TrendingUp className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">CRM & Oportunidades</h2>
          <p className="text-sm text-muted-foreground mt-2">
            No tienes agentes activos. Crea un agente antes de acceder al panel CRM.
          </p>
        </div>
      </div>
    );
  }

  const selectedAgentId = activeAgentId || agents[0]?.id;

  return (
    <div className="space-y-6">
      {/* Selector */}
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
            Ver prospectos e interacciones vinculadas a este agente
          </span>
        </div>
      </div>

      <CRMView botId={selectedAgentId} />

      <InlineCopilot
        moduleContext="CRM"
        placeholder="Ask about your CRM pipeline..."
        quickActions={[
          { label: "Score my leads", message: "Score my leads" },
          { label: "Show pipeline overview", message: "Show pipeline overview" },
          { label: "Draft email for hot lead", message: "Draft email for hot lead" },
        ]}
      />
    </div>
  );
}
