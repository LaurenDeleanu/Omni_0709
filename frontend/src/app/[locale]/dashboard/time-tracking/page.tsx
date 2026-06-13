"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Clock, Play, Square, Timer, Calendar, Clock8 } from "lucide-react";
import { toast } from "sonner";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function TimeTrackingPage() {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState("");
  const [projectId, setProjectId] = useState("");

  const { data: activeSession, isLoading: sessionLoading } = useQuery({
    queryKey: ["active-session"],
    queryFn: () => fetchClient("/api/v1/time-tracking/active").then(r => r.json()),
    refetchInterval: 30000,
  });

  const { data: logs } = useQuery({
    queryKey: ["time-logs"],
    queryFn: () => fetchClient("/api/v1/time-tracking/logs?limit=20").then(r => r.json()),
  });

  const { data: summary } = useQuery({
    queryKey: ["time-summary"],
    queryFn: () => fetchClient("/api/v1/time-tracking/summary").then(r => r.json()),
  });

  const clockInMutation = useMutation({
    mutationFn: () => fetchClient("/api/v1/time-tracking/in", {
      method: "POST",
      body: JSON.stringify({ notes, project_id: projectId }),
    }).then(r => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-session"] });
      queryClient.invalidateQueries({ queryKey: ["time-logs"] });
      toast.success("Clocked in");
      setNotes("");
    },
    onError: (e: any) => toast.error(e.message || "Failed to clock in"),
  });

  const clockOutMutation = useMutation({
    mutationFn: () => fetchClient("/api/v1/time-tracking/out", { method: "POST", body: JSON.stringify({ notes: "" }) }).then(r => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-session"] });
      queryClient.invalidateQueries({ queryKey: ["time-logs"] });
      toast.success("Clocked out");
    },
    onError: (e: any) => toast.error(e.message || "Failed to clock out"),
  });

  const isActive = activeSession?.active && activeSession?.session;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Control horario</h1>
        <p className="text-muted-foreground">Clock in/out and track your working hours</p>
      </div>

      <InlineCopilot
        moduleContext="time-tracking"
        placeholder="Ask about your hours or work patterns..."
        quickActions={[
          { label: "Summarize my week", message: "Summarize my week" },
          { label: "Show overtime hours", message: "Show overtime hours" },
          { label: "Analyze my work patterns", message: "Analyze my work patterns" },
        ]}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card className={isActive ? "border-green-500" : ""}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">{isActive ? "En curso" : "No activo"}</CardTitle>
            <Timer className={`h-4 w-4 ${isActive ? "text-green-500 animate-pulse" : "text-muted-foreground"}`} />
          </CardHeader>
          <CardContent>
            {isActive ? (
              <div className="space-y-2">
                <div className="text-lg font-bold text-green-600">
                  {activeSession.session?.elapsed_hours?.toFixed(1)}h
                </div>
                <Button variant="destructive" size="sm" className="w-full gap-2" onClick={() => clockOutMutation.mutate()} disabled={clockOutMutation.isPending}>
                  <Square className="h-4 w-4" /> Clock Out
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <Input placeholder="Notas (opcional)" value={notes} onChange={e => setNotes(e.target.value)} />
                <Input placeholder="Proyecto (opcional)" value={projectId} onChange={e => setProjectId(e.target.value)} />
                <Button className="w-full gap-2" onClick={() => clockInMutation.mutate()} disabled={clockInMutation.isPending}>
                  <Play className="h-4 w-4" /> {clockInMutation.isPending ? "Clocking in..." : "Clock In"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Hoy</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_hours?.toFixed(1) ?? "—"}h</div>
            <p className="text-xs text-muted-foreground">{summary?.total_entries ?? 0} registros</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Registros</CardTitle>
            <Clock8 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{logs?.count ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Últimos registros</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {logs?.logs?.slice(0, 10).map((log: any) => (
              <div key={log.id} className="flex items-center justify-between border-b pb-2 text-sm">
                <div>
                  <Clock className="h-4 w-4 inline mr-2 text-muted-foreground" />
                  {new Date(log.clock_in).toLocaleDateString()}
                </div>
                <div className="flex gap-4">
                  <span>{new Date(log.clock_in).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  <span className="text-muted-foreground">→</span>
                  <span>{log.clock_out ? new Date(log.clock_out).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "..."}</span>
                </div>
                {log.project_id && <Badge variant="outline">{log.project_id}</Badge>}
              </div>
            ))}
            {(!logs?.logs || logs.logs.length === 0) && (
              <p className="text-sm text-muted-foreground text-center py-4">No hay registros aún</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
