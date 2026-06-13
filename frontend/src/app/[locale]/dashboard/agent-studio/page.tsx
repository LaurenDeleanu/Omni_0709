"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import AgentStudioView from "@/components/admin/views/AgentStudio/AgentStudioView";
import { ToolRegistry } from "@/components/agents/ToolRegistry";
import { useState, useRef } from "react";
import { Sparkles, Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";

export default function AgentStudioPage() {
  const queryClient = useQueryClient();
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newAgentName, setNewAgentName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // 1. Fetch all agents
  const { data: agents, isLoading } = useQuery({
    queryKey: ["agentsList"],
    queryFn: async () => { const res = await fetchClient("/agents"); return res.items ?? res; },
  });

  // Fetch dynamic models list
  const { data: modelsData } = useQuery({
    queryKey: ["agentModels"],
    queryFn: () => fetchClient("/agents/models"),
  });

  // 2. Mutation to create an agent
  const createAgentMutation = useMutation({
    mutationFn: (name: string) => fetchClient("/agents", {
      method: "POST",
      body: JSON.stringify({ name, agent_type: "conversational" })
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["agentsList"] });
      setActiveAgentId(data.id);
      setShowCreateDialog(false);
      setNewAgentName("");
      toast.success("Agente de IA creado exitosamente.");
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al crear agente.");
    }
  });

  const handleCreateAgent = () => {
    const name = newAgentName.trim();
    if (name) {
      createAgentMutation.mutate(name);
    }
  };

  const openCreateDialog = () => {
    setNewAgentName("");
    setShowCreateDialog(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Cargando agentes de IA...</p>
      </div>
    );
  }

  // Si no hay agentes en absoluto, mostrar estado vacío
  if (!agents || agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] max-w-md mx-auto text-center gap-6">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <Sparkles className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">Estudio de Agentes de IA</h2>
          <p className="text-sm text-muted-foreground mt-2">
            No tienes ningún agente configurado. Crea tu primer agente inteligente para automatizar tareas e interacciones de la empresa.
          </p>
        </div>
        <Button onClick={openCreateDialog} disabled={createAgentMutation.isPending} className="gap-2">
          {createAgentMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Crear Primer Agente
        </Button>
      </div>
    );
  }

  const selectedAgentId = activeAgentId || agents[0]?.id;

  return (
    <div className="space-y-6">
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
          <Button variant="outline" size="sm" onClick={openCreateDialog} className="gap-1">
            <Plus className="w-3.5 h-3.5" /> Nuevo Agente
          </Button>
        </div>
      </div>

      {/* Renderizar panel Studio del agente seleccionado */}
      <AgentStudioView
        botId={selectedAgentId}
        userTier="ENTERPRISE"
        onUpgradeClick={() => {}}
        dynamicModels={modelsData?.models || []}
      />

      <Dialog open={showCreateDialog} onOpenChange={(open) => { if (!createAgentMutation.isPending) setShowCreateDialog(open); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crear Nuevo Agente de IA</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { e.preventDefault(); handleCreateAgent(); }} className="space-y-4 pt-2">
            <Input
              ref={inputRef}
              placeholder="Nombre del agente (ej: Asistente de Ventas)"
              value={newAgentName}
              onChange={(e) => setNewAgentName(e.target.value)}
              autoFocus
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setShowCreateDialog(false); setNewAgentName(""); }} disabled={createAgentMutation.isPending}>
                Cancelar
              </Button>
              <Button type="submit" disabled={!newAgentName.trim() || createAgentMutation.isPending} className="gap-2">
                {createAgentMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Crear Agente
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ToolRegistry />
    </div>
  );
}
