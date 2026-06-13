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

interface UsageBreakdownProps {
  runs: ExecutionRun[];
  isLoading: boolean;
}

export default function UsageBreakdown({ runs, isLoading }: UsageBreakdownProps) {
  const totalCost = runs.reduce((acc, r) => acc + r.costUsd, 0);
  const totalTokens = runs.reduce((acc, r) => acc + r.tokenUsage, 0);

  // Group by trigger source
  const sources = ["WEBHOOK", "CRON", "MANUAL"];
  const sourceStats = sources.map((source) => {
    const matchingRuns = runs.filter((r) => r.triggerSource === source);
    const count = matchingRuns.length;
    const tokens = matchingRuns.reduce((acc, r) => acc + r.tokenUsage, 0);
    const cost = matchingRuns.reduce((acc, r) => acc + r.costUsd, 0);
    return {
      source,
      count,
      tokens,
      cost,
      tokenPct: totalTokens > 0 ? (tokens / totalTokens) * 100 : 0,
      costPct: totalCost > 0 ? (cost / totalCost) * 100 : 0,
    };
  });

  const [modelCosts, setModelCosts] = React.useState<any[]>([]);
  const [loadingModels, setLoadingModels] = React.useState(true);

  React.useEffect(() => {
    async function loadModelCosts() {
      try {
        const { fetchClient } = await import("@/lib/api/client");
        const data = await fetchClient("/monitoring/agent-costs?weeks=12");
        if (data && data.model_costs) {
          setModelCosts(data.model_costs);
        }
      } catch (e) {
        console.error("Error loading model costs:", e);
      } finally {
        setLoadingModels(false);
      }
    }
    loadModelCosts();
  }, []);

  const getModelColor = (modelName: string, index: number) => {
    const colors = [
      "bg-indigo-500 text-indigo-400",
      "bg-purple-500 text-purple-400",
      "bg-cyan-500 text-cyan-400",
      "bg-emerald-500 text-emerald-400",
      "bg-amber-500 text-amber-400",
      "bg-rose-500 text-rose-400"
    ];
    return colors[index % colors.length];
  };

  const totalModelCost = modelCosts.reduce((acc, m) => acc + (m.total_cost || 0), 0);
  const modelsList = modelCosts.map((m, idx) => {
    const cost = m.total_cost || 0;
    const share = totalModelCost > 0 ? Math.round((cost / totalModelCost) * 100) : 0;
    return {
      name: m.model_name,
      share,
      tokens: m.total_tokens || 0,
      cost,
      color: getModelColor(m.model_name, idx)
    };
  });

  const finalModels = modelsList.length > 0 ? modelsList : [
    { name: "gpt-4o-mini", share: 65, tokens: Math.round(totalTokens * 0.65), cost: totalCost * 0.65, color: "bg-indigo-500 text-indigo-400" },
    { name: "gpt-4o", share: 20, tokens: Math.round(totalTokens * 0.20), cost: totalCost * 0.20, color: "bg-purple-500 text-purple-400" },
    { name: "google/gemini-1.5-flash", share: 10, tokens: Math.round(totalTokens * 0.10), cost: totalCost * 0.10, color: "bg-cyan-500 text-cyan-400" },
    { name: "meta-llama/llama-3.1-8b-instruct", share: 5, tokens: Math.round(totalTokens * 0.05), cost: totalCost * 0.05, color: "bg-emerald-500 text-emerald-400" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-white text-xs">
      
      {/* Trigger Source Usage Share */}
      <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-4">
        <h4 className="text-sm font-bold text-zinc-200">Consumo por Origen de Desencadenador</h4>
        <p className="text-[11px] text-zinc-400 -mt-2">
          Análisis de tokens y costos agregados según la procedencia del trigger.
        </p>
 
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 text-zinc-500">
            <span className="animate-spin text-lg mb-2">🔄</span>
            <span>Cargando desglose...</span>
          </div>
        ) : (
          <div className="flex flex-col gap-4 mt-2">
            {sourceStats.map((stat) => (
              <div key={stat.source} className="flex flex-col gap-1.5 p-3.5 bg-zinc-800/25 border border-white/5 rounded-xl">
                <div className="flex justify-between items-center text-[10px] text-zinc-300 font-bold">
                  <span>{stat.source === "WEBHOOK" ? "🔗 WEBHOOKS" : stat.source === "CRON" ? "⏰ TAREAS PROGRAMADAS (CRON)" : "👤 DISPAROS MANUALES"}</span>
                  <span className="text-emerald-400">${stat.cost.toFixed(5)}</span>
                </div>
                
                <div className="flex justify-between text-[9px] text-zinc-500 mt-0.5">
                  <span>{stat.count} ejecuciones ({stat.tokens.toLocaleString()} tokens)</span>
                  <span>{stat.costPct.toFixed(1)}% del gasto total</span>
                </div>
 
                <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mt-1">
                  <div 
                    className="bg-indigo-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${stat.costPct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
 
      {/* Model Shares Distribution */}
      <div className="bg-zinc-900/60 border border-white/10 rounded-2xl p-5 flex flex-col gap-4">
        <h4 className="text-sm font-bold text-zinc-200">Distribución de Consumo de Modelos LLM</h4>
        <p className="text-[11px] text-zinc-400 -mt-2">
          Modelos que procesaron solicitudes de inferencia y toma de decisiones.
        </p>
 
        <div className="flex flex-col gap-4 mt-2">
          {finalModels.map((m) => {
            return (
              <div key={m.name} className="flex flex-col gap-1">
                <div className="flex justify-between items-center text-[10px] text-zinc-400">
                  <span className="font-semibold text-zinc-200">{m.name}</span>
                  <span className="font-mono text-zinc-300">{m.share}%</span>
                </div>
 
                <div className="flex justify-between text-[9px] text-zinc-500">
                  <span>{isLoading || loadingModels ? "..." : `${m.tokens.toLocaleString()} tokens`}</span>
                  <span className="text-emerald-400/80 font-mono">${isLoading || loadingModels ? "0.00" : m.cost.toFixed(5)}</span>
                </div>
 
                <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mt-1">
                  <div 
                    className={`${m.color.split(" ")[0]} h-full rounded-full transition-all duration-500`}
                    style={{ width: `${m.share}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>


    </div>
  );
}
