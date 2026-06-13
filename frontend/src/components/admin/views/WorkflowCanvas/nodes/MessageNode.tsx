import React from "react";
import { Handle, Position } from "@xyflow/react";
import { MessageSquare, HelpCircle, FileText, CheckCircle2 } from "lucide-react";

export default function MessageNode({ data }: { data: any }) {
  const label = data.label || "Mensaje";
  const type = data.type;
  const config = data.config || {};
  const cards = config.cards || [];
  const branches = Array.isArray(config.branches) ? config.branches : [];

  const getValidationIcon = (vType: string) => {
    switch (vType) {
      case "email": return "📧 Email";
      case "phone": return "📱 Teléfono";
      case "number": return "🔢 Número";
      default: return "✏️ Entrada Libre";
    }
  };

  return (
    <div className="glass-card min-w-[280px] max-w-[340px] rounded-2xl border border-blue-500/30 hover:border-blue-500/60 shadow-[0_8px_30px_rgba(59,130,246,0.15)] transition-all duration-300 relative group overflow-hidden bg-gradient-to-br from-blue-950/20 via-zinc-900/95 to-zinc-950/98 backdrop-blur-xl">
      {/* Input Handle on Left */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="w-3 h-3 bg-blue-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ left: "-6px" }} 
      />

      <div className="absolute top-2 right-3 flex items-center gap-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
        {type === "COLLECT_FIELD" ? "📝 Captura" : type === "CHOICE_LIST" ? "📋 Opciones" : "📸 Archivo"}
      </div>

      {/* Node Header */}
      <div className="p-3 border-b border-blue-500/10 bg-blue-500/5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 text-sm">
          <MessageSquare className="w-3.5 h-3.5" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">{type.replace("_", " ")}</p>
          <h4 className="text-xs font-bold text-white truncate">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2.5">
        {/* Render Cards Stack */}
        {cards.map((c: any, idx: number) => {
          if (c.type === "TEXT") {
            return (
              <div key={idx} className="bg-black/30 border border-white/5 rounded-xl p-2.5 text-xs text-zinc-300">
                <span className="text-[9px] font-bold text-blue-400 uppercase tracking-wider block mb-1">TEXTO</span>
                <p className="line-clamp-2 text-zinc-400">{c.content || "Mensaje sin texto"}</p>
              </div>
            );
          }
          return null;
        })}

        {/* Validation Info for COLLECT_FIELD */}
        {type === "COLLECT_FIELD" && (
          <div className="bg-zinc-800/40 border border-zinc-700/50 rounded-xl p-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-zinc-400 font-bold uppercase">Valida:</span>
              <span className="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded border border-blue-500/30 font-semibold">
                {getValidationIcon(config.validationType)}
              </span>
            </div>
            <span className="text-[9px] text-zinc-500 font-mono">
              {"{{" + (config.field || "nombre") + "}}"}
            </span>
          </div>
        )}

        {/* Choice List Option buttons and Handles */}
        {type === "CHOICE_LIST" && (
          <div className="space-y-1.5 mt-2">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">Bifurcaciones por Opción:</span>
            {Array.isArray(config.options) && config.options.map((opt: string, idx: number) => (
              <div key={idx} className="relative flex items-center justify-between p-2 rounded bg-black/40 border border-white/5 hover:border-white/10 transition-colors pr-8">
                <span className="text-[10px] text-zinc-300 font-medium truncate max-w-[200px]">🔘 {opt}</span>
                <Handle 
                  type="source" 
                  position={Position.Right} 
                  id={`option-${idx}`} 
                  className="w-2.5 h-2.5 bg-amber-500 border border-zinc-950 rounded-full hover:scale-125 transition-transform" 
                  style={{ right: "-4px" }} 
                />
              </div>
            ))}
          </div>
        )}

        {/* File Upload constraints */}
        {type === "FILE_UPLOAD" && (
          <div className="bg-zinc-800/40 border border-zinc-700/50 rounded-xl p-2.5 text-xs text-zinc-400 space-y-1">
            <div className="flex justify-between items-center text-[10px]">
              <span>Formato:</span>
              <span className="font-semibold text-zinc-300">{config.acceptType || "Cualquiera"}</span>
            </div>
            <div className="flex justify-between items-center text-[10px]">
              <span>Opcional:</span>
              <span className="font-semibold text-zinc-300">{config.optional ? "Sí" : "No"}</span>
            </div>
            <div className="flex justify-between items-center text-[10px]">
              <span>Extraer texto (OCR):</span>
              <span className="font-semibold text-zinc-300">{config.ocrEnabled ? "Activado" : "Desactivado"}</span>
            </div>
          </div>
        )}

        {/* Transition routes if branches are configured */}
        {branches.length > 0 && (
          <div className="space-y-1.5 mt-2 pt-2 border-t border-white/5">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">Rutas Adicionales (Bifurcaciones):</span>
            {branches.map((b: any, idx: number) => {
              // Only render dynamic branch handle if it's NOT connected to a CHOICE_LIST option
              let isOptionConnected = false;
              if (type === "CHOICE_LIST" && Array.isArray(config.options)) {
                const optIdx = config.options.findIndex((o: string) => o.toLowerCase() === (b.match || "").toLowerCase());
                if (optIdx !== -1) isOptionConnected = true;
              }
              if (isOptionConnected) return null;

              return (
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
              );
            })}
          </div>
        )}
      </div>

      {/* Footer controls */}
      <button 
        type="button" 
        onClick={(e) => { e.stopPropagation(); data.onEdit(); }}
        className="w-full text-center py-2 border-t border-white/5 hover:bg-white/5 text-[10px] text-zinc-400 font-semibold transition-all hover:text-white"
      >
        Configurar Paso
      </button>

      {/* Main output handle (only render if NOT a branching list options step, or choice list) */}
      {type !== "CHOICE_LIST" && (
        <Handle 
          type="source" 
          position={Position.Right} 
          id="default" 
          className="w-3 h-3 bg-blue-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
          style={{ right: "-6px" }} 
        />
      )}
    </div>
  );
}
