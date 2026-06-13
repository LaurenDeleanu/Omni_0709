import React from "react";
import { Handle, Position } from "@xyflow/react";
import { Network, UserCheck, Headset, FolderGit } from "lucide-react";

export default function ActionNode({ data }: { data: any }) {
  const label = data.label || "Acción";
  const type = data.type;
  const config = data.config || {};
  const branches = Array.isArray(config.branches) ? config.branches : [];

  const getActionIcon = () => {
    switch (type) {
      case "API_CALL": return <Network className="w-3.5 h-3.5" />;
      case "CREATE_LEAD": return <UserCheck className="w-3.5 h-3.5" />;
      case "CALL_WORKFLOW": return <FolderGit className="w-3.5 h-3.5" />;
      default: return <Headset className="w-3.5 h-3.5" />;
    }
  };

  const getActionTheme = () => {
    switch (type) {
      case "HUMAN_TAKEOVER": return "border-rose-500/30 hover:border-rose-500/60 shadow-[0_8px_30px_rgba(239,68,68,0.15)] bg-gradient-to-br from-rose-950/20 via-zinc-900/95 to-zinc-950/98";
      case "API_CALL": return "border-orange-500/30 hover:border-orange-500/60 shadow-[0_8px_30px_rgba(249,115,22,0.15)] bg-gradient-to-br from-orange-950/20 via-zinc-900/95 to-zinc-950/98";
      default: return "border-indigo-500/30 hover:border-indigo-500/60 shadow-[0_8px_30px_rgba(99,102,241,0.15)] bg-gradient-to-br from-indigo-950/20 via-zinc-900/95 to-zinc-950/98";
    }
  };

  const getActionThemeColor = () => {
    switch (type) {
      case "HUMAN_TAKEOVER": return "rose";
      case "API_CALL": return "orange";
      default: return "indigo";
    }
  };

  const getBadgeClass = (theme: string) => {
    if (theme === "rose") return "bg-rose-500/10 border-rose-500/20 text-rose-400";
    if (theme === "orange") return "bg-orange-500/10 border-orange-500/20 text-orange-400";
    return "bg-indigo-500/10 border-indigo-500/20 text-indigo-400";
  };

  const getHeaderIconBgClass = (theme: string) => {
    if (theme === "rose") return "bg-rose-500/20 border-rose-500/30 text-rose-400";
    if (theme === "orange") return "bg-orange-500/20 border-orange-500/30 text-orange-400";
    return "bg-indigo-500/20 border-indigo-500/30 text-indigo-400";
  };

  const themeColor = getActionThemeColor();

  return (
    <div className={`glass-card min-w-[280px] max-w-[340px] rounded-2xl border transition-all duration-300 relative group overflow-hidden backdrop-blur-xl ${getActionTheme()}`}>
      {/* Target Input handle */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className={`w-3 h-3 bg-${themeColor}-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform`} 
        style={{ left: "-6px" }} 
      />

      <div className={`absolute top-2 right-3 flex items-center gap-1 border text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${getBadgeClass(themeColor)}`}>
        {type === "API_CALL" ? "🔗 Webhook" : type === "CREATE_LEAD" ? "👤 CRM Stage" : type === "CALL_WORKFLOW" ? "🔄 Sub-Flujo" : "⏸ Transferir"}
      </div>

      {/* Node Header */}
      <div className={`p-3 border-b border-${themeColor}-500/10 bg-${themeColor}-500/5 flex items-center gap-2`}>
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm border ${getHeaderIconBgClass(themeColor)}`}>
          {getActionIcon()}
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">{type.replace("_", " ")}</p>
          <h4 className="text-xs font-bold text-white truncate">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2.5">
        {type === "API_CALL" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 space-y-1.5 text-[10px]">
            <div className="flex items-center gap-1.5">
              <span className="bg-orange-500/20 text-orange-300 border border-orange-500/30 px-1 py-0.5 rounded font-mono text-[8px] font-bold uppercase">
                {config.apiMethod || "POST"}
              </span>
              <span className="text-zinc-400 font-mono truncate select-all">
                {config.apiUrl || "https://api.ejemplo.com/webhook"}
              </span>
            </div>
            
            {config.saveToField && (
              <div className="border-t border-white/5 pt-1.5 flex justify-between text-zinc-500 font-mono text-[9px]">
                <span>Guarda en:</span>
                <span className="text-orange-400">{"{{" + config.saveToField + "}}"}</span>
              </div>
            )}
          </div>
        )}

        {type === "CREATE_LEAD" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 flex items-center justify-between text-[10px]">
            <span className="text-zinc-500 uppercase font-bold">Mover a etapa:</span>
            <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-full font-bold capitalize">
              {config.newLeadStage || "lead"}
            </span>
          </div>
        )}

        {type === "CALL_WORKFLOW" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 flex flex-col gap-1 text-[10px]">
            <span className="text-zinc-500 uppercase font-bold">Bot/Flujo Destino:</span>
            <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-1 rounded font-mono truncate text-[9px]">
              {config.workflowId || "No seleccionado"}
            </span>
          </div>
        )}

        {type === "HUMAN_TAKEOVER" && (
          <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-2.5 text-[10px] leading-relaxed text-rose-300">
            Pausa la automatización del bot y notifica a soporte humano.
            {config.prompt && (
              <p className="mt-1.5 text-zinc-400 italic line-clamp-2 bg-black/20 p-1.5 rounded border border-white/5">
                "{config.prompt}"
              </p>
            )}
          </div>
        )}

        {/* Transition routes if branches are configured */}
        {branches.length > 0 && (
          <div className="space-y-1.5 mt-2 pt-2 border-t border-white/5">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">Rutas (Bifurcaciones):</span>
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
          </div>
        )}
      </div>

      {/* Footer trigger */}
      <button 
        type="button" 
        onClick={(e) => { e.stopPropagation(); data.onEdit(); }}
        className="w-full text-center py-2 border-t border-white/5 hover:bg-white/5 text-[10px] text-zinc-400 font-semibold transition-all hover:text-white"
      >
        Configurar Acción
      </button>

      {/* Sequential output handle on the Right (HUMAN_TAKEOVER doesn't have one since it halts conversation) */}
      {type !== "HUMAN_TAKEOVER" && (
        <Handle 
          type="source" 
          position={Position.Right} 
          id="default" 
          className={`w-3 h-3 bg-${themeColor}-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform`} 
          style={{ right: "-6px" }} 
        />
      )}
    </div>
  );
}
