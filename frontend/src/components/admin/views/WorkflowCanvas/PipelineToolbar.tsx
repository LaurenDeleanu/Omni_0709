"use client";
import React from "react";
import { Bot, Play, LayoutDashboard, GitFork, RefreshCw, Layout } from "lucide-react";
import { Link } from "@/i18n/routing";

export default function PipelineToolbar({
  botId,
  viewMode,
  setViewMode,
  onAutoLayout,
  showSimulator,
  setShowSimulator,
  onAddStep
}: {
  botId: string;
  viewMode: "linear" | "canvas";
  setViewMode: (v: "linear" | "canvas") => void;
  onAutoLayout: () => void;
  showSimulator: boolean;
  setShowSimulator: (v: boolean) => void;
  onAddStep: () => void;
}) {
  return (
    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6 pb-4 border-b border-white/5">
      <div>
        <h1 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          <GitFork className="w-5 h-5 text-indigo-400 rotate-90" />
          Pipeline Builder
        </h1>
        <p className="text-xs text-zinc-500">Diseña y conecta tus flujos de conversación de forma interactiva.</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Shortcut to AI Lab (Open Question 3 Answer) */}
        <Link 
          href="/dashboard/agents"
          className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 border border-purple-500/30 text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 rounded-xl transition-all"
        >
          <Bot className="w-3.5 h-3.5 animate-pulse" />
          🤖 Ir al AI Lab
        </Link>

        {/* Auto Layout Button (Open Question 2 Answer) */}
        {viewMode === "canvas" && (
          <button
            onClick={onAutoLayout}
            title="Auto-organizar nodos del lienzo"
            className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 border border-emerald-500/30 text-emerald-300 bg-emerald-500/5 hover:bg-emerald-500/15 rounded-xl transition-all"
          >
            <Layout className="w-3.5 h-3.5" />
            Auto Organizar Lienzo
          </button>
        )}

        {/* View mode toggle */}
        <div className="flex bg-zinc-900/80 p-0.5 rounded-xl border border-white/5">
          <button 
            onClick={() => setViewMode("canvas")} 
            className={`px-3 py-1.5 text-xs rounded-lg font-bold transition-all ${
              viewMode === "canvas" 
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20" 
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Visual 2D
          </button>
          <button 
            onClick={() => setViewMode("linear")} 
            className={`px-3 py-1.5 text-xs rounded-lg font-bold transition-all ${
              viewMode === "linear" 
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20" 
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Lista Lineal
          </button>
        </div>

        {/* Simulator toggle */}
        <button 
          onClick={() => setShowSimulator(!showSimulator)}
          className={`btn-secondary text-xs px-3.5 py-1.5 flex items-center gap-1.5 rounded-xl transition-all ${
            showSimulator 
              ? "bg-indigo-500/10 border-indigo-500 text-indigo-300" 
              : "border-white/10 hover:border-white/20 text-zinc-300"
          }`}
        >
          <Play className={`w-3.5 h-3.5 ${showSimulator ? "fill-indigo-300" : ""}`} />
          {showSimulator ? "Ocultar Simulador" : "Probar Agente"}
        </button>

        {/* Add Step Action */}
        <button 
          onClick={onAddStep}
          className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 rounded-xl font-bold shadow-lg shadow-indigo-600/10 hover:scale-105 active:scale-95 transition-all"
        >
          + Añadir Paso
        </button>
      </div>
    </div>
  );
}
