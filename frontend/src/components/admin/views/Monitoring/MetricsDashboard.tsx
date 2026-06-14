"use client";
import React from "react";

interface ExecutionRun {
  id: string;
  triggerSource: string;
  status: string;
  inputPayload: string;
  outputResult: string | null;
  loopCount: number;
  tokenUsage: number;
  costUsd: number;
  latencyMs: number;
  createdAt: string;
}

interface MetricsDashboardProps {
  runs: ExecutionRun[];
  isLoading: boolean;
}

export default function MetricsDashboard({ runs, isLoading }: MetricsDashboardProps) {
  // Calculate stats from runs list
  const totalRuns = runs.length;
  const successRuns = runs.filter((r) => r.status === "success").length;
  const successRate = totalRuns > 0 ? (successRuns / totalRuns) * 100 : 0;
  
  const avgLatency = totalRuns > 0
    ? Math.round(runs.reduce((acc, r) => acc + r.latencyMs, 0) / totalRuns)
    : 0;

  const totalTokens = runs.reduce((acc, r) => acc + r.tokenUsage, 0);
  const totalCost = runs.reduce((acc, r) => acc + r.costUsd, 0);

  // Trigger breakdown
  const webhookCount = runs.filter((r) => r.triggerSource === "WEBHOOK").length;
  const cronCount = runs.filter((r) => r.triggerSource === "CRON").length;
  const manualCount = runs.filter((r) => r.triggerSource === "MANUAL").length;

  return (
    <div className="flex flex-col gap-6 text-white text-xs">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Success Rate */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-emerald-400 text-lg opacity-40">📈</div>
          <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Tasa de Éxito</span>
          <span className="text-2xl font-black text-emerald-400 mt-1">
            {isLoading ? "..." : `${successRate.toFixed(1)}%`}
          </span>
          <span className="text-[10px] text-zinc-500 mt-1">
            {isLoading ? "Calculando..." : `${successRuns} de ${totalRuns} ejecuciones completadas`}
          </span>
        </div>

        {/* Avg Latency */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-blue-400 text-lg opacity-40">⚡</div>
          <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Latencia Promedio</span>
          <span className="text-2xl font-black text-blue-400 mt-1">
            {isLoading ? "..." : `${(avgLatency / 1000).toFixed(2)}s`}
          </span>
          <span className="text-[10px] text-zinc-500 mt-1">
            {isLoading ? "Calculando..." : `${avgLatency} ms promedio de respuesta`}
          </span>
        </div>

        {/* Token Usage */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-purple-400 text-lg opacity-40">🤖</div>
          <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Consumo de Tokens</span>
          <span className="text-2xl font-black text-purple-400 mt-1">
            {isLoading ? "..." : totalTokens.toLocaleString()}
          </span>
          <span className="text-[10px] text-zinc-500 mt-1">
            {isLoading ? "Calculando..." : "Prompt y completion tokens combinados"}
          </span>
        </div>

        {/* Total Cost */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-cyan-400 text-lg opacity-40">💰</div>
          <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Costo Acumulado</span>
          <span className="text-2xl font-black text-cyan-400 mt-1">
            {isLoading ? "..." : `$${totalCost.toFixed(4)}`}
          </span>
          <span className="text-[10px] text-zinc-500 mt-1">
            {isLoading ? "Calculando..." : "Basado en tokens consumidos por modelo"}
          </span>
        </div>
      </div>

      {/* Execution Distribution & Spark charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Source Breakdown */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-4">
          <h4 className="text-sm font-bold text-zinc-200">Orígenes de Desencadenadores</h4>
          
          <div className="flex flex-col gap-3.5 mt-2">
            {/* Webhook bar */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-[10px] text-zinc-400">
                <span className="font-semibold text-zinc-300">🔗 Webhooks Externos</span>
                <span>{webhookCount} ejecuciones</span>
              </div>
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-indigo-500 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${totalRuns > 0 ? (webhookCount / totalRuns) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* Cron bar */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-[10px] text-zinc-400">
                <span className="font-semibold text-zinc-300">⏰ Tareas Cron (Programadas)</span>
                <span>{cronCount} ejecuciones</span>
              </div>
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-cyan-500 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${totalRuns > 0 ? (cronCount / totalRuns) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* Manual bar */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-[10px] text-zinc-400">
                <span className="font-semibold text-zinc-300">👤 Disparos Manuales</span>
                <span>{manualCount} ejecuciones</span>
              </div>
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-amber-500 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${totalRuns > 0 ? (manualCount / totalRuns) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Quality metrics */}
        <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-4">
          <h4 className="text-sm font-bold text-zinc-200">Rendimiento Operativo</h4>
          
          <div className="grid grid-cols-2 gap-4 mt-2">
            <div className="p-3 bg-zinc-800/40 border border-white/5 rounded-xl text-center flex flex-col gap-1">
              <span className="text-[10px] text-zinc-400">Promedio de Loops</span>
              <span className="text-lg font-bold text-zinc-200">
                {isLoading ? "..." : (runs.reduce((acc, r) => acc + r.loopCount, 0) / (totalRuns || 1)).toFixed(1)}
              </span>
              <span className="text-[8px] text-zinc-500">Pasos por ejecución</span>
            </div>

            <div className="p-3 bg-zinc-800/40 border border-white/5 rounded-xl text-center flex flex-col gap-1">
              <span className="text-[10px] text-zinc-400">Costo promedio</span>
              <span className="text-lg font-bold text-emerald-400">
                {isLoading ? "..." : `$${(totalCost / (totalRuns || 1)).toFixed(4)}`}
              </span>
              <span className="text-[8px] text-zinc-500">Por ejecución</span>
            </div>
          </div>

          <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-xl p-3 flex gap-2.5 items-start mt-2">
            <span className="text-sm">⚠️</span>
            <div className="flex flex-col gap-0.5 text-[10px] leading-relaxed">
              <span className="font-bold">Nota de consumo empresarial</span>
              <span>
                El consumo acumulado actual se descuenta de tu cuota de suscripción. Puedes configurar límites de fallas y alertas en el panel de Alertas.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
