"use client";
import React, { useState } from "react";

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
  executionTrace: string;
  createdAt: string;
}

interface ExecutionTimelineProps {
  runs: ExecutionRun[];
  isLoading: boolean;
}

export default function ExecutionTimeline({ runs, isLoading }: ExecutionTimelineProps) {
  const [selectedRun, setSelectedRun] = useState<ExecutionRun | null>(null);

  const getStatusBadge = (status: string) => {
    if (status === "SUCCESS") {
      return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25";
    }
    return "bg-red-500/10 text-red-400 border border-red-500/25";
  };

  const getTriggerIcon = (source: string) => {
    if (source === "WEBHOOK") return "🔗 Webhook";
    if (source === "CRON") return "⏰ Cron";
    return "👤 Manual";
  };

  const formatJson = (str: string | null) => {
    if (!str) return "{}";
    try {
      return JSON.stringify(JSON.parse(str), null, 2);
    } catch {
      return str;
    }
  };

  const parseTrace = (traceStr: string) => {
    try {
      return JSON.parse(traceStr) || [];
    } catch {
      return [];
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 text-white text-xs">
      {/* Left List of Runs */}
      <div className="lg:col-span-2 flex flex-col bg-zinc-900/60 border border-white/10 rounded-2xl p-5 overflow-hidden">
        <h3 className="text-sm font-bold mb-4 flex items-center justify-between">
          <span>Ejecuciones del Agente</span>
          <span className="text-[10px] text-zinc-400 font-medium">Últimas 50 ejecuciones</span>
        </h3>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
            <span className="animate-spin text-xl mb-2">🔄</span>
            <span>Cargando ejecuciones...</span>
          </div>
        ) : runs.length === 0 ? (
          <div className="text-center py-20 text-zinc-500">
            No se han registrado ejecuciones de este Agente.
          </div>
        ) : (
          <div className="flex flex-col gap-2 max-h-[550px] overflow-y-auto pr-1 custom-scrollbar">
            {runs.map((run) => (
              <div
                key={run.id}
                onClick={() => setSelectedRun(run)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                  selectedRun?.id === run.id
                    ? "bg-zinc-800 border-indigo-500/40 shadow-md shadow-indigo-500/5"
                    : "bg-[#18181b]/40 border-white/5 hover:border-white/10 hover:bg-[#18181b]/80"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${getStatusBadge(run.status)}`}>
                    {run.status}
                  </span>
                  <div className="flex flex-col">
                    <span className="font-mono text-zinc-300 font-bold">{run.id}</span>
                    <span className="text-[10px] text-zinc-500 mt-0.5">
                      {getTriggerIcon(run.triggerSource)} • {new Date(run.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-6 text-[11px] font-mono text-zinc-400">
                  <div className="flex flex-col text-right">
                    <span className="text-zinc-300">{run.latencyMs} ms</span>
                    <span className="text-[9px] text-zinc-500">Latencia</span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-zinc-300">{run.tokenUsage}</span>
                    <span className="text-[9px] text-zinc-500">Tokens</span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-emerald-400 font-bold">${run.costUsd.toFixed(5)}</span>
                    <span className="text-[9px] text-zinc-500">Costo</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right Details Panel */}
      <div className="flex flex-col bg-zinc-900/60 border border-white/10 rounded-2xl p-5 min-h-[400px]">
        {selectedRun ? (
          <div className="flex flex-col gap-4 h-full">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <div>
                <h4 className="font-bold text-sm text-zinc-200">Detalles de Ejecución</h4>
                <p className="text-[10px] text-zinc-500 mt-0.5 font-mono">{selectedRun.id}</p>
              </div>
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${getStatusBadge(selectedRun.status)}`}>
                {selectedRun.status}
              </span>
            </div>

            {/* Steps Trace Timeline */}
            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Línea de Tiempo del Trace:</span>
              <div className="flex flex-col gap-3 pl-3 border-l border-white/10 mt-1.5 ml-2.5">
                {parseTrace(selectedRun.executionTrace).map((step: any, idx: number) => (
                  <div key={idx} className="relative flex flex-col gap-0.5">
                    {/* Circle dot marker */}
                    <div className={`absolute -left-[17px] top-1 w-2.5 h-2.5 rounded-full border bg-zinc-950 ${
                      step.status === "failed" ? "border-red-500" : "border-emerald-500"
                    }`} />
                    <span className="font-bold text-zinc-200 text-xs">{step.step}</span>
                    {step.info && <span className="text-zinc-500 text-[10px] leading-relaxed">{step.info}</span>}
                    {step.error && <span className="text-red-400 text-[10px] leading-relaxed font-mono mt-0.5 bg-red-950/20 p-1.5 rounded border border-red-500/20">{step.error}</span>}
                    <span className="text-[9px] text-zinc-500 mt-0.5 font-mono">
                      {new Date(step.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Input Payload */}
            <div className="flex flex-col gap-1 border-t border-white/5 pt-3 mt-2">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Carga Útil de Entrada (Input):</span>
              <pre className="p-3 bg-black/40 rounded-lg text-[10px] font-mono text-zinc-300 overflow-x-auto max-h-40 leading-relaxed custom-scrollbar">
                {formatJson(selectedRun.inputPayload)}
              </pre>
            </div>

            {/* Output Result */}
            <div className="flex flex-col gap-1 border-t border-white/5 pt-3">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Resultado de Salida (Output):</span>
              <pre className="p-3 bg-black/40 rounded-lg text-[10px] font-mono text-zinc-300 overflow-x-auto max-h-40 leading-relaxed custom-scrollbar">
                {formatJson(selectedRun.outputResult)}
              </pre>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center flex-1 text-zinc-500 text-center py-20">
            <span className="text-3xl mb-3">🔍</span>
            <span className="font-medium text-xs">Selecciona una ejecución para inspeccionar el trace</span>
            <p className="text-[10px] text-zinc-600 max-w-xs mt-1">
              Podrás ver el flujo de decisiones paso a paso, los datos de entrada/salida y los logs de herramientas.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
