"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Activity, Heart, Cpu, Zap, Clock, CheckCircle2, AlertTriangle, Loader2,
  Sparkles, Wrench, Server, RefreshCw
} from "lucide-react";

interface RuntimeStats {
  runtime_stats?: {
    healthy_agents?: number;
    total_agents?: number;
    active_executions?: number;
    completed_executions?: number;
    failed_executions?: number;
    avg_response_ms?: number;
    uptime_seconds?: number;
  };
  active_tasks?: number;
  completed_tasks?: number;
  supervised_agents?: string[];
}

export function AgentRuntimeLive() {
  const { data, isLoading, error } = useQuery<RuntimeStats>({
    queryKey: ["agent-runtime-stats"],
    queryFn: () => fetchClient("/agents/runtime-stats").then(r => r),
    refetchInterval: 8000,
  });

  const stats = data?.runtime_stats || {};

  if (isLoading) {
    return (
      <Card className="glass">
        <CardHeader><Skeleton className="h-5 w-40" /></CardHeader>
        <CardContent><Skeleton className="h-24 w-full" /></CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="glass border-amber-500/20 bg-amber-500/5">
        <CardHeader>
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Activity className="h-5 w-5 text-amber-500" />
            Agent Runtime
          </CardTitle>
          <CardDescription>Métricas no disponibles — el runtime puede estar en modo de desarrollo</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const healthyAgents = stats.healthy_agents || 0;
  const totalAgents = stats.total_agents || 0;
  const healthPct = totalAgents > 0 ? Math.round((healthyAgents / totalAgents) * 100) : 100;
  const activeExecs = stats.active_executions || 0;
  const failedExecs = stats.failed_executions || 0;
  const avgMs = stats.avg_response_ms || 0;
  const uptime = stats.uptime_seconds ? `${Math.floor(stats.uptime_seconds / 3600)}h ${Math.floor((stats.uptime_seconds % 3600) / 60)}m` : "—";

  return (
    <Card className={`glass shadow-sm ${healthPct < 80 ? "border-rose-500/20 bg-rose-500/5" : healthPct < 95 ? "border-amber-500/20 bg-amber-500/5" : "border-border/30"}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Heart className={`h-5 w-5 ${healthPct >= 95 ? "text-emerald-500" : "text-rose-500"}`} />
            Agent Runtime Status
          </CardTitle>
          <CardDescription>
            {healthPct >= 95 ? "Todos los agentes operativos" : healthPct >= 80 ? "Algunos agentes requieren atención" : "Varios agentes con problemas"}
            {uptime !== "—" && ` · Uptime: ${uptime}`}
          </CardDescription>
        </div>
        <Badge className={healthPct >= 95 ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-rose-500/10 text-rose-500 border-rose-500/20"}>
          {healthPct >= 95 ? <CheckCircle2 className="w-3 h-3 mr-1" /> : <AlertTriangle className="w-3 h-3 mr-1" />}
          {healthyAgents}/{totalAgents} healthy
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-3 mb-4">
          {[
            { label: "Ejecuciones activas", value: activeExecs, icon: Zap, color: "text-blue-500" },
            { label: "Fallos", value: failedExecs, icon: AlertTriangle, color: failedExecs > 0 ? "text-rose-500" : "text-muted-foreground" },
            { label: "Respuesta media", value: `${avgMs}ms`, icon: Clock, color: "text-indigo-500" },
            { label: "Completadas", value: stats.completed_executions || 0, icon: CheckCircle2, color: "text-emerald-500" },
          ].map(kpi => (
            <div key={kpi.label} className="p-3 rounded-xl bg-background/50 border border-border/30 text-center">
              <kpi.icon className={`h-4 w-4 mx-auto mb-1 ${kpi.color}`} />
              <p className="text-lg font-extrabold">{kpi.value}</p>
              <p className="text-[9px] text-muted-foreground">{kpi.label}</p>
            </div>
          ))}
        </div>

        {data?.supervised_agents && data.supervised_agents.length > 0 && (
          <div className="p-3 rounded-xl bg-muted/10 border border-border/30">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
              <Wrench className="h-3 w-3" /> Agentes Supervisados ({data.supervised_agents.length})
            </p>
            <div className="flex flex-wrap gap-1">
              {data.supervised_agents.map(name => (
                <Badge key={name} variant="outline" className="text-[10px]">{name}</Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
