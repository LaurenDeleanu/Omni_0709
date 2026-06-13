"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Activity, Zap, Clock, Cpu, Loader2, AlertCircle,
  CheckCircle2, Sparkles, Pause, Play
} from "lucide-react";

interface ConcurrencyData {
  active_slots: number;
  max_slots: number;
  queued: number;
  status: string;
}

export function AgentConcurrencyPanel() {
  const { data, isLoading, error } = useQuery<ConcurrencyData>({
    queryKey: ["concurrency-status"],
    queryFn: () => fetchClient("/monitoring/concurrency").then(r => r),
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <Card className="glass">
        <CardHeader><Skeleton className="h-5 w-40" /></CardHeader>
        <CardContent><Skeleton className="h-20 w-full" /></CardContent>
      </Card>
    );
  }

  const pct = data?.max_slots ? Math.min((data.active_slots / data.max_slots) * 100, 100) : 0;
  const queueLength = data?.queued || 0;

  return (
    <Card className={`glass shadow-sm ${pct > 80 ? "border-amber-500/20 bg-amber-500/5" : pct > 50 ? "border-blue-500/20" : "border-border/30"}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Cpu className={`h-5 w-5 ${pct > 80 ? "text-amber-500" : "text-primary"}`} />
          Agent Runtime Status
        </CardTitle>
        <Badge className={pct > 80 ? "bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-bold" : "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold"}>
          {pct > 80 ? <AlertCircle className="w-3 h-3 mr-1" /> : <CheckCircle2 className="w-3 h-3 mr-1" />}
          {pct > 80 ? "Alta carga" : "Operativo"}
        </Badge>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-center gap-3 py-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive">Error cargando estado del runtime.</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Activity className="h-3.5 w-3.5" /> Slots de ejecución
                </span>
                <span className="font-bold">{data?.active_slots || 0} / {data?.max_slots || 10}</span>
              </div>
              <Progress value={pct} className={`h-2 ${pct > 80 ? "[&>div]:bg-amber-500" : "[&>div]:bg-primary"}`} />
              <p className="text-[10px] text-muted-foreground">
                {pct > 80 ? "Considera aumentar max_slots en configuración." : `${(data?.max_slots || 10) - (data?.active_slots || 0)} slots disponibles`}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-background/50 border border-border/30 text-center">
                <p className="text-lg font-bold flex items-center justify-center gap-1">
                  {queueLength > 0 ? <AlertCircle className="h-4 w-4 text-amber-500" /> : <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                  {queueLength}
                </p>
                <p className="text-[10px] text-muted-foreground mt-0.5">En cola</p>
              </div>
              <div className="p-3 rounded-xl bg-background/50 border border-border/30 text-center">
                <div className="flex items-center justify-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${data?.status === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
                  <p className="text-lg font-bold capitalize">{data?.status || "unknown"}</p>
                </div>
                <p className="text-[10px] text-muted-foreground mt-0.5">Estado</p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
