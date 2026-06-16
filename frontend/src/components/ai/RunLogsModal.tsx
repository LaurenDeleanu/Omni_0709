import React from "react";
import { Terminal, Copy, Check, X, Clock } from "lucide-react";
import { Message, RunLog } from "./types";

interface LogsModalProps {
  msg: Message;
  onClose: () => void;
  onCopy: (log: RunLog) => void;
  copiedField: string | null;
}

export function RunLogsModal({ msg, onClose, onCopy, copiedField }: LogsModalProps) {
  const log = msg.runLog!;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-950 border border-cyan-500/20 rounded-2xl w-[520px] max-h-[80vh] overflow-hidden flex flex-col shadow-[0_0_40px_rgba(6,182,212,0.15)]">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-slate-900/50">
          <div className="flex items-center gap-2">
            <Terminal size={14} className="text-cyan-400" />
            <span className="text-xs font-bold text-zinc-200 uppercase tracking-wider">Execution Logs</span>
            <span className="text-[9px] text-zinc-600 font-mono">{log.runId.slice(0, 16)}...</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onCopy(log)}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-cyan-400 hover:bg-cyan-500/10 transition-all"
              title="Copiar logs"
            >
              {copiedField === log.runId ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-white/10 transition-all"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        <div className="p-4 space-y-3 overflow-y-auto custom-scrollbar bg-slate-950/50">
          {/* Metrics */}
          <div className="grid grid-cols-2 gap-2">
            <LogMetric label="Status" value={log.status} color={log.status === "completed" ? "text-emerald-400" : log.status === "failed" ? "text-red-400" : "text-amber-400"} />
            <LogMetric label="Latency" value={`${log.latencyMs}ms`} />
            <LogMetric label="Tokens" value={log.tokenUsage.toLocaleString()} />
            <LogMetric label="Cost" value={`$${log.costUsd.toFixed(6)}`} />
            {log.model && <LogMetric label="Model" value={log.model} mono />}
          </div>

          {/* Traces */}
          {log.trace && log.trace.length > 0 && (
            <div>
              <div className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Traces ({log.trace.length} steps)</div>
              <div className="space-y-1.5 max-h-[200px] overflow-y-auto custom-scrollbar bg-slate-900/50 rounded-lg p-2.5 border border-zinc-800">
                {log.trace.map((step, sIdx) => (
                  <div key={sIdx} className="flex gap-2 text-[10px]">
                    <span className="text-violet-400 font-mono shrink-0">[{step.step}]</span>
                    <span className="text-cyan-400 font-semibold shrink-0">{step.tool}</span>
                    <span className="text-zinc-500 truncate">&mdash; &ldquo;{step.thought}&rdquo;</span>
                    {step.latencyMs && <span className="text-zinc-600 ml-auto shrink-0">{step.latencyMs}ms</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tool Calls */}
          {log.toolTrace && log.toolTrace.length > 0 && (
            <div>
              <div className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Tool Calls ({log.toolTrace.length})</div>
              <div className="space-y-1.5 max-h-[200px] overflow-y-auto custom-scrollbar bg-slate-900/50 rounded-lg p-2.5 border border-zinc-800">
                {log.toolTrace.map((step, sIdx) => (
                  <div key={sIdx} className="text-[10px]">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${step.status === "completed" ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
                      <span className="text-indigo-400 font-semibold">{step.tool}</span>
                      <span className="text-zinc-600 text-[9px] ml-auto">{step.status}</span>
                    </div>
                    {step.args && Object.keys(step.args).length > 0 && (
                      <div className="mt-0.5 pl-4 text-zinc-500 font-mono text-[9px] break-all">
                        args: {JSON.stringify(step.args)}
                      </div>
                    )}
                    {step.result && (
                      <div className="mt-0.5 pl-4 text-zinc-400 font-mono text-[9px] break-all max-h-[60px] overflow-y-auto">
                        &rarr; {step.result}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Run ID footer */}
          <div className="pt-2 border-t border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[9px] text-zinc-600 font-mono">
              <span className="text-zinc-700">ID:</span>
              <span className="text-zinc-500">{log.runId}</span>
            </div>
            <div className="flex items-center gap-1 text-[9px] text-zinc-600">
              <Clock size={10} />
              <span>{log.latencyMs}ms</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LogMetric({ label, value, color = "text-zinc-300", mono }: { label: string; value: string; color?: string; mono?: boolean }) {
  return (
    <div className="bg-slate-900/80 border border-zinc-800 rounded-lg p-2">
      <div className="text-[8px] uppercase tracking-wider text-zinc-600 mb-0.5">{label}</div>
      <div className={`text-xs font-semibold ${color} ${mono ? "font-mono text-[11px]" : ""}`}>{value}</div>
    </div>
  );
}
