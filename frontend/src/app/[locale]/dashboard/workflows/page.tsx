"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import PipelineView from "@/components/admin/views/WorkflowCanvas/PipelineView";
import { useState } from "react";
import { Network, Loader2, Plus, X } from "lucide-react";

export default function WorkflowsPage() {
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState("");
  const [newWorkflowDesc, setNewWorkflowDesc] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const queryClient = useQueryClient();

  // 1. Fetch all visual workflows
  const { data: workflows, isLoading } = useQuery({
    queryKey: ["workflowsList"],
    queryFn: async () => { 
      const res = await fetchClient("/visual-workflows"); 
      return Array.isArray(res) ? res : (res.workflows || res.items || []); 
    },
  });

  const handleCreateWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkflowName.trim()) return;
    
    setIsCreating(true);
    try {
      const res = await fetchClient("/visual-workflows", {
        method: "POST",
        body: JSON.stringify({
          name: newWorkflowName,
          description: newWorkflowDesc
        })
      });
      
      await queryClient.invalidateQueries({ queryKey: ["workflowsList"] });
      setIsModalOpen(false);
      setNewWorkflowName("");
      setNewWorkflowDesc("");
      if (res && res.id) {
        setActiveWorkflowId(res.id);
      }
    } catch (err) {
      console.error("Failed to create workflow", err);
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Cargando flujos de automatización...</p>
      </div>
    );
  }

  // Si no hay workflows en absoluto
  if (!workflows || workflows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] max-w-md mx-auto text-center gap-6">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <Network className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">Constructor de Flujos de Automatización</h2>
          <p className="text-sm text-muted-foreground mt-2 mb-6">
            Aún no tienes ningún flujo visual creado. Los flujos te permiten diseñar procesos interactivos y lógicos.
          </p>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="btn-primary px-6 py-2 rounded-xl flex items-center gap-2 mx-auto font-bold"
          >
            <Plus className="w-4 h-4" />
            Crear tu primer Flujo
          </button>
        </div>

        {/* Create Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-zinc-950 border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl relative text-left">
              <button onClick={() => setIsModalOpen(false)} className="absolute top-4 right-4 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
              <h3 className="text-lg font-bold text-white mb-4">Nuevo Flujo Visual</h3>
              <form onSubmit={handleCreateWorkflow} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-zinc-400 mb-1">Nombre del Flujo</label>
                  <input 
                    type="text" 
                    value={newWorkflowName}
                    onChange={e => setNewWorkflowName(e.target.value)}
                    placeholder="Ej: Onboarding de Clientes"
                    className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-400 mb-1">Descripción (Opcional)</label>
                  <textarea 
                    value={newWorkflowDesc}
                    onChange={e => setNewWorkflowDesc(e.target.value)}
                    placeholder="¿Para qué sirve este flujo?"
                    className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm h-20 resize-none"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setIsModalOpen(false)} className="btn-secondary px-4 py-2 text-sm">Cancelar</button>
                  <button type="submit" disabled={isCreating} className="btn-primary px-4 py-2 text-sm flex items-center gap-2">
                    {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Crear Flujo
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    );
  }

  const selectedWorkflowId = activeWorkflowId || workflows[0]?.id;

  return (
    <div className="space-y-6 h-[calc(100vh-10rem)] relative">
      {/* Cabecera con selector */}
      <div className="flex items-center justify-between border-b border-border/50 pb-4">
        <div className="flex items-center gap-4">
          <select
            value={selectedWorkflowId}
            onChange={(e) => setActiveWorkflowId(e.target.value)}
            className="bg-card border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary font-medium min-w-[250px]"
          >
            {workflows.map((w: any) => (
              <option key={w.id} value={w.id}>
                ⚡ {w.name}
              </option>
            ))}
          </select>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1 border border-white/10 hover:border-white/20 rounded-lg"
          >
            <Plus className="w-3.5 h-3.5" /> Nuevo Flujo
          </button>
        </div>
      </div>

      {/* Renderizar panel del Canvas de Flujos */}
      <div className="border border-border rounded-xl overflow-hidden h-full">
        <PipelineView
          key={selectedWorkflowId}
          workflowId={selectedWorkflowId}
          userTier="ENTERPRISE"
          onUpgradeClick={() => {}}
          dynamicModels={[]}
        />
      </div>

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-zinc-950 border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl relative text-left">
            <button onClick={() => setIsModalOpen(false)} className="absolute top-4 right-4 text-zinc-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-lg font-bold text-white mb-4">Nuevo Flujo Visual</h3>
            <form onSubmit={handleCreateWorkflow} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-zinc-400 mb-1">Nombre del Flujo</label>
                <input 
                  type="text" 
                  value={newWorkflowName}
                  onChange={e => setNewWorkflowName(e.target.value)}
                  placeholder="Ej: Onboarding de Clientes"
                  className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-400 mb-1">Descripción (Opcional)</label>
                <textarea 
                  value={newWorkflowDesc}
                  onChange={e => setNewWorkflowDesc(e.target.value)}
                  placeholder="¿Para qué sirve este flujo?"
                  className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm h-20 resize-none focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn-secondary px-4 py-2 text-sm rounded-xl">Cancelar</button>
                <button type="submit" disabled={isCreating} className="btn-primary px-4 py-2 text-sm flex items-center gap-2 rounded-xl">
                  {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  Crear Flujo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
