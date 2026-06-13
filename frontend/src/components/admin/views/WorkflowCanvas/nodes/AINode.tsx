import React from "react";
import { Handle, Position } from "@xyflow/react";
import { Brain, Sparkles, ChevronRight } from "lucide-react";

export default function AINode({ data }: { data: any }) {
  const label = data.label || "AI Agent";
  const type = data.type;
  const config = data.config || {};
  const branches = Array.isArray(config.branches) ? config.branches : [];

  return (
    <div className="glass-card min-w-[280px] max-w-[340px] rounded-2xl border border-purple-500/30 hover:border-purple-500/60 shadow-[0_8px_30px_rgba(168,85,247,0.15)] transition-all duration-300 relative group overflow-hidden bg-gradient-to-br from-purple-950/30 via-zinc-900/95 to-zinc-950/98 backdrop-blur-xl">
      {/* Input Target handle on Left */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="w-3 h-3 bg-purple-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ left: "-6px" }} 
      />

      <div className="absolute top-2 right-3 flex items-center gap-1 bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
        {type === "AI_RESPONDER" ? "🧠 AI Responder" : "🤖 Agente Autónomo"}
      </div>

      {/* Node Header */}
      <div className="p-3 border-b border-purple-500/10 bg-purple-500/5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 text-sm">
          {type === "AI_RESPONDER" ? <Brain className="w-3.5 h-3.5 animate-pulse" /> : <Sparkles className="w-3.5 h-3.5" />}
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">{type === "AI_RESPONDER" ? "LLM RAG PIPELINE" : "DYNAMIC AUTO-ROUTING"}</p>
          <h4 className="text-xs font-bold text-white truncate">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2.5">
        {/* Model and System Prompt Preview */}
        <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 space-y-1.5">
          <div className="flex justify-between items-center text-[10px]">
            <span className="text-zinc-500 uppercase font-bold">Modelo:</span>
            <span className="bg-purple-500/20 text-purple-300 font-mono text-[9px] border border-purple-500/30 px-1.5 py-0.5 rounded font-bold">
              {config.aiModel || "llama-3.1-8b-instant"}
            </span>
          </div>

          <div className="flex flex-col gap-0.5 mt-1">
            <span className="text-[9px] text-zinc-500 font-bold uppercase">System Prompt Override:</span>
            <p className="text-[10px] text-zinc-400 leading-normal line-clamp-2 italic">
              "{config.systemPrompt || "Eres un agente amigable..."}"
            </p>
          </div>
        </div>

        {/* Knowledge Base indicator */}
        <div className="flex items-center gap-2 text-[10px] text-zinc-400 bg-zinc-800/30 border border-zinc-700/50 p-2 rounded-xl">
          <span className="text-purple-400 text-xs">📖</span>
          <span>
            {config.useKnowledgeBase !== false 
              ? "Acceso a Base de Conocimientos (RAG)" 
              : "Sin Base de Conocimientos"}
          </span>
        </div>

        {/* Transition routes for AUTONOMOUS_AGENT or AI_RESPONDER with branches */}
        {(type === "AUTONOMOUS_AGENT" || (type === "AI_RESPONDER" && branches.length > 0)) && (
          <div className="space-y-1.5 mt-2">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">Rutas Autónomas (Bifurcaciones):</span>
            {branches.map((b: any, idx: number) => (
              <div key={idx} className="relative flex items-center justify-between p-2 rounded bg-black/40 border border-white/5 text-[10px] pr-8">
                <span className="text-zinc-300 font-mono truncate max-w-[200px]">→ {b.match}</span>
                <Handle 
                  type="source" 
                  position={Position.Right} 
                  id={`branch-${idx}`} 
                  className="w-2.5 h-2.5 bg-amber-500 border border-zinc-950 rounded-full hover:scale-125 transition-transform" 
                  style={{ right: "-4px" }} 
                />
              </div>
            ))}
            {type === "AUTONOMOUS_AGENT" && branches.length === 0 && (
              <p className="text-[10px] text-zinc-500 italic text-center py-2">Sin bifurcaciones configuradas</p>
            )}
          </div>
        )}
      </div>

      {/* Node action */}
      <button 
        type="button" 
        onClick={(e) => { e.stopPropagation(); data.onEdit(); }}
        className="w-full text-center py-2 border-t border-white/5 hover:bg-white/5 text-[10px] text-zinc-400 font-semibold transition-all hover:text-white"
      >
        Configurar Agente IA
      </button>

      {/* Main output handle for sequential steps */}
      <Handle 
        type="source" 
        position={Position.Right} 
        id="default" 
        className="w-3 h-3 bg-purple-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ right: "-6px" }} 
      />
    </div>
  );
}
