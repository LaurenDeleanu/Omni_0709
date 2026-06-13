"use client";
import React, { useState } from "react";
import { Search, Folder, ChevronDown, ChevronRight, Lock } from "lucide-react";
import { NODE_CATEGORIES } from "./NodeCategories";
import { VariableDescriptor } from "./hooks/usePipelineState";

export default function NodePalette({
  userTier = "FREE",
  onAddStep,
  onUpgradeClick,
  variables = []
}: {
  userTier?: string;
  onAddStep: (type: string, label: string) => void;
  onUpgradeClick?: () => void;
  variables: any[];
}) {
  const [search, setSearch] = useState("");
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    "Mensajes y Captura": true,
    "Comercio y Pagos": true,
    "Lógica y Agentes": true,
    "Integraciones": true,
    "Utilidades": true
  });

  const toggleCategory = (catName: string) => {
    setExpandedCategories(prev => ({ ...prev, [catName]: !prev[catName] }));
  };

  const isTierLocked = (reqTier: "FREE" | "PRO" | "ENTERPRISE") => {
    if (userTier === "ENTERPRISE") return false;
    if (userTier === "PRO") return reqTier === "ENTERPRISE";
    return reqTier !== "FREE";
  };

  return (
    <div className="w-72 border-r border-white/5 bg-zinc-950/70 p-4 flex flex-col gap-4 shrink-0 select-none animate-fade-in custom-scrollbar overflow-y-auto">
      {/* Node Catalog Title */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-1">Paleta de Componentes</h3>
        <p className="text-[10px] text-zinc-500">Arrastra o haz clic para añadir nodos al lienzo</p>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-2.5" />
        <input 
          type="text"
          className="input pl-9 text-xs py-1.5 bg-black/30 border-white/5 focus:border-indigo-500" 
          placeholder="Buscar componentes..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Categories Catalog */}
      <div className="flex flex-col gap-3">
        {NODE_CATEGORIES.map(cat => {
          const filteredItems = cat.items.filter(item => 
            item.l.toLowerCase().includes(search.toLowerCase()) || 
            item.desc.toLowerCase().includes(search.toLowerCase()) || 
            item.v.toLowerCase().includes(search.toLowerCase())
          );

          if (filteredItems.length === 0) return null;

          const isExpanded = expandedCategories[cat.name] !== false;

          return (
            <div key={cat.name} className="flex flex-col">
              <button 
                onClick={() => toggleCategory(cat.name)}
                className="flex items-center justify-between text-[11px] font-bold text-zinc-400 uppercase tracking-wider py-1.5 border-b border-white/5 w-full text-left"
              >
                <span className="flex items-center gap-1.5">
                  <cat.icon className="w-3.5 h-3.5 text-indigo-400" />
                  {cat.name}
                </span>
                {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              </button>

              {isExpanded && (
                <div className="flex flex-col gap-1.5 mt-2">
                  {filteredItems.map(item => {
                    const locked = isTierLocked(item.reqTier);
                    
                    const handleDragStart = (e: React.DragEvent) => {
                      if (locked) {
                        e.preventDefault();
                        if (onUpgradeClick) onUpgradeClick();
                        return;
                      }
                      e.dataTransfer.setData("application/reactflow", item.v);
                      e.dataTransfer.setData("application/reactflow-label", item.l);
                      e.dataTransfer.effectAllowed = "move";
                    };

                    return (
                      <div 
                        key={item.v}
                        draggable={!locked}
                        onDragStart={handleDragStart}
                        onClick={() => {
                          if (locked) {
                            if (onUpgradeClick) onUpgradeClick();
                          } else {
                            onAddStep(item.v, item.l);
                          }
                        }}
                        className={`group relative flex items-start gap-2.5 p-2 rounded-xl border border-white/5 bg-zinc-900/30 text-left transition-all ${
                          locked 
                            ? "opacity-50 cursor-not-allowed hover:bg-zinc-900/40" 
                            : "cursor-grab active:cursor-grabbing hover:bg-indigo-500/5 hover:border-indigo-500/30 hover:-translate-y-0.5"
                        }`}
                      >
                        <span className="text-base p-1 bg-white/5 rounded-lg shrink-0 group-hover:scale-105 transition-transform">{item.icon}</span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs text-zinc-300 font-bold group-hover:text-white transition-colors">{item.l}</span>
                            {locked && (
                              <span className="text-[7px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1 rounded flex items-center gap-0.5 font-bold uppercase shrink-0">
                                <Lock className="w-2 h-2" />
                                {item.reqTier}
                              </span>
                            )}
                          </div>
                          <p className="text-[9px] text-zinc-500 leading-normal line-clamp-2 mt-0.5 group-hover:text-zinc-400 transition-colors">{item.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Scoped Variables explorer section */}
      <div className="border-t border-white/5 mt-4 pt-4">
        <h4 className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <span>📊</span> Variables Scoped
        </h4>
        <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto custom-scrollbar">
          {variables.map(v => (
            <div key={v.name} className="flex items-center justify-between p-2 rounded-xl bg-black/20 border border-white/5 text-[9px] font-mono text-zinc-300">
              <span className="truncate">{"conversation." + v.name}</span>
              <span className="text-[8px] text-indigo-400 font-sans uppercase font-bold shrink-0 px-1.5 py-0.5 bg-indigo-500/10 border border-indigo-500/20 rounded">
                {v.type.substring(0, 6)}
              </span>
            </div>
          ))}
          {variables.length === 0 && (
            <div className="text-[9px] text-zinc-500 text-center py-4 bg-zinc-900/10 rounded-xl border border-dashed border-zinc-800">
              No hay variables guardadas aún. Crea pasos de captura.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
