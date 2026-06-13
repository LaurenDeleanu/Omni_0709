"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  CheckSquare, Clock, AlertCircle, CheckCircle2, Loader2, ChevronDown,
  ChevronRight, Calendar, User, Sparkles
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

interface ChecklistTask {
  id: string;
  checklist_id: string;
  task_name: string;
  description: string | null;
  responsible_role: string;
  sort_order: number;
  is_required: boolean;
  is_completed: boolean;
  completed_at: string | null;
  completed_by: string | null;
  notes: string | null;
}

interface ActiveChecklist {
  id: string;
  template_id: string | null;
  user_id: string;
  assigned_by: string | null;
  status: string;
  progress: number;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  tasks: ChecklistTask[];
}

export function EmployeeChecklists() {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: checklists, isLoading, error } = useQuery<ActiveChecklist[]>({
    queryKey: ["my-checklists"],
    queryFn: () => fetchClient("/checklists/my-checklists"),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ taskId, completed }: { taskId: string; completed: boolean }) =>
      fetchClient(`/checklists/checklist-tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ completed, notes: null }),
      }).then(r => r),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-checklists"] });
    },
    onError: () => toast.error("Failed to update task"),
  });

  if (isLoading) {
    return (
      <Card className="glass">
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 animate-pulse">
              <Skeleton className="h-4 w-4 rounded" />
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error || !checklists) {
    return (
      <Card className="glass border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive">Unable to load checklists.</p>
        </CardContent>
      </Card>
    );
  }

  if (checklists.length === 0) {
    return (
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <CheckSquare className="h-5 w-5 text-primary" />
            Listas de Tareas
          </CardTitle>
          <CardDescription>Checklists de onboarding y procesos</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <CheckSquare className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted-foreground">No tienes checklists activos.</p>
            <p className="text-xs text-muted-foreground">Cuando un administrador te asigne uno, aparecerá aquí.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const statusBadge = (status: string) => {
    if (status === "completed") return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold"><CheckCircle2 className="w-3 h-3 mr-1" /> Completado</Badge>;
    return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-bold"><Clock className="w-3 h-3 mr-1" /> En Progreso</Badge>;
  };

  return (
    <Card className="glass">
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <CheckSquare className="h-5 w-5 text-primary" />
          Listas de Tareas
        </CardTitle>
        <CardDescription>
          {checklists.length} checklist{checklists.length !== 1 ? "s" : ""} activo{checklists.length !== 1 ? "s" : ""}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {checklists.map((cl) => (
          <div key={cl.id} className="border border-border/60 rounded-xl overflow-hidden">
            <button
              className="w-full flex items-center justify-between p-4 hover:bg-muted/30 transition-colors text-left"
              onClick={() => setExpandedId(expandedId === cl.id ? null : cl.id)}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  {cl.status === "completed" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <Sparkles className="h-4 w-4 text-primary" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-semibold">
                    Checklist {cl.tasks?.length || 0} tareas
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    {statusBadge(cl.status)}
                    {cl.due_date && (
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {new Date(cl.due_date).toLocaleDateString("es-ES")}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Progress value={cl.progress} className="w-20 h-2" />
                <span className="text-xs font-bold text-muted-foreground">{Math.round(cl.progress)}%</span>
                {expandedId === cl.id ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </button>

            {expandedId === cl.id && (
              <div className="border-t border-border/60 p-4 space-y-2 bg-muted/20">
                {cl.tasks?.map((task) => (
                  <div
                    key={task.id}
                    className={`flex items-start gap-3 p-3 rounded-lg transition-colors ${
                      task.is_completed ? "bg-emerald-500/5" : "bg-background/50"
                    }`}
                  >
                    <Checkbox
                      checked={task.is_completed}
                      onCheckedChange={(checked) => {
                        toggleMutation.mutate({ taskId: task.id, completed: !!checked });
                      }}
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <Label
                        className={`text-sm font-medium cursor-pointer ${
                          task.is_completed ? "line-through text-muted-foreground" : ""
                        }`}
                      >
                        {task.task_name}
                      </Label>
                      {task.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">{task.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="outline" className="text-[10px] capitalize">
                        {task.responsible_role}
                      </Badge>
                      {task.is_required && (
                        <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px]">
                          Obligatorio
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
                {(!cl.tasks || cl.tasks.length === 0) && (
                  <p className="text-sm text-muted-foreground text-center py-4">No hay tareas definidas.</p>
                )}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
