import React from "react";
import { Handle, Position } from "@xyflow/react";
import { Play } from "lucide-react";

export default function StartNode({ data }: { data: any }) {
  const label = data.label || "Bienvenida";
  const config = data.config || {};
  const cards = config.cards || [];

  return (
    <div className="glass-card min-w-[280px] max-w-[320px] rounded-2xl border border-emerald-500/30 hover:border-emerald-500/60 shadow-[0_8px_30px_rgba(16,185,129,0.15)] transition-all duration-300 relative group overflow-hidden bg-gradient-to-br from-emerald-950/40 via-zinc-900/90 to-zinc-950/95 backdrop-blur-xl">
      {/* Visual pulse ring indicating starting entrypoint */}
      <div className="absolute top-2 right-3 flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        Inicio (Start)
      </div>

      {/* Node Header */}
      <div className="p-3 border-b border-emerald-500/10 bg-emerald-500/5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-sm">
          <Play className="w-3.5 h-3.5 fill-current" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Punto de Entrada</p>
          <h4 className="text-xs font-bold text-white truncate">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2">
        {cards.length === 0 ? (
          <p className="text-[10px] text-zinc-500 italic">Mensaje inicial vacío</p>
        ) : (
          cards.map((c: any, idx: number) => (
            <div key={idx} className="bg-black/30 border border-white/5 rounded-xl p-2.5 text-xs text-zinc-300">
              <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-wider block mb-1">TEXTO</span>
              <p className="line-clamp-3 leading-normal text-zinc-400">{c.content || "Mensaje sin texto"}</p>
            </div>
          ))
        )}
      </div>

      {/* Bottom Button to trigger editing */}
      <button 
        type="button" 
        onClick={(e) => { e.stopPropagation(); data.onEdit(); }}
        className="w-full text-center py-2 border-t border-white/5 hover:bg-white/5 text-[10px] text-zinc-400 font-semibold transition-all hover:text-white"
      >
        Configurar Bienvenida
      </button>

      {/* Output handle on the Right */}
      <Handle 
        type="source" 
        position={Position.Right} 
        id="default" 
        className="w-3 h-3 bg-emerald-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ right: "-6px" }} 
      />
    </div>
  );
}
