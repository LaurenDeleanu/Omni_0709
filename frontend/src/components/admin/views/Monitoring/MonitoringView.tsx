"use client";
import React, { useState, useEffect } from "react";
import MetricsDashboard from "./MetricsDashboard";
import ExecutionTimeline from "./ExecutionTimeline";
import LogsExplorer from "./LogsExplorer";
import AlertsPanel from "./AlertsPanel";
import UsageBreakdown from "./UsageBreakdown";

interface MonitoringViewProps {
  botId: string;
}

export default function MonitoringView({ botId }: MonitoringViewProps) {
  const [activeTab, setActiveTab] = useState<"metrics" | "timeline" | "logs" | "alerts" | "usage">("metrics");
  const [runs, setRuns] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchRuns = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/bots/${botId}/execution-runs?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setRuns(data.runs || []);
      }
    } catch (e) {
      console.error("Error loading execution runs:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, [botId]);

  return (
    <div className="flex flex-col h-full bg-[#0a0a0c] text-white overflow-hidden font-sans p-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-white/5 pb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">
            Monitoreo y Observabilidad
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Inspecciona las métricas de rendimiento, tokens consumidos, trazas de ejecución en tiempo real y costos.
          </p>
        </div>

        {/* Tab switch navigation */}
        <div className="flex bg-[#18181b] p-1 rounded-xl border border-white/5 self-start md:self-auto shrink-0 shadow-lg">
          <button
            onClick={() => setActiveTab("metrics")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "metrics"
                ? "bg-zinc-800 text-white shadow-md border border-white/5"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            📊 Métricas Clave
          </button>
          <button
            onClick={() => setActiveTab("timeline")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "timeline"
                ? "bg-zinc-800 text-white shadow-md border border-white/5"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            ⏱️ Trazas de Ejecución
          </button>
          <button
            onClick={() => setActiveTab("usage")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "usage"
                ? "bg-zinc-800 text-white shadow-md border border-white/5"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            💰 Consumo & Modelos
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "logs"
                ? "bg-zinc-800 text-white shadow-md border border-white/5"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            📋 Logs de Actividad
          </button>
          <button
            onClick={() => setActiveTab("alerts")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "alerts"
                ? "bg-zinc-800 text-white shadow-md border border-white/5"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            ⚠️ Alertas
          </button>
        </div>
      </div>

      {/* Main Panel Content */}
      <div className="flex-1 overflow-y-auto mt-6 pr-1 custom-scrollbar">
        {activeTab === "metrics" && <MetricsDashboard runs={runs} isLoading={isLoading} />}
        {activeTab === "timeline" && <ExecutionTimeline runs={runs} isLoading={isLoading} />}
        {activeTab === "usage" && <UsageBreakdown runs={runs} isLoading={isLoading} />}
        {activeTab === "logs" && <LogsExplorer botId={botId} />}
        {activeTab === "alerts" && <AlertsPanel />}
      </div>
    </div>
  );
}
