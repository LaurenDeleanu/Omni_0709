"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Activity, Server, TrendingUp, Clock, Zap, DollarSign,
  CheckCircle2, XCircle, AlertTriangle, Loader2, Sparkles,
  Download, RefreshCw
} from "lucide-react";

interface AgentRun {
  id: string;
  agent_id: string;
  status: string;
  cost_usd: number | null;
  latency_ms: number | null;
  token_usage: number | null;
  trigger_source: string;
  created_at: string;
}

interface AgentMetrics {
  total_runs: number;
  success_count: number;
  total_cost_usd: number;
  total_tokens: number;
  avg_latency_ms: number;
  recent_runs: AgentRun[];
  provider_health: Record<string, string>;
  cache_stats: { hits: number; misses: number; hit_rate: number } | null;
  concurrency: { active_slots: number; max_slots: number; queued: number } | null;
}

export function AgentHealthDashboard() {
  const { data: metrics, isLoading, error } = useQuery<AgentMetrics>({
    queryKey: ["agent-monitoring-metrics"],
    queryFn: () => fetchClient("/monitoring/metrics").then(r => r),
    refetchInterval: 15000,
  });

  const { data: providers } = useQuery<Record<string, string>>({
    queryKey: ["provider-health"],
    queryFn: () => fetchClient("/monitoring/provider-health").then(r => r),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <Card className="glass border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertTriangle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive">Unable to load agent metrics.</p>
        </CardContent>
      </Card>
    );
  }

  const successRate = metrics.total_runs > 0 ? ((metrics.success_count / metrics.total_runs) * 100).toFixed(1) : "0";
  const cacheHitRate = metrics.cache_stats ? (metrics.cache_stats.hit_rate * 100).toFixed(1) : "0";
  const concurrencyPct = metrics.concurrency ? Math.min((metrics.concurrency.active_slots / metrics.concurrency.max_slots) * 100, 100) : 0;

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Ejecuciones</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total_runs.toLocaleString()}</div>
            <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" /> {metrics.success_count} exitosas
            </p>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Tasa de Éxito</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{successRate}%</div>
            <Progress value={parseFloat(successRate)} className="h-1.5 mt-2" />
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Coste Total</CardTitle>
            <DollarSign className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(metrics.total_cost_usd || 0).toFixed(2)}</div>
            <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
              <Zap className="h-3 w-3 text-blue-500" /> {(metrics.total_tokens || 0).toLocaleString()} tokens
            </p>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Latencia Media</CardTitle>
            <Clock className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(metrics.avg_latency_ms || 0).toFixed(0)}ms</div>
            <p className="text-[10px] text-muted-foreground mt-1">Por ejecución</p>
          </CardContent>
        </Card>
      </div>

      {/* Provider Health + Concurrency */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="glass md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" />
              Salud de Proveedores LLM
            </CardTitle>
            <CardDescription>Estado de los 6 proveedores de IA</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-3">
              {(providers || metrics?.provider_health) && Object.entries(providers || metrics?.provider_health || {}).map(([name, status]) => {
                const isHealthy = status === "healthy" || status === "ok";
                const providerNames: Record<string, string> = {
                  openai: "OpenAI", gemini: "Google Gemini", anthropic: "Anthropic",
                  openrouter: "OpenRouter", groq: "Groq", grok: "Grok (xAI)",
                };
                return (
                  <div key={name} className={`p-3 rounded-xl border ${isHealthy ? "border-emerald-500/30 bg-emerald-500/5" : "border-rose-500/30 bg-rose-500/5"}`}>
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-bold">{providerNames[name] || name}</p>
                      <div className={`w-2 h-2 rounded-full ${isHealthy ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
                    </div>
                    <Badge className={isHealthy ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px]" : "bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px]"}>
                      {isHealthy ? <CheckCircle2 className="w-3 h-3 mr-1" /> : <XCircle className="w-3 h-3 mr-1" />}
                      {isHealthy ? "Operativo" : "Degradado"}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Activity className="h-5 w-5 text-amber-500" />
              Concurrencia
            </CardTitle>
            <CardDescription>Slots activos de agentes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {metrics.concurrency ? (
              <>
                <div className="space-y-1.5">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Activos</span>
                    <span className="font-bold">{metrics.concurrency.active_slots} / {metrics.concurrency.max_slots}</span>
                  </div>
                  <Progress value={concurrencyPct} className="h-2" />
                </div>
                <div className="p-3 rounded-lg bg-background/50 border border-border/30">
                  <p className="text-sm font-semibold">{metrics.concurrency.queued}</p>
                  <p className="text-xs text-muted-foreground">En cola</p>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">Sin datos de concurrencia</p>
            )}

            <div className="space-y-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Cache LLM</p>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Hit Rate</span>
                <span className="font-bold">{cacheHitRate}%</span>
              </div>
              <Progress value={parseFloat(cacheHitRate)} className="h-1.5" />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>{metrics.cache_stats?.hits || 0} hits</span>
                <span>{metrics.cache_stats?.misses || 0} misses</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Runs Table */}
      <Card className="glass">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Ejecuciones Recientes
            </CardTitle>
            <CardDescription>Últimas 15 ejecuciones de agentes</CardDescription>
          </div>
          <Button variant="outline" size="xs" className="gap-1.5">
            <Download className="h-3.5 w-3.5" /> Exportar CSV
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/40 text-left">
                  <th className="py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Agente</th>
                  <th className="py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Estado</th>
                  <th className="py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Coste</th>
                  <th className="py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Latencia</th>
                  <th className="py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Origen</th>
                  <th className="py-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {metrics.recent_runs?.map((run: AgentRun) => (
                  <tr key={run.id} className="border-b border-border/20 hover:bg-muted/10 transition-colors">
                    <td className="py-2 px-3 font-medium text-xs">{run.agent_id.slice(0, 12)}...</td>
                    <td className="py-2 px-3">
                      <Badge className={run.status === "success"
                        ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px]"
                        : run.status === "failed"
                        ? "bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px]"
                        : "bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px]"
                      }>
                        {run.status === "success" ? <CheckCircle2 className="w-2.5 h-2.5 mr-1" /> : run.status === "failed" ? <XCircle className="w-2.5 h-2.5 mr-1" /> : <Loader2 className="w-2.5 h-2.5 mr-1 animate-spin" />}
                        {run.status}
                      </Badge>
                    </td>
                    <td className="py-2 px-3 text-xs">${(run.cost_usd || 0).toFixed(4)}</td>
                    <td className="py-2 px-3 text-xs">{run.latency_ms || 0}ms</td>
                    <td className="py-2 px-3 text-xs capitalize">{run.trigger_source || "api"}</td>
                    <td className="py-2 px-3 text-xs text-muted-foreground">
                      {run.created_at ? new Date(run.created_at).toLocaleTimeString("es-ES") : "—"}
                    </td>
                  </tr>
                ))}
                {(!metrics.recent_runs || metrics.recent_runs.length === 0) && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-muted-foreground">
                      No hay ejecuciones recientes.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
