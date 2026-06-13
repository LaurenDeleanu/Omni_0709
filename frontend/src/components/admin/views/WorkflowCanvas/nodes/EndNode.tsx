import React from "react";
import { Handle, Position } from "@xyflow/react";
import { CheckCircle } from "lucide-react";

export default function EndNode({ data }: { data: any }) {
  const label = data.label || "Completado";

  return (
    <div className="glass-card min-w-[260px] max-w-[300px] rounded-2xl border border-rose-500/30 hover:border-rose-500/60 shadow-[0_8px_30px_rgba(239,68,68,0.15)] transition-all duration-300 relative group overflow-hidden bg-gradient-to-br from-rose-950/40 via-zinc-900/90 to-zinc-950/95 backdrop-blur-xl">
      {/* Target handle on Left */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="w-3 h-3 bg-rose-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ left: "-6px" }} 
      />

      <div className="absolute top-2 right-3 flex items-center gap-1.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
        Fin (End)
      </div>

      {/* Node Header */}
      <div className="p-3 border-b border-rose-500/10 bg-rose-500/5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400 text-sm">
          <CheckCircle className="w-3.5 h-3.5 fill-current" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Finalizar</p>
          <h4 className="text-xs font-bold text-white truncate">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3">
        <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 text-[10px] leading-relaxed text-zinc-400 text-center">
          La conversación se da por completada con éxito. El bot se detendrá para este usuario hasta que envíe un nuevo mensaje de reinicio.
        </div>
      </div>

      {/* Bottom Button */}
      <button 
        type="button" 
        onClick={(e) => { e.stopPropagation(); data.onEdit(); }}
        className="w-full text-center py-2 border-t border-white/5 hover:bg-white/5 text-[10px] text-zinc-400 font-semibold transition-all hover:text-white"
      >
        Configurar Fin
      </button>
    </div>
  );
}
