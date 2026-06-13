import React from "react";
import { Handle, Position } from "@xyflow/react";
import { GitMerge, Scale } from "lucide-react";

export default function LogicNode({ data }: { data: any }) {
  const label = data.label || "Lógica";
  const type = data.type;
  const config = data.config || {};
  const branches = Array.isArray(config.branches) ? config.branches : [];

  return (
    <div className="glass-card min-w-[280px] max-w-[340px] rounded-2xl border border-amber-500/30 hover:border-amber-500/60 shadow-[0_8px_30px_rgba(245,158,11,0.15)] transition-all duration-300 relative group overflow-hidden bg-gradient-to-br from-amber-950/20 via-zinc-900/95 to-zinc-950/98 backdrop-blur-xl">
      {/* Target input handle */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="w-3 h-3 bg-amber-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ left: "-6px" }} 
      />

      <div className="absolute top-2 right-3 flex items-center gap-1 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
        {type === "CONDITION" ? "🔀 Condición" : "⚖️ Test A/B"}
      </div>

      {/* Node Header */}
      <div className="p-3 border-b border-amber-500/10 bg-amber-500/5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 text-sm">
          {type === "CONDITION" ? <GitMerge className="w-3.5 h-3.5" /> : <Scale className="w-3.5 h-3.5" />}
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">{type === "CONDITION" ? "CONDICIONAL" : "DIVISIÓN A/B"}</p>
          <h4 className="text-xs font-bold text-white truncate">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-3">
        {type === "CONDITION" && (
          <div className="space-y-2">
            <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 flex flex-col gap-1">
              <span className="text-[9px] font-bold text-zinc-500 uppercase">Evalúa variable:</span>
              <span className="font-mono text-xs text-amber-400">{"conversation." + (config.checkField || "variable")}</span>
            </div>
            
            <div className="space-y-1.5">
              <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block">Reglas de Salida:</span>
              {branches.map((b: any, idx: number) => (
                <div key={idx} className="relative flex items-center justify-between p-2 rounded bg-black/40 border border-white/5 text-[10px] pr-8">
                  <span className="text-zinc-300 font-mono truncate max-w-[200px]">si coincide "{b.match || ".*"}"</span>
                  <Handle 
                    type="source" 
                    position={Position.Right} 
                    id={`branch-${idx}`} 
                    className="w-2.5 h-2.5 bg-amber-500 border border-zinc-950 rounded-full hover:scale-125 transition-transform" 
                    style={{ right: "-4px" }} 
                  />
                </div>
              ))}
              {branches.length === 0 && (
                <p className="text-[10px] text-zinc-500 italic text-center py-2">Sin reglas de bifurcación</p>
              )}
            </div>
          </div>
        )}

        {type === "AB_TEST" && (
          <div className="space-y-2.5">
            <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 text-[10px] space-y-1">
              <div className="flex justify-between items-center text-zinc-400">
                <span>Tráfico Rama A:</span>
                <span className="font-semibold text-pink-400">{config.branchAWeight ?? 50}%</span>
              </div>
              <div className="flex justify-between items-center text-zinc-400">
                <span>Tráfico Rama B:</span>
                <span className="font-semibold text-violet-400">{100 - (config.branchAWeight ?? 50)}%</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="relative flex items-center justify-center p-2 rounded-xl bg-pink-500/10 border border-pink-500/20 text-[10px] text-pink-300 font-bold">
                RAMA A
                <Handle 
                  type="source" 
                  position={Position.Right} 
                  id="ab-A" 
                  className="w-2.5 h-2.5 bg-pink-500 border border-zinc-950 rounded-full hover:scale-125 transition-transform" 
                  style={{ right: "-4px" }} 
                />
              </div>
              <div className="relative flex items-center justify-center p-2 rounded-xl bg-violet-500/10 border border-violet-500/20 text-[10px] text-violet-300 font-bold">
                RAMA B
                <Handle 
                  type="source" 
                  position={Position.Right} 
                  id="ab-B" 
                  className="w-2.5 h-2.5 bg-violet-500 border border-zinc-950 rounded-full hover:scale-125 transition-transform" 
                  style={{ right: "-4px" }} 
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Node action */}
      <button 
        type="button" 
        onClick={(e) => { e.stopPropagation(); data.onEdit(); }}
        className="w-full text-center py-2 border-t border-white/5 hover:bg-white/5 text-[10px] text-zinc-400 font-semibold transition-all hover:text-white"
      >
        Configurar Lógica
      </button>

      {/* Main output handle (for CONDITION linear default flow) */}
      {type === "CONDITION" && (
        <Handle 
          type="source" 
          position={Position.Right} 
          id="default" 
          className="w-3 h-3 bg-amber-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
          style={{ right: "-6px" }} 
        />
      )}
    </div>
  );
}
