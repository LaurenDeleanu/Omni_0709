"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Target, Plus, Trash2, Save, Star, GripVertical, AlertCircle,
  CheckCircle2, Sparkles, ClipboardList, ChevronRight, Loader2
} from "lucide-react";
import { toast } from "sonner";

interface Criterion {
  id?: string;
  name: string;
  description?: string;
  max_score: number;
  weight: number;
  sort_order: number;
}

interface Scorecard {
  id: string;
  name: string;
  role_title: string;
  department: string | null;
  description: string | null;
  criteria_count: number;
  is_active: boolean;
  created_at: string;
}

interface Stage {
  name: string;
  description?: string;
  duration_minutes: number;
  interviewer_role: string;
  sort_order: number;
  suggested_questions: string[];
  evaluation_focus?: string;
}

interface InterviewKitItem {
  id: string;
  name: string;
  role_title: string;
  scorecard_id: string | null;
  description: string | null;
  total_duration_minutes: number;
  stage_count: number;
  is_active: boolean;
  created_at: string;
}

export function ScorecardBuilder() {
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [description, setDescription] = useState("");
  const [criteria, setCriteria] = useState<Criterion[]>([
    { name: "", description: "", max_score: 5, weight: 1.0, sort_order: 0 },
  ]);

  const { data: scorecards, isLoading } = useQuery<Scorecard[]>({
    queryKey: ["interview-scorecards"],
    queryFn: () => fetchClient("/interview-scorecards").then(r => r),
    enabled: isOpen,
  });

  const createMutation = useMutation({
    mutationFn: (data: any) =>
      fetchClient("/interview-scorecards", { method: "POST", body: JSON.stringify(data) }).then(r => r),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["interview-scorecards"] });
      setIsOpen(false);
      resetForm();
      toast.success("Scorecard created");
    },
    onError: () => toast.error("Failed to create scorecard"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => fetchClient(`/interview-scorecards/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["interview-scorecards"] });
      toast.success("Scorecard deleted");
    },
  });

  const resetForm = () => {
    setName(""); setRoleTitle(""); setDepartment(""); setDescription("");
    setCriteria([{ name: "", description: "", max_score: 5, weight: 1.0, sort_order: 0 }]);
  };

  const addCriterion = () => {
    setCriteria([...criteria, { name: "", description: "", max_score: 5, weight: 1.0, sort_order: criteria.length }]);
  };

  const removeCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const updateCriterion = (index: number, field: keyof Criterion, value: any) => {
    const updated = [...criteria];
    (updated[index] as any)[field] = value;
    setCriteria(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const validCriteria = criteria.filter(c => c.name.trim());
    createMutation.mutate({
      name, role_title: roleTitle, department: department || null,
      description: description || null,
      criteria: validCriteria.map((c, i) => ({ ...c, sort_order: i })),
    });
  };

  return (
    <Card className="glass">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            Plantillas de Evaluación
          </CardTitle>
          <CardDescription>Scorecards estructurados por rol para entrevistas</CardDescription>
        </div>
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogTrigger render={<Button size="sm" className="gap-1.5"><Plus className="h-4 w-4" /> Nuevo</Button>} />
          <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2"><Target className="h-5 w-5 text-primary" /> Crear Scorecard</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Nombre</Label>
                  <Input className="bg-card/60" value={name} onChange={e => setName(e.target.value)} placeholder="Ej: Senior Engineer" required />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Departamento</Label>
                  <Input className="bg-card/60" value={department} onChange={e => setDepartment(e.target.value)} placeholder="Ej: Engineering" />
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Título del Rol</Label>
                <Input className="bg-card/60" value={roleTitle} onChange={e => setRoleTitle(e.target.value)} placeholder="Ej: Senior Software Engineer" required />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Descripción</Label>
                <Textarea className="bg-card/60" value={description} onChange={e => setDescription(e.target.value)} placeholder="Qué evalúa este scorecard..." />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-bold uppercase tracking-wider text-foreground/80">Criterios de Evaluación</Label>
                  <Button type="button" variant="ghost" size="xs" onClick={addCriterion}><Plus className="h-3 w-3 mr-1" /> Añadir</Button>
                </div>
                {criteria.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-muted/30 border border-border/40">
                    <GripVertical className="h-4 w-4 text-muted-foreground mt-2 shrink-0" />
                    <div className="flex-1 space-y-2">
                      <Input className="bg-card/60 h-7 text-sm" value={c.name} onChange={e => updateCriterion(i, "name", e.target.value)} placeholder="Ej: System Design" />
                      <div className="flex gap-2">
                        <div className="w-20">
                          <Label className="text-[10px] text-muted-foreground">Peso</Label>
                          <Input type="number" className="bg-card/60 h-7 text-sm" value={c.weight} onChange={e => updateCriterion(i, "weight", parseFloat(e.target.value) || 1)} min={0.5} max={3} step={0.5} />
                        </div>
                        <div className="w-20">
                          <Label className="text-[10px] text-muted-foreground">Max Punt.</Label>
                          <Input type="number" className="bg-card/60 h-7 text-sm" value={c.max_score} onChange={e => updateCriterion(i, "max_score", parseInt(e.target.value) || 5)} min={1} max={10} />
                        </div>
                      </div>
                    </div>
                    {criteria.length > 1 && (
                      <Button type="button" variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-destructive" onClick={() => removeCriterion(i)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>

              <Button type="submit" className="w-full gap-2" disabled={createMutation.isPending}>
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Guardar Scorecard
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
          </div>
        ) : !scorecards || scorecards.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <ClipboardList className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted-foreground">No hay scorecards definidos.</p>
            <p className="text-xs text-muted-foreground">Crea plantillas de evaluación estructurada para tus procesos de selección.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {scorecards.map(sc => (
              <div key={sc.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/30 transition-colors">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold">{sc.name}</p>
                    <Badge variant="outline" className="text-[10px]">{sc.role_title}</Badge>
                    {sc.department && <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px]">{sc.department}</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{sc.criteria_count} criterios</p>
                </div>
                <Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-destructive" onClick={() => deleteMutation.mutate(sc.id)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
