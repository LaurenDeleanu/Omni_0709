import React from "react";
import { Handle, Position } from "@xyflow/react";
import { Brain, Sparkles, ChevronRight } from "lucide-react";

export default function AINode({ data }: { data: any }) {
  const label = data.label || "AI Agent";
  const type = data.type;
  const config = data.config || {};
  const branches = Array.isArray(config.branches) ? config.branches : [];

  return (
    <div className="glass-card min-w-[280px] max-w-[340px] rounded-[1.5rem] border border-indigo-500/20 hover:border-indigo-400/60 hover:shadow-[0_0_30px_rgba(99,102,241,0.25)] transition-all duration-500 relative group overflow-hidden bg-gradient-to-b from-indigo-950/40 via-zinc-950/80 to-zinc-950/90 backdrop-blur-2xl">
      {/* Animated Glowing Aura */}
      <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/10 via-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
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
      <div className="p-4 border-b border-white/5 bg-gradient-to-r from-indigo-500/10 to-transparent flex items-center gap-3 relative z-10">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500/30 to-purple-600/10 border border-indigo-400/30 flex items-center justify-center text-indigo-300 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] group-hover:scale-110 transition-transform duration-500 relative">
          <div className="absolute inset-0 rounded-xl bg-indigo-400/20 animate-ping opacity-20" />
          {type === "AI_RESPONDER" ? <Brain className="w-4 h-4 relative z-10" /> : <Sparkles className="w-4 h-4 relative z-10" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[9px] text-indigo-300/80 font-black uppercase tracking-[0.2em] mb-0.5">{type === "AI_RESPONDER" ? "LLM RAG PIPELINE" : "DYNAMIC AUTO-ROUTING"}</p>
          <h4 className="text-[13px] font-bold text-white truncate drop-shadow-md">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2.5">
        {/* Frosted-glass Model and System Prompt Preview */}
        <div className="bg-white/[0.02] border border-white/5 backdrop-blur-md rounded-2xl p-3.5 space-y-2.5 shadow-inner">
          <div className="flex justify-between items-center text-[10px]">
            <span className="text-zinc-400 uppercase font-bold tracking-wider">Modelo:</span>
            <span className="bg-indigo-500/20 text-indigo-300 font-mono text-[9px] border border-indigo-500/30 px-2 py-0.5 rounded-md shadow-[0_0_10px_rgba(99,102,241,0.2)]">
              {config.aiModel || "llama-3.1-8b-instant"}
            </span>
          </div>

          <div className="flex flex-col gap-1 mt-1 border-t border-white/5 pt-2">
            <span className="text-[8px] text-indigo-400/80 font-black uppercase tracking-[0.15em]">System Prompt Override:</span>
            <p className="text-[10px] text-zinc-300 leading-relaxed line-clamp-3 italic">
              &quot;{config.systemPrompt || "Eres un agente amigable..."}&quot;
            </p>
          </div>
        </div>

        {/* Knowledge Base indicator */}
        <div className="flex items-center gap-2.5 text-[10px] text-zinc-300 bg-[#1e2330] border border-indigo-500/20 p-2.5 rounded-xl shadow-inner group-hover:border-indigo-400/40 transition-colors">
          <div className="w-5 h-5 rounded-md bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
            <span className="text-indigo-400 text-xs">📖</span>
          </div>
          <span className="font-medium">
            {config.useKnowledgeBase !== false 
              ? "Base de Conocimientos (RAG)" 
              : "Sin Base de Conocimientos"}
          </span>
        </div>

        {/* Transition routes for AUTONOMOUS_AGENT or AI_RESPONDER with branches */}
        {(type === "AUTONOMOUS_AGENT" || (type === "AI_RESPONDER" && branches.length > 0)) && (
          <div className="space-y-1.5 mt-2">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">Rutas Autónomas (Bifurcaciones):</span>
            {branches.map((b: any, idx: number) => (
              <div key={idx} className="relative flex items-center justify-between p-2.5 rounded-xl bg-black/40 border border-white/5 text-[10px] pr-8 group/branch hover:border-indigo-400/30 transition-colors">
                <span className="text-zinc-300 font-mono truncate max-w-[200px]">
                  <span className="text-indigo-500/50 mr-1">→</span>
                  {b.match}
                </span>
                <Handle 
                  type="source" 
                  position={Position.Right} 
                  id={`branch-${idx}`} 
                  className="w-2.5 h-2.5 bg-indigo-500 border border-zinc-950 rounded-full group-hover/branch:scale-125 group-hover/branch:bg-indigo-400 transition-all shadow-[0_0_10px_rgba(99,102,241,0.5)]" 
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
