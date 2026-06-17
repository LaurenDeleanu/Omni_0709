import React from "react";
import { Handle, Position } from "@xyflow/react";
import { Zap } from "lucide-react";

export default function PowerAutomateNode({ data }: { data: any }) {
  const label = data.label || "Power Automate";
  const config = data.config || {};
  const branches = Array.isArray(config.branches) ? config.branches : [];

  const themeColor = "blue"; // Typical Power Automate color

  return (
    <div className="glass-card min-w-[280px] max-w-[340px] rounded-[1.5rem] border transition-all duration-500 relative group overflow-hidden backdrop-blur-2xl border-blue-500/20 hover:border-blue-400/60 hover:shadow-[0_0_25px_rgba(59,130,246,0.2)] bg-gradient-to-b from-blue-950/40 to-zinc-950/80">
      {/* Animated Glow Background */}
      <div className={`absolute inset-0 bg-gradient-to-tr from-${themeColor}-500/5 via-transparent to-${themeColor}-400/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none`} />
      
      {/* Target Input handle */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className={`w-3 h-3 bg-${themeColor}-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform`} 
        style={{ left: "-6px" }} 
      />

      <div className={`absolute top-2 right-3 flex items-center gap-1 border text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/10 border-blue-500/20 text-blue-400`}>
        ⚡ Integración Externa
      </div>

      {/* Node Header */}
      <div className={`p-4 border-b border-white/5 bg-gradient-to-r from-${themeColor}-500/10 to-transparent flex items-center gap-3 relative z-10`}>
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-sm border shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] group-hover:scale-110 transition-transform duration-300 bg-[#0078D4]/20 border-[#0078D4]/30 text-[#0078D4]`}>
          <Zap className="w-4 h-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className={`text-[9px] text-${themeColor}-300/80 font-black uppercase tracking-[0.2em] mb-0.5`}>Power Automate</p>
          <h4 className="text-[13px] font-bold text-white truncate drop-shadow-md">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2.5 relative z-10">
        <div className="bg-[#1e2330] border border-[#0078D4]/30 shadow-inner rounded-xl p-3 space-y-2 text-[10px]">
          <div className="flex items-center gap-1.5">
            <span className="bg-[#0078D4]/20 text-[#0078D4] border border-[#0078D4]/30 px-1.5 py-0.5 rounded-md font-mono text-[8px] font-bold uppercase shadow-[0_0_10px_rgba(0,120,212,0.2)]">
              POST
            </span>
            <span className="text-zinc-300 font-mono truncate select-all">
              {config.flowUrl || "URL de Flujo no configurada"}
            </span>
          </div>
          
          <div className="text-[9px] text-zinc-400/80 leading-relaxed font-medium">
            Lanza una ejecución del flujo configurado, enviando el contexto actual.
          </div>
        </div>
      </div>

      {/* Source Output Handles */}
      <div className="bg-black/40 border-t border-white/5 px-3 py-2 flex flex-col gap-1.5 relative z-10">
        {branches.map((br: any, i: number) => (
          <div key={`branch-${i}`} className="flex items-center justify-between text-[10px] font-medium text-zinc-300 relative py-1 hover:text-white transition-colors">
            <span className="truncate pr-4 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_5px_rgba(59,130,246,0.5)]"></span>
              {br.label || "Siguiente"}
            </span>
            <Handle 
              type="source" 
              position={Position.Right} 
              id={br.id}
              className="w-2.5 h-2.5 bg-zinc-800 border-2 border-zinc-500 rounded-full hover:bg-blue-400 hover:border-blue-400 hover:scale-125 transition-all !right-[-14px]" 
            />
          </div>
        ))}
        {branches.length === 0 && (
          <div className="flex items-center justify-between text-[10px] font-medium text-zinc-500 relative py-1">
            <span className="italic">No hay ramas configuradas</span>
            <Handle 
              type="source" 
              position={Position.Right} 
              id="default-out"
              className="w-2.5 h-2.5 bg-zinc-800 border-2 border-zinc-600 rounded-full hover:bg-zinc-400 hover:scale-125 transition-all !right-[-14px]" 
            />
          </div>
        )}
      </div>
    </div>
  );
}
