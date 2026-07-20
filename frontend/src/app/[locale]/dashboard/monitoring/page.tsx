"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import MonitoringView from "@/components/admin/views/Monitoring/MonitoringView";
import { useState } from "react";
import { Activity, Loader2 } from "lucide-react";
import { AgentHealthDashboard } from "@/components/admin/AgentHealthDashboard";
import { RAGMonitor } from "@/components/admin/RAGMonitor";
import { AgentSecurityDashboard } from "@/components/admin/AgentSecurityDashboard";
import { AgentConcurrencyPanel } from "@/components/admin/AgentConcurrencyPanel";
import { AgentRuntimeLive } from "@/components/admin/AgentRuntimeLive";

export default function MonitoringPage() {
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
        <p className="text-sm text-muted-foreground">Cargando observabilidad...</p>
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] max-w-md mx-auto text-center gap-6">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <Activity className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">Observabilidad de IA</h2>
          <p className="text-sm text-muted-foreground mt-2">
            No tienes agentes activos. Por favor crea un agente en el &quot;Estudio de Agentes&quot; para monitorizar latencias y costos.
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
            Métricas de costo, tiempos de respuesta y depuración de trazas de ejecución en tiempo real
          </span>
        </div>
      </div>

      <MonitoringView botId={selectedAgentId} />

      <AgentHealthDashboard />

      <RAGMonitor />

      <AgentSecurityDashboard />

      <AgentConcurrencyPanel />

      <AgentRuntimeLive />
    </div>
  );
}
