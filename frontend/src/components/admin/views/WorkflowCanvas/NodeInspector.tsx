"use client";
import React, { useState, useEffect } from "react";
import { X, Settings, Trash2, Copy, Plus, ArrowDownRight, GitMerge, AlertCircle, Link, HelpCircle, Bot } from "lucide-react";
import { Step } from "@/shared";
import { CardsEditor } from "./editors/CardsEditor";
import { NodeEditorFields } from "./editors/NodeEditors";
import { nodeIcons } from "./NodeCategories";

export default function NodeInspector({
  editingStep,
  setEditingStep,
  steps,

  dynamicModels = [],
  onSave,
  onClose,
  onDelete,
  onDuplicate
}: {
  editingStep: Step;
  setEditingStep: (s: Step | null) => void;
  steps: Step[];

  dynamicModels: any[];
  onSave: (stepId: string, updatedData: Partial<Step>) => Promise<void>;
  onClose: () => void;
  onDelete: (stepId: string) => Promise<void>;
  onDuplicate: (stepId: string) => Promise<void>;
}) {
  const [label, setLabel] = useState(editingStep.label || editingStep.name);
  const [config, setConfig] = useState<any>({});
  const [isLocalSaving, setIsLocalSaving] = useState(false);

  useEffect(() => {
    setLabel(editingStep.label || editingStep.name);
    try {
      setConfig(typeof editingStep.config === "string" ? JSON.parse(editingStep.config) : editingStep.config || {});
    } catch {
      setConfig({});
    }
  }, [editingStep]);

  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  const handleConfigChange = (newConfig: any) => {
    setConfig(newConfig);
    if (debounceTimer) clearTimeout(debounceTimer);
    const timer = setTimeout(() => {
      const updatedStep = { ...editingStep, label, config: JSON.stringify(newConfig) };
      onSave(editingStep.id, { label, config: JSON.stringify(newConfig) });
    }, 500);
    setDebounceTimer(timer);
  };

  const handleFieldChange = (key: string, value: any) => {
    const updated = { ...config, [key]: value };
    handleConfigChange(updated);
  };

  const handleLabelChange = (val: string) => {
    setLabel(val);
    onSave(editingStep.id, { label: val, config: JSON.stringify(config) });
  };

  const stepType = editingStep.type;

  return (
    <div className="w-[450px] border-l border-white/5 bg-zinc-950/70 p-6 flex flex-col gap-6 shrink-0 h-full overflow-y-auto custom-scrollbar relative z-20">
      {/* Header Info */}
      <div className="flex justify-between items-start border-b border-white/5 pb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl p-2 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
            {nodeIcons[stepType] || "📦"}
          </span>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
              <Settings className="w-4 h-4 text-indigo-400" />
              Inspector de Nodo
            </h3>
            <span className="badge badge-indigo text-[9px] uppercase font-bold tracking-wider mt-1">{stepType}</span>
          </div>
        </div>
        <button 
          type="button" 
          onClick={onClose}
          className="p-1.5 hover:bg-white/5 rounded-full text-zinc-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Quick Actions Panel */}
      <div className="flex gap-2">
        <button 
          onClick={() => onDuplicate(editingStep.id)}
          className="flex-1 btn-secondary text-xs py-2 px-3 flex items-center justify-center gap-1.5 hover:text-indigo-400"
        >
          <Copy className="w-3.5 h-3.5" /> Duplicar Paso
        </button>
        <button 
          onClick={() => onDelete(editingStep.id)}
          className="flex-1 btn-secondary text-xs py-2 px-3 flex items-center justify-center gap-1.5 hover:text-rose-400 border-rose-500/20 hover:border-rose-500/40"
        >
          <Trash2 className="w-3.5 h-3.5" /> Eliminar Paso
        </button>
      </div>

      {/* Editor Body */}
      <div className="flex flex-col gap-5">
        {/* Step Label name (Common to all) */}
        <div className="glass p-4 border border-white/5 rounded-xl bg-zinc-900/30">
          <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Nombre / Identificador del Paso</label>
          <input 
            className="input text-xs" 
            placeholder="Ej: Solicitar Correo..." 
            value={label} 
            onChange={e => handleLabelChange(e.target.value)} 
            required 
          />
        </div>

        {/* WELCOME / COLLECT_FIELD / CHOICE_LIST / FILE_UPLOAD Cards messaging */}
        {["WELCOME", "COLLECT_FIELD", "CHOICE_LIST", "FILE_UPLOAD", "BOOKING", "PAYMENT", "COMPLETED", "AI_RESPONDER", "AUTONOMOUS_AGENT"].includes(stepType) && (
          <div className="glass p-4 border border-white/5 rounded-xl bg-zinc-900/30">
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3 text-zinc-400">Mensajes del Bot (Burbujas)</h4>
            <CardsEditor stepType={stepType} config={config} onChange={handleConfigChange} />
          </div>
        )}

        <NodeEditorFields
          stepType={stepType}
          config={config}
          handleFieldChange={handleFieldChange}
          handleConfigChange={handleConfigChange}
          steps={steps}
          dynamicModels={dynamicModels}
          editingStepId={editingStep.id}
        />
      </div>

      <div className="flex gap-3 mt-4 pt-4 border-t border-white/5 pb-10">
        <button 
          type="button" 
          onClick={onClose}
          className="btn-secondary flex-1 py-2 text-xs font-semibold"
        >
          Cerrar Inspector
        </button>
      </div>
    </div>
  );
}
