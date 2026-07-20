"use client";
import React, { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { ArrowDownRight, Edit, Trash2, Copy, Move, Bot, LayoutGrid, Check, X } from "lucide-react";
import { Node, Edge } from "@xyflow/react";

import PipelineToolbar from "./PipelineToolbar";
import NodePalette from "./NodePalette";
import PipelineCanvas from "./PipelineCanvas";
import NodeInspector from "./NodeInspector";
import SimulatorPanel from "./SimulatorPanel";

import { usePipelineState } from "./hooks/usePipelineState";
import { getLayoutedElements } from "./utils/layoutEngine";
import { nodeIcons, NODE_CATEGORIES } from "./NodeCategories";
import { getDefaultConfig } from "./utils/configDefaults";
import { fetchClient } from "@/lib/api/client";

export default function PipelineView({
  workflowId,
  userTier = "FREE",
  onUpgradeClick,
  dynamicModels = []
}: {
  workflowId: string;
  userTier?: string;
  onUpgradeClick?: () => void;
  dynamicModels: any[];
}) {
  const {
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
  } = usePipelineState(workflowId);

  const [viewMode, setViewMode] = useState<"linear" | "canvas">("canvas");
  const [showSimulator, setShowSimulator] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingStep, setEditingStep] = useState<any | null>(null);

  const [configuringNewType, setConfiguringNewType] = useState<{ v: string; l: string } | null>(null);
  const [newStepLabel, setNewStepLabel] = useState("");
  const [newStepConfig, setNewStepConfig] = useState<any>({});
  const [newStepPosition, setNewStepPosition] = useState<{ x: number; y: number } | undefined>(undefined);

  const [schedules, setSchedules] = useState<any[]>([]);

  // Canvas Nodes & Edges visual state
  const [canvasNodes, setCanvasNodes] = useState<Node[]>([]);
  const [canvasEdges, setCanvasEdges] = useState<Edge[]>([]);

  // Fetch schedules for BOOKING node support
  useEffect(() => {
    async function loadResources() {
      try {
        const d = await fetchClient("/schedules");
        setSchedules(Array.isArray(d) ? d : (d.schedules || d));
      } catch (e) {
        console.error("Failed loading schedules", e);
      }
    }
    loadResources();
  }, [workflowId]);

  // Trigger opening step configuration modal before adding to canvas
  const triggerStepConfiguration = (type: string, label: string, position?: { x: number; y: number }) => {
    let foundItem: any = null;
    for (const cat of NODE_CATEGORIES) {
      const match = cat.items.find(it => it.v === type);
      if (match) {
        foundItem = match;
        break;
      }
    }
    if (!foundItem) return;

    setNewStepPosition(position);
    setConfiguringNewType(foundItem);
    setNewStepLabel(label || foundItem.l);
    try {
      setNewStepConfig(JSON.parse(getDefaultConfig(type)));
    } catch {
      setNewStepConfig({});
    }
    setShowAddModal(true);
  };

  // Handle Drag-and-Drop Node Addition from left palette
  const handleDropNode = (e: React.DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData("application/reactflow");
    const label = e.dataTransfer.getData("application/reactflow-label");
    if (!type) return;

    // Estimate coordinates inside visual drop boundaries
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    const x = e.clientX - rect.left - 150;
    const y = e.clientY - rect.top - 120;

    triggerStepConfiguration(type, label, { x, y });
  };

  // Trigger auto layout organize visual positions
  const handleAutoLayout = async () => {
    if (!steps.length) return;
    const layouted = getLayoutedElements(steps.map(s => ({ ...s, position: { x: 0, y: 0 }, data: { ...s, type: s.type } } as any)), ({ direction: "TB" } as any));
    try {
      await Promise.all(layouted.map(async (node) => {
        const cfg = typeof node.data.config === "string" ? JSON.parse(node.data.config) : node.data.config;
        cfg.position = { x: Math.round(node.position.x), y: Math.round(node.position.y) };
        await updateStep(node.id, { config: JSON.stringify(cfg) });
      }));
      toast.success("Layout aplicado");
    } catch {
      toast.error("Error al aplicar auto-layout");
    }
  };

  // Delete node helper
  const handleDeleteStep = async (id: string) => {
    if (editingStep && editingStep.id === id) {
      setEditingStep(null);
    }
    await deleteStep(id);
  };

  // Duplicate node helper
  const handleDuplicateStep = async (id: string) => {
    await duplicateStep(id);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] gap-3 text-zinc-400">
        <span className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin"></span>
        <p className="text-sm font-semibold">Cargando constructor de flujos...</p>
      </div>
    );
  }

  return (
    <div className="p-8 animate-fade-in flex flex-col h-[calc(100vh-100px)] relative overflow-hidden select-none">
      {/* 1. Header toolbar */}
      <PipelineToolbar 
        workflowId={workflowId}
        viewMode={viewMode}
        setViewMode={setViewMode}
        onAutoLayout={handleAutoLayout}
        showSimulator={showSimulator}
        setShowSimulator={setShowSimulator}
        onAddStep={() => setShowAddModal(true)}
      />

      {/* 2. Main builder workplace */}
      <div className="flex-1 flex gap-4 overflow-hidden mt-2 relative rounded-2xl border border-white/5 bg-zinc-950/20 backdrop-blur-sm">
        
        {/* Canvas view mode */}
        {viewMode === "canvas" ? (
          <>
            {/* Left nodes catalog palette */}
            <NodePalette 
              userTier={userTier}
              onUpgradeClick={onUpgradeClick}
              onAddStep={(type, label) => triggerStepConfiguration(type, label)}
              variables={getCollectedVariables()}
            />

            {/* Center Canvas area */}
            <div 
              className="flex-1 relative bg-zinc-950 overflow-hidden"
              onDrop={handleDropNode}
              onDragOver={e => e.preventDefault()}
            >
              {steps.length > 0 ? (
                <PipelineCanvas 
                  steps={steps}
                  workflowId={workflowId}
                  onEdit={setEditingStep}
                  fetchSteps={fetchSteps}
                  onSaveStep={updateStep}
                  canvasNodes={canvasNodes}
                  setCanvasNodes={setCanvasNodes}
                  canvasEdges={canvasEdges}
                  setCanvasEdges={setCanvasEdges}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                  <LayoutGrid className="w-12 h-12 text-zinc-600 animate-pulse" />
                  <div>
                    <h3 className="text-sm font-bold text-white mb-1">Pipeline Vacío</h3>
                    <p className="text-xs text-zinc-500 max-w-[280px]">Arrastra componentes desde la paleta izquierda o añade un paso arriba.</p>
                  </div>
                  <button 
                    onClick={() => triggerStepConfiguration("COLLECT_FIELD", "Inicio")}
                    className="btn-primary text-xs py-2 px-4"
                  >
                    + Añadir Primer Paso
                  </button>
                </div>
              )}

              {/* Floating Simulator chat component */}
              {showSimulator && (
                <div className="absolute bottom-4 right-4 z-[99]">
                  <SimulatorPanel 
                    workflowId={workflowId}
                    onClose={() => setShowSimulator(false)}
                  />
                </div>
              )}
            </div>

            {/* Right Inspector editing panel */}
            {editingStep && (
              <NodeInspector 
                editingStep={editingStep}
                setEditingStep={setEditingStep}
                steps={steps}
                schedules={schedules}
                dynamicModels={dynamicModels}
                onSave={updateStep}
                onClose={() => setEditingStep(null)}
                onDelete={handleDeleteStep}
                onDuplicate={handleDuplicateStep}
              />
            )}
          </>
        ) : (
          /* Linear view list fallback */
          <div className="flex-1 p-6 overflow-y-auto custom-scrollbar flex flex-col gap-4 max-w-4xl mx-auto py-10 w-full">
            {steps.map((step, i) => {
              let hasBranches = false;
              let branchTargets: string[] = [];
              try {
                const c = typeof step.config === "string" ? JSON.parse(step.config) : step.config || {};
                hasBranches = Array.isArray(c.branches) && c.branches.length > 0;
                if (hasBranches) {
                  branchTargets = c.branches.map((b: any) => {
                    const target = steps.find(st => st.id === b.goToStepId || st.order === b.goToStepOrder);
                    return target ? `#${target.order} ${target.label || target.name}` : `Opción "${b.match}"`;
                  });
                }
              } catch {}

              return (
                <div 
                  key={step.id} 
                  className="flex items-center gap-4 bg-zinc-900/40 border border-white/5 p-4 rounded-2xl hover:border-white/10 hover:bg-zinc-900/60 transition-all group"
                >
                  <span className="text-2xl p-2 bg-white/5 rounded-xl border border-white/5">{nodeIcons[step.type] || "📦"}</span>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-zinc-500 font-bold">PASO #{step.order}</span>
                      <span className="text-xs bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded font-bold uppercase tracking-wider">{step.type}</span>
                      <span className="text-sm font-bold text-white truncate">{step.label || step.name}</span>
                    </div>

                    {hasBranches && (
                      <p className="text-[10px] text-amber-400 font-semibold mt-1.5 flex flex-wrap gap-1.5 items-center">
                        <span className="text-zinc-500 font-bold uppercase tracking-wider">Saltos a:</span>
                        {branchTargets.map((t, idx) => (
                          <span key={idx} className="bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded font-mono">{t}</span>
                        ))}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => {
                        const newOrder = steps.map((s, idx) => {
                          if (idx === i) return { id: s.id, order: i };
                          if (idx === i - 1) return { id: s.id, order: i + 1 };
                          return { id: s.id, order: s.order };
                        });
                        if (i > 0) reorderSteps(newOrder);
                      }} 
                      disabled={i === 0}
                      className="p-1.5 hover:bg-white/5 rounded text-zinc-400 disabled:opacity-30"
                    >
                      ▲
                    </button>
                    <button 
                      onClick={() => {
                        const newOrder = steps.map((s, idx) => {
                          if (idx === i) return { id: s.id, order: i + 2 };
                          if (idx === i + 1) return { id: s.id, order: i + 1 };
                          return { id: s.id, order: s.order };
                        });
                        if (i < steps.length - 1) reorderSteps(newOrder);
                      }} 
                      disabled={i === steps.length - 1}
                      className="p-1.5 hover:bg-white/5 rounded text-zinc-400 disabled:opacity-30"
                    >
                      ▼
                    </button>
                    <button onClick={() => { setViewMode("canvas"); setEditingStep(step); }} className="p-1.5 hover:bg-white/5 rounded text-indigo-400" title="Editar">✏️</button>
                    <button onClick={() => handleDuplicateStep(step.id)} className="p-1.5 hover:bg-white/5 rounded text-zinc-400" title="Duplicar">📋</button>
                    <button onClick={() => handleDeleteStep(step.id)} className="p-1.5 hover:bg-rose-500/10 rounded text-rose-400" title="Eliminar">🗑</button>
                  </div>
                </div>
              );
            })}
            {steps.length === 0 && (
              <div className="text-center py-16">
                <p className="text-sm text-zinc-500 mb-4">Pipeline vacío</p>
                <button onClick={() => triggerStepConfiguration("COLLECT_FIELD", "Inicio")} className="btn-primary text-xs py-2 px-4">+ Añadir Primer Paso</button>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Add Step Selection Modal */}
      {showAddModal && (
        <div 
          className="fixed inset-0 z-[150] flex items-center justify-center p-4 animate-fade-in"
          style={{ background: "rgba(0,0,0,0.85)", backdropFilter: "blur(12px)" }}
          onClick={(e) => { 
            if (e.target === e.currentTarget) {
              setShowAddModal(false); 
              setConfiguringNewType(null);
              setNewStepPosition(undefined);
            }
          }}
        >
          <div className="glass-card w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col rounded-2xl shadow-2xl animate-slide-up bg-zinc-950/80 border border-white/10">
            {/* Header */}
            <div className="p-6 border-b border-white/5 flex justify-between items-center bg-zinc-900/50">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <span>➕</span> {!configuringNewType ? "Añadir Nuevo Paso" : `Configurar Nuevo Paso: ${configuringNewType.l}`}
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  {!configuringNewType 
                    ? "Selecciona el tipo de nodo que quieres agregar al flujo de conversación."
                    : "Define los parámetros iniciales de este nodo antes de agregarlo al lienzo."
                  }
                </p>
              </div>
              <button 
                type="button" 
                onClick={() => {
                  setShowAddModal(false);
                  setConfiguringNewType(null);
                  setNewStepPosition(undefined);
                }} 
                className="text-zinc-400 hover:text-white transition-colors p-2 bg-black/20 rounded-full hover:bg-white/10 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {/* Body */}
            {!configuringNewType ? (
              /* Phase 1: Selector */
              <div className="p-6 overflow-y-auto custom-scrollbar flex-1 relative space-y-6">
                {NODE_CATEGORIES.map((cat) => (
                  <div key={cat.name} className="space-y-3">
                    <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-wider border-b border-white/5 pb-1.5 flex items-center gap-2">
                      <cat.icon className="w-4 h-4" /> {cat.name}
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {cat.items.map((item) => {
                        const locked = userTier !== "ENTERPRISE" && (userTier === "PRO" ? item.reqTier === "ENTERPRISE" : item.reqTier !== "FREE");
                        
                        return (
                          <button
                            key={item.v}
                            type="button"
                            onClick={() => {
                              if (locked) {
                                if (onUpgradeClick) onUpgradeClick();
                              } else {
                                setConfiguringNewType(item);
                                setNewStepLabel(item.l);
                                try {
                                  setNewStepConfig(JSON.parse(getDefaultConfig(item.v)));
                                } catch {
                                  setNewStepConfig({});
                                }
                              }
                            }}
                            className={`group flex items-start gap-3 p-3 rounded-xl border border-white/5 bg-zinc-900/30 text-left transition-all ${
                              locked 
                                ? "opacity-50 cursor-not-allowed hover:bg-zinc-900/40" 
                                : "cursor-pointer hover:bg-indigo-500/5 hover:border-indigo-500/30 hover:-translate-y-0.5"
                            }`}
                          >
                            <span className="text-xl p-2 bg-white/5 rounded-lg shrink-0 group-hover:scale-105 transition-transform">{item.icon}</span>
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs text-zinc-300 font-bold group-hover:text-white transition-colors">{item.l}</span>
                                {locked && (
                                  <span className="text-[7px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1 rounded flex items-center gap-0.5 font-bold uppercase shrink-0">
                                    🔒 {item.reqTier}
                                  </span>
                                )}
                              </div>
                              <p className="text-[10px] text-zinc-500 leading-normal mt-1 group-hover:text-zinc-400 transition-colors">{item.desc}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Phase 2: Configurator */
              <>
                <div className="p-6 overflow-y-auto custom-scrollbar flex-1 relative space-y-5 bg-black/20">
                  {/* Common label field */}
                  <div className="glass p-4 border border-white/5 rounded-xl bg-zinc-900/30">
                    <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Nombre / Identificador del Paso</label>
                    <input 
                      className="input text-xs" 
                      placeholder="Ej: Saludar al usuario..." 
                      value={newStepLabel} 
                      onChange={e => setNewStepLabel(e.target.value)} 
                      required 
                    />
                  </div>

                  {/* Type specific message/cards if applicable */}
                  {["WELCOME", "COLLECT_FIELD", "CHOICE_LIST", "FILE_UPLOAD", "BOOKING", "PAYMENT", "COMPLETED"].includes(configuringNewType.v) && (
                    <div className="glass p-4 border border-white/5 rounded-xl bg-zinc-900/30">
                      <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1.5">Mensaje del Bot (Contenido de texto inicial)</label>
                      <textarea 
                        className="input text-xs" 
                        rows={3}
                        placeholder="Escribe el mensaje que el bot enviará en este paso..."
                        value={newStepConfig.cards?.[0]?.content || ""}
                        onChange={e => {
                          const val = e.target.value;
                          setNewStepConfig((prev: any) => {
                            const cards = Array.isArray(prev.cards) ? [...prev.cards] : [];
                            if (cards.length > 0) {
                              cards[0] = { ...cards[0], content: val };
                            } else {
                              cards.push({ id: "card-1", type: "TEXT", content: val });
                            }
                            return { ...prev, cards };
                          });
                        }}
                      />
                    </div>
                  )}

                  {configuringNewType.v === "COLLECT_FIELD" && (
                    <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Parámetros de Captura</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Nombre de la Variable (Guardar respuesta en)</label>
                        <input 
                          className="input text-xs font-mono" 
                          placeholder="Ej: user_email" 
                          value={newStepConfig.field || ""}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, field: e.target.value.trim() }))}
                        />
                      </div>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Tipo de Validación</label>
                        <select 
                          className="input text-xs" 
                          value={newStepConfig.validationType || "none"}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, validationType: e.target.value }))}
                        >
                          <option value="none">Ninguna (Entrada Libre)</option>
                          <option value="email">📧 Correo Electrónico</option>
                          <option value="phone">📱 Teléfono Internacional</option>
                          <option value="number">🔢 Número</option>
                        </select>
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "CHOICE_LIST" && (
                    <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Lista de Opciones (WhatsApp Buttons)</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable de Destino</label>
                        <input 
                          className="input text-xs font-mono" 
                          value={newStepConfig.field || "seleccion"}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, field: e.target.value.trim() }))}
                        />
                      </div>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Opciones (Separadas por comas)</label>
                        <input 
                          className="input text-xs" 
                          placeholder="Sí, No, Consultar" 
                          value={Array.isArray(newStepConfig.options) ? newStepConfig.options.join(", ") : ""}
                          onChange={e => {
                            const opts = e.target.value.split(",").map(o => o.trim()).filter(Boolean);
                            const updatedBranches = opts.map(o => ({
                              match: o,
                              goToStepId: "",
                              goToStepOrder: 0
                            }));
                            setNewStepConfig((prev: any) => ({ ...prev, options: opts, branches: updatedBranches }));
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "FILE_UPLOAD" && (
                    <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Subida de Archivos</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar URL</label>
                        <input 
                          className="input text-xs font-mono" 
                          value={newStepConfig.field || "archivo_url"}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, field: e.target.value.trim() }))}
                        />
                      </div>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Tipos de archivo aceptados</label>
                        <select 
                          className="input text-xs" 
                          value={newStepConfig.acceptType || "any"}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, acceptType: e.target.value }))}
                        >
                          <option value="any">Cualquier Archivo</option>
                          <option value="image">🖼️ Sólo Imágenes (PNG, JPG)</option>
                          <option value="pdf">📄 Sólo Documentos PDF</option>
                        </select>
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "AI_RESPONDER" && (
                    <div className="glass p-4 border border-purple-500/20 rounded-xl bg-purple-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">🧠 LLM Inteligente (RAG)</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Respuesta</label>
                        <input 
                          className="input text-xs font-mono" 
                          value={newStepConfig.field || "respuesta_ia"}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, field: e.target.value.trim() }))}
                        />
                      </div>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">System Prompt Override</label>
                        <textarea 
                          className="input text-xs" 
                          rows={3}
                          placeholder="Instrucciones para la personalidad..."
                          value={newStepConfig.systemPrompt || ""}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, systemPrompt: e.target.value }))}
                        />
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "AUTONOMOUS_AGENT" && (
                    <div className="glass p-4 border border-purple-500/20 rounded-xl bg-purple-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">🤖 Agente Autónomo Ventas</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Instrucciones Directivas</label>
                        <textarea 
                          className="input text-xs" 
                          rows={4}
                          placeholder="Eres un agente de ventas libre..."
                          value={newStepConfig.systemPrompt || ""}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, systemPrompt: e.target.value }))}
                        />
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "API_CALL" && (
                    <div className="glass p-4 border border-orange-500/20 rounded-xl bg-orange-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-orange-400">🔌 Integración Webhook API</h4>
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Método</label>
                          <select 
                            className="input text-xs" 
                            value={newStepConfig.apiMethod || "POST"}
                            onChange={e => setNewStepConfig((prev: any) => ({ ...prev, apiMethod: e.target.value }))}
                          >
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                            <option value="PUT">PUT</option>
                          </select>
                        </div>
                        <div className="col-span-2">
                          <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">URL de Destino</label>
                          <input 
                            className="input text-xs font-mono" 
                            placeholder="https://api.ejemplo.com/hook" 
                            value={newStepConfig.apiUrl || ""}
                            onChange={e => setNewStepConfig((prev: any) => ({ ...prev, apiUrl: e.target.value.trim() }))}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "BOOKING" && (
                    <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">📅 Agenda de Citas</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Fecha</label>
                        <input 
                          className="input text-xs font-mono" 
                          value={newStepConfig.field || "fecha_cita"}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, field: e.target.value.trim() }))}
                        />
                      </div>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Vincular Agenda</label>
                        <select 
                          className="input text-xs" 
                          value={newStepConfig.scheduleId || ""}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, scheduleId: e.target.value }))}
                        >
                          <option value="">-- Calendario General (Automático) --</option>
                          {schedules.map(sch => (
                            <option key={sch.id} value={sch.id}>{sch.name}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "PAYMENT" && (
                    <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">💵 Cobro Fijo</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Monto Fijo</label>
                          <input 
                            type="number"
                            className="input text-xs" 
                            value={newStepConfig.amount || 0}
                            onChange={e => setNewStepConfig((prev: any) => ({ ...prev, amount: parseFloat(e.target.value) || 0 }))}
                          />
                        </div>
                        <div>
                          <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Moneda</label>
                          <select 
                            className="input text-xs" 
                            value={newStepConfig.currency || "USD"}
                            onChange={e => setNewStepConfig((prev: any) => ({ ...prev, currency: e.target.value }))}
                          >
                            <option value="USD">USD ($)</option>
                            <option value="MXN">MXN ($)</option>
                            <option value="EUR">EUR (€)</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "CREATE_LEAD" && (
                    <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">👤 Actualización CRM Funnel Stage</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Mover Lead a la Etapa:</label>
                        <select 
                          className="input text-xs capitalize" 
                          value={newStepConfig.newLeadStage || "qualified"}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, newLeadStage: e.target.value }))}
                        >
                          <option value="lead">Prospecto</option>
                          <option value="qualified">Calificado</option>
                          <option value="won">Ganado/Cliente</option>
                        </select>
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "HUMAN_TAKEOVER" && (
                    <div className="glass p-4 border border-rose-500/20 rounded-xl bg-rose-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400">🎧 Soporte Humano (Handoff)</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Mensaje de Despedida</label>
                        <textarea 
                          className="input text-xs" 
                          rows={3}
                          value={newStepConfig.prompt || ""}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, prompt: e.target.value }))}
                        />
                      </div>
                    </div>
                  )}

                  {configuringNewType.v === "CALL_WORKFLOW" && (
                    <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">🔄 Llamar Sub-flujo</h4>
                      <div>
                        <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">ID Bot Destino</label>
                        <input 
                          className="input text-xs font-mono" 
                          placeholder="bot_xxx123..."
                          value={newStepConfig.workflowId || ""}
                          onChange={e => setNewStepConfig((prev: any) => ({ ...prev, workflowId: e.target.value.trim() }))}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer Actions */}
                <div className="p-6 border-t border-white/5 flex gap-3 bg-zinc-900/50">
                  <button 
                    type="button" 
                    onClick={() => {
                      setConfiguringNewType(null);
                      setNewStepPosition(undefined);
                    }}
                    className="btn-secondary flex-1 py-2 text-xs font-bold uppercase tracking-wider transition-all"
                  >
                    Atrás
                  </button>
                  <button 
                    type="button" 
                    onClick={async () => {
                      if (!configuringNewType) return;
                      await addStep(configuringNewType.v, newStepLabel, newStepConfig, newStepPosition);
                      setShowAddModal(false);
                      setConfiguringNewType(null);
                      setNewStepPosition(undefined);
                    }}
                    className="btn-primary flex-1 py-2 text-xs font-bold uppercase tracking-wider transition-all animate-pulse"
                  >
                    Añadir al Lienzo
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
