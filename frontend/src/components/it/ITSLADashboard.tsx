"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Clock, AlertTriangle, CheckCircle2, TrendingUp, BarChart3,
  AlertCircle, Target, Sparkles
} from "lucide-react";

interface SLAData {
  total_open: number;
  total_resolved: number;
  sla_breached: number;
  breach_pct: number;
  avg_resolution_hours: number;
  age_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  response_data: { date: string; opened: number; resolved: number }[];
}

const AGE_COLORS: Record<string, string> = {
  "<4h": "bg-emerald-500",
  "4-8h": "bg-blue-500",
  "8-24h": "bg-amber-500",
  "24-72h": "bg-orange-500",
  ">72h": "bg-rose-500",
};

const PRIORITY_BADGES: Record<string, string> = {
  critical: "bg-rose-500/10 text-rose-500 border-rose-500/20",
  high: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  medium: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  low: "bg-blue-500/10 text-blue-500 border-blue-500/20",
};

export function ITSLADashboard() {
  const { data, isLoading, error } = useQuery<SLAData>({
    queryKey: ["it-sla-summary"],
    queryFn: () => fetchClient("/it/sla/summary").then(r => r),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card className="glass border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive">Unable to load SLA data.</p>
        </CardContent>
      </Card>
    );
  }

  const maxAge = Math.max(...Object.values(data.age_distribution), 1);
  const totalPriority = Object.values(data.priority_distribution).reduce((a, b) => a + b, 0) || 1;
  const maxResponse = Math.max(...data.response_data.map(d => d.opened + d.resolved), 1);

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Tickets Abiertos</CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.total_open}</div>
            <p className="text-[10px] text-muted-foreground mt-1">Activos ahora</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Resueltos</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.total_resolved}</div>
            <p className="text-[10px] text-muted-foreground mt-1">Total acumulado</p>
          </CardContent>
        </Card>
        <Card className={`glass shadow-sm hover:shadow-md transition-shadow ${data.breach_pct > 20 ? "border-rose-500/30 bg-rose-500/5" : ""}`}>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">SLA Breached</CardTitle>
            <AlertTriangle className={`h-4 w-4 ${data.breach_pct > 20 ? "text-rose-500" : "text-amber-500"}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.sla_breached}</div>
            <div className="flex items-center gap-1.5 mt-1">
              <Progress value={data.breach_pct} className={`h-1 flex-1 ${data.breach_pct > 20 ? "[&>div]:bg-rose-500" : ""}`} />
              <span className="text-[10px] font-bold text-muted-foreground">{data.breach_pct.toFixed(0)}%</span>
            </div>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Tiempo Medio</CardTitle>
            <Target className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.avg_resolution_hours.toFixed(1)}h</div>
            <p className="text-[10px] text-muted-foreground mt-1">Resolución media</p>
          </CardContent>
        </Card>
      </div>

      {/* Age & Priority */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-500" />
              Distribución por Antigüedad
            </CardTitle>
            <CardDescription>Tickets abiertos por tiempo transcurrido</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(data.age_distribution).map(([range, count]) => (
              <div key={range} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{range}</span>
                  <span className="text-muted-foreground text-xs">{count} tickets</span>
                </div>
                <div className="flex gap-1 h-3">
                  <div
                    className={`h-full rounded-full transition-all ${AGE_COLORS[range] || "bg-slate-500"}`}
                    style={{ width: `${(count / maxAge) * 100}%`, minWidth: count > 0 ? "8px" : "0" }}
                  />
                  <span className="text-[10px] text-muted-foreground">{((count / Math.max(data.total_open, 1)) * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-rose-500" />
              Distribución por Prioridad
            </CardTitle>
            <CardDescription>Volumen de tickets por nivel de prioridad</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(data.priority_distribution).map(([priority, count]) => (
              <div key={priority} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <Badge className={`text-[10px] font-bold capitalize ${PRIORITY_BADGES[priority] || "bg-slate-500/10"}`}>
                    {priority}
                  </Badge>
                  <span className="text-muted-foreground text-xs">{count} tickets</span>
                </div>
                <div className="flex gap-1 items-center">
                  <Progress
                    value={(count / totalPriority) * 100}
                    className={`h-2 flex-1 ${
                      priority === "critical" ? "[&>div]:bg-rose-500" :
                      priority === "high" ? "[&>div]:bg-orange-500" :
                      priority === "medium" ? "[&>div]:bg-amber-500" :
                      "[&>div]:bg-blue-500"
                    }`}
                  />
                  <span className="text-[10px] text-muted-foreground w-8 text-right">{((count / totalPriority) * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* 7-Day Trend */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-indigo-500" />
            Tendencia 7 Días
          </CardTitle>
          <CardDescription>Tickets abiertos y resueltos por día</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-2 h-40">
            {data.response_data.map(day => {
              const openedHeight = (day.opened / maxResponse) * 100;
              const resolvedHeight = (day.resolved / maxResponse) * 100;
              return (
                <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex flex-col-reverse h-32">
                    <div
                      className="w-full rounded-t-sm bg-blue-500/80 transition-all hover:bg-blue-500"
                      style={{ height: `${openedHeight}%`, minHeight: day.opened > 0 ? "4px" : "0" }}
                      title={`${day.opened} abiertos`}
                    />
                    <div
                      className="w-full rounded-t-sm bg-emerald-500/80 transition-all hover:bg-emerald-500"
                      style={{ height: `${resolvedHeight}%`, minHeight: day.resolved > 0 ? "4px" : "0" }}
                      title={`${day.resolved} resueltos`}
                    />
                  </div>
                  <div className="flex gap-2 text-[10px] text-muted-foreground">
                    <span className="text-blue-500 font-bold">{day.opened}</span>
                    <span className="text-emerald-500 font-bold">{day.resolved}</span>
                  </div>
                  <span className="text-[8px] text-muted-foreground uppercase">
                    {new Date(day.date).toLocaleDateString("es-ES", { weekday: "short" }).slice(0, 3)}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex items-center justify-center gap-4 mt-3">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm bg-blue-500/80" />
              <span className="text-[10px] text-muted-foreground">Abiertos</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm bg-emerald-500/80" />
              <span className="text-[10px] text-muted-foreground">Resueltos</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
