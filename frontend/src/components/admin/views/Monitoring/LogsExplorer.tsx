"use client";
import React, { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";

interface LogEntry {
  id: string;
  action: string;
  details: string;
  userId: string | null;
  createdAt: string;
}

interface LogsExplorerProps {
  botId: string;
}

export default function LogsExplorer({ botId }: LogsExplorerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const data = await fetchClient(`/agents/${botId}/execution-runs?limit=150`);
      setLogs(data.runs || []);
    } catch (e) {
      console.error("Error loading explorer logs:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [botId]);

  useEffect(() => {
    let filtered = logs;

    if (search) {
      filtered = filtered.filter(
        (l) =>
          l.action.toLowerCase().includes(search.toLowerCase()) ||
          l.details.toLowerCase().includes(search.toLowerCase())
      );
    }

    if (categoryFilter !== "all") {
      filtered = filtered.filter((l) => {
        if (categoryFilter === "agent") return l.action.startsWith("agent.") || l.action.includes("message");
        if (categoryFilter === "bot") return l.action.startsWith("bot.") || l.action.startsWith("step.");
        if (categoryFilter === "integration") return l.action.startsWith("integration.") || l.action.startsWith("custom_");
        if (categoryFilter === "client") return l.action.startsWith("client.");
        return true;
      });
    }

    setFilteredLogs(filtered);
  }, [search, categoryFilter, logs]);

  const getLogBadge = (action: string) => {
    if (action.startsWith("bot.")) return "bg-blue-500/10 text-blue-400 border border-blue-500/25";
    if (action.startsWith("step.")) return "bg-purple-500/10 text-purple-400 border border-purple-500/25";
    if (action.startsWith("integration.") || action.startsWith("custom_")) return "bg-cyan-500/10 text-cyan-400 border border-cyan-500/25";
    if (action.startsWith("client.")) return "bg-amber-500/10 text-amber-400 border border-amber-500/25";
    return "bg-zinc-800 text-zinc-400 border border-zinc-700/50";
  };

  const formatDetails = (detailsStr: string) => {
    try {
      const parsed = JSON.parse(detailsStr);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return detailsStr;
    }
  };

  return (
    <div className="flex flex-col bg-zinc-900/60 border border-white/10 rounded-2xl overflow-hidden text-white text-xs">
      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 border-b border-white/5 bg-zinc-900/40">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-sm text-zinc-200">Explorador de Actividades</h3>
          <span className="bg-zinc-800 text-zinc-400 text-[10px] px-2 py-0.5 rounded-full font-mono">
            {filteredLogs.length} logs
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Buscar en logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-[#18181b] border border-white/5 rounded-xl px-3 py-1.5 focus:outline-none focus:border-indigo-500 text-xs w-44 transition-colors"
          />

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-[#18181b] border border-white/5 rounded-xl px-2.5 py-1.5 focus:outline-none text-xs text-zinc-300"
          >
            <option value="all">Todas las Categorías</option>
            <option value="bot">Plataforma / Bot</option>
            <option value="agent">Agente IA / Mensajes</option>
            <option value="integration">Integraciones & APIs</option>
            <option value="client">CRM & Clientes</option>
          </select>

          <button
            onClick={fetchLogs}
            disabled={isLoading}
            className="p-1.5 bg-[#18181b] hover:bg-zinc-800 rounded-xl border border-white/5 hover:border-white/10 transition-colors disabled:opacity-50"
            title="Refrescar logs"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Logs output console */}
      <div className="flex-1 overflow-y-auto max-h-[500px] p-5 flex flex-col gap-2 custom-scrollbar">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
            <span className="animate-spin text-xl mb-2">🔄</span>
            <span>Cargando logs...</span>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-20 text-zinc-500">
            No se encontraron logs de actividad que coincidan.
          </div>
        ) : (
          <div className="flex flex-col gap-2 font-mono">
            {filteredLogs.map((log) => {
              const isExpanded = expandedLogId === log.id;
              return (
                <div
                  key={log.id}
                  className={`border border-white/5 hover:border-white/10 rounded-xl overflow-hidden transition-all ${
                    isExpanded ? "bg-[#18181b]" : "bg-black/20 hover:bg-black/30"
                  }`}
                >
                  <div
                    onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                    className="flex items-center justify-between p-3 cursor-pointer text-[11px]"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded font-sans uppercase shrink-0 ${getLogBadge(log.action)}`}>
                        {log.action}
                      </span>
                      <span className="text-zinc-300 truncate">{log.details.slice(0, 80)}...</span>
                    </div>

                    <div className="flex items-center gap-4 shrink-0 font-mono text-[9px] text-zinc-500">
                      <span>{new Date(log.createdAt).toLocaleTimeString()}</span>
                      <span>{isExpanded ? "▲" : "▼"}</span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-4 pb-4 pt-3 border-t border-white/5 bg-[#0d0d0f] text-[10px]">
                      <div className="flex flex-col gap-2">
                        <span className="font-bold text-zinc-500 uppercase tracking-wider text-[9px]">Payload de Datos (detalles):</span>
                        <pre className="p-3 bg-black/40 rounded-lg text-zinc-300 overflow-x-auto leading-relaxed custom-scrollbar max-h-60">
                          {formatDetails(log.details)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
