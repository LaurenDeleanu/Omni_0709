"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Target, Users, Star, Loader2, Plus, Eye } from "lucide-react";
import { toast } from "sonner";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function ReviewsPage() {
  const queryClient = useQueryClient();
  const [selectedCycle, setSelectedCycle] = useState<string>("");

  const { data: cycles, isLoading: cyclesLoading } = useQuery({
    queryKey: ["review-cycles"],
    queryFn: () => fetchClient("/api/v1/reviews-360/cycles").then(r => r.json()),
  });

  const { data: categories } = useQuery({
    queryKey: ["review-categories"],
    queryFn: () => fetchClient("/api/v1/reviews-360/categories").then(r => r.json()),
  });

  const { data: cycleProgress, isLoading: progressLoading } = useQuery({
    queryKey: ["review-cycle-progress", selectedCycle],
    queryFn: () => fetchClient(`/api/v1/reviews-360/cycles/${selectedCycle}/progress`).then(r => r.json()),
    enabled: !!selectedCycle,
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">360° Evaluaciones</h1>
          <p className="text-muted-foreground">Multi-rater performance reviews and feedback</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Nuevo ciclo
        </Button>
      </div>

      <InlineCopilot
        moduleContext="reviews"
        placeholder="Ask about performance reviews and feedback..."
        quickActions={[
          { label: "Summarize my review cycle", message: "Summarize my review cycle" },
          { label: "Identify top performers", message: "Identify top performers" },
          { label: "Show peer feedback themes", message: "Show peer feedback themes" },
          { label: "Suggest development goals", message: "Suggest development goals" },
        ]}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Ciclos activos</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {cyclesLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{cycles?.cycles?.length ?? 0}</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Evaluadores</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">—</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Categorías</CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{categories?.categories?.length ?? 8}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Progreso de ciclo</CardTitle>
          <CardDescription>Selecciona un ciclo para ver su progreso</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedCycle} onValueChange={(v) => setSelectedCycle(v ?? "")}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Seleccionar ciclo..." />
            </SelectTrigger>
            <SelectContent>
              {cycles?.cycles?.map((c: any) => (
                <SelectItem key={c.id} value={c.id}>{c.name} ({c.status})</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {progressLoading && <Skeleton className="h-4 mt-4 w-full" />}
          {cycleProgress && !progressLoading && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span>Completadas: {cycleProgress.submitted_reviews}/{cycleProgress.total_reviews}</span>
                <span className="font-medium">{cycleProgress.completion_pct}%</span>
              </div>
              <Progress value={cycleProgress.completion_pct} className="h-2" />
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Categorías de evaluación</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {categories?.categories?.map((cat: any) => (
              <Card key={cat.key} className="p-4">
                <h4 className="font-medium text-sm">{cat.label}</h4>
                <p className="text-xs text-muted-foreground mt-1">{cat.description}</p>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
