"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { GrowAPI, Objective, KeyResult, PerformanceReview } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Target, Star, Plus, CheckCircle2, Circle, Edit, Trash, StarIcon } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { InlineCopilot } from "@/components/ai/InlineCopilot";
import { FeedbackModule } from "@/components/performance/FeedbackModule";
import { TalentGrid } from "@/components/talent/TalentGrid";
import { CareerFramework } from "@/components/talent/CareerFramework";
import { OKRCascadingTree } from "@/components/performance/OKRCascadingTree";
import { PulseSurvey } from "@/components/engagement/PulseSurvey";
import { SkillsMatrix } from "@/components/talent/SkillsMatrix";

export default function GrowPage() {
  const [activeTab, setActiveTab] = useState("okrs");
  const { user } = useUser();

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Desempeño y Cultura</h1>
        <p className="text-muted-foreground mt-2">
          Gestiona los objetivos de la empresa (OKRs) y las evaluaciones de desempeño (360°).
        </p>
      </div>

      <InlineCopilot
        moduleContext="grow"
        placeholder="Pregunta sobre desempeño o desarrollo..."
        quickActions={[
          { label: "Summarize my OKR progress", message: "Summarize my OKR progress" },
          { label: "Generate team objectives", message: "Generate team objectives" },
          { label: "Show my review feedback", message: "Show my review feedback" },
          { label: "Suggest career development goals", message: "Suggest career development goals" }
        ]}
      />

      <div className="flex border-b border-border/50 gap-6 overflow-x-auto pb-px">
        <button
          onClick={() => setActiveTab("okrs")}
          className={`flex items-center gap-2 pb-4 px-1 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "okrs" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground/80"
          }`}
        >
          <Target className="w-4 h-4" /> Objetivos (OKRs)
        </button>
        <button
          onClick={() => setActiveTab("reviews")}
          className={`flex items-center gap-2 pb-4 px-1 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "reviews" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground/80"
          }`}
        >
          <Star className="w-4 h-4" /> Evaluaciones
        </button>
      </div>

      <div className="mt-6">
        {activeTab === "okrs" && <OkrsTab userId={user?.id} />}
        {activeTab === "reviews" && <ReviewsTab userId={user?.id} />}
      </div>
    </div>
  );
}

function OkrsTab({ userId }: { userId?: string }) {
  const queryClient = useQueryClient();
  
  // Objective Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  // Edit Objective Modal State
  const [isEditOkrOpen, setIsEditOkrOpen] = useState(false);
  const [selectedOkrForEdit, setSelectedOkrForEdit] = useState<Objective | null>(null);
  const [editOkrTitle, setEditOkrTitle] = useState("");
  const [editOkrStatus, setEditOkrStatus] = useState("");

  // Key Result Modal State
  const [isKRModalOpen, setIsKRModalOpen] = useState(false);
  const [selectedOkrForKR, setSelectedOkrForKR] = useState<string | null>(null);
  const [newKRTitle, setNewKRTitle] = useState("");
  const [newKRTarget, setNewKRTarget] = useState(100);
  const [newKRUnit, setNewKRUnit] = useState("%");

  // Edit KR Modal State
  const [isEditKROpen, setIsEditKROpen] = useState(false);
  const [selectedKRForEdit, setSelectedKRForEdit] = useState<KeyResult | null>(null);
  const [editKRTitle, setEditKRTitle] = useState("");
  const [editKRCurrent, setEditKRCurrent] = useState(0);
  const [editKRTarget, setEditKRTarget] = useState(100);
  const [editKRUnit, setEditKRUnit] = useState("");

  const { data: okrs, isLoading } = useQuery({
    queryKey: ["grow_okrs", userId],
    queryFn: () => GrowAPI.getObjectives(userId),
    enabled: !!userId
  });

  const createMutation = useMutation({
    mutationFn: (title: string) => GrowAPI.createObjective({ title, owner_id: userId, status: "On Track", key_results: [] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_okrs"] });
      toast.success("Objetivo creado");
      setIsModalOpen(false);
      setNewTitle("");
    }
  });

  const updateOkrMutation = useMutation({
    mutationFn: ({ id, title, status }: { id: string; title: string; status: string }) => 
      GrowAPI.updateObjective(id, { title, status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_okrs"] });
      toast.success("Objetivo actualizado");
      setIsEditOkrOpen(false);
    }
  });

  const deleteOkrMutation = useMutation({
    mutationFn: (id: string) => GrowAPI.deleteObjective(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_okrs"] });
      toast.success("Objetivo eliminado");
    }
  });

  const createKRMutation = useMutation({
    mutationFn: ({ objectiveId, title, target_value, unit }: { objectiveId: string; title: string; target_value: number; unit: string }) => 
      GrowAPI.addKeyResult(objectiveId, { title, target_value, current_value: 0, unit }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_okrs"] });
      toast.success("Key Result añadido");
      setIsKRModalOpen(false);
      setNewKRTitle("");
      setNewKRTarget(100);
      setNewKRUnit("%");
    }
  });

  const updateKRMutation = useMutation({
    mutationFn: ({ id, title, current_value, target_value, unit }: { id: string; title: string; current_value: number; target_value: number; unit: string }) => 
      GrowAPI.updateKeyResult(id, { title, current_value, target_value, unit }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_okrs"] });
      toast.success("Key Result actualizado");
      setIsEditKROpen(false);
    }
  });

  const deleteKRMutation = useMutation({
    mutationFn: (id: string) => GrowAPI.deleteKeyResult(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_okrs"] });
      toast.success("Key Result eliminado");
      setIsEditKROpen(false);
    }
  });

  const handleEditObjective = (okr: Objective) => {
    setSelectedOkrForEdit(okr);
    setEditOkrTitle(okr.title);
    setEditOkrStatus(okr.status);
    setIsEditOkrOpen(true);
  };

  const handleEditKR = (kr: KeyResult) => {
    setSelectedKRForEdit(kr);
    setEditKRTitle(kr.title);
    setEditKRCurrent(kr.current_value);
    setEditKRTarget(kr.target_value);
    setEditKRUnit(kr.unit);
    setIsEditKROpen(true);
  };

  if (isLoading) return <div className="text-muted-foreground">Cargando OKRs...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-card/40 p-4 rounded-xl border border-border/50">
        <div>
          <h3 className="font-bold text-lg text-foreground">Mis Objetivos</h3>
          <p className="text-sm text-muted-foreground">Define resultados clave y mide tu progreso.</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="bg-primary text-white">
          <Plus className="w-4 h-4 mr-2" /> Nuevo Objetivo
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {okrs?.length === 0 ? (
          <div className="col-span-2 text-center p-8 border border-dashed rounded-xl text-muted-foreground">
            No tienes objetivos definidos aún.
          </div>
        ) : (
          okrs?.map((okr: Objective) => {
            const totalKR = okr.key_results.length;
            const avgProgress = totalKR > 0 
              ? okr.key_results.reduce((acc, kr) => acc + (kr.current_value / kr.target_value) * 100, 0) / totalKR
              : 0;

            return (
              <Card key={okr.id} className="border-border/60 bg-card/40 backdrop-blur-sm shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start gap-4">
                    <CardTitle className="text-lg leading-tight flex-1">{okr.title}</CardTitle>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        okr.status === "On Track" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                        okr.status === "At Risk" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                        "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}>
                        {okr.status}
                      </span>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={() => handleEditObjective(okr)}>
                        <Edit className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-red-500" onClick={() => { if(confirm("¿Seguro de eliminar este objetivo?")) deleteOkrMutation.mutate(okr.id); }}>
                        <Trash className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                  <CardDescription className="flex items-center justify-between text-xs mt-1">
                    <span>Progreso general: {Math.round(avgProgress)}%</span>
                  </CardDescription>
                  <Progress value={avgProgress} className="h-2 mt-2" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Key Results</div>
                  {okr.key_results.length === 0 ? (
                    <div className="text-xs text-muted-foreground py-2 italic">Sin Key Results definidos.</div>
                  ) : (
                    okr.key_results.map((kr) => {
                      const krProgress = (kr.current_value / kr.target_value) * 100;
                      return (
                        <div 
                          key={kr.id} 
                          onClick={() => handleEditKR(kr)}
                          className="bg-muted/30 p-2.5 rounded-lg border border-border/50 hover:bg-muted/60 transition-colors cursor-pointer group/kr flex justify-between items-center"
                        >
                          <div className="flex-1 min-w-0 mr-2">
                            <div className="flex justify-between text-sm mb-1.5">
                              <span className="font-medium flex items-center gap-2 truncate">
                                {krProgress >= 100 ? (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                                ) : (
                                  <Circle className="w-4 h-4 text-muted-foreground shrink-0" />
                                )}
                                <span className="truncate">{kr.title}</span>
                              </span>
                              <span className="text-muted-foreground shrink-0 text-xs font-semibold">{kr.current_value} / {kr.target_value} {kr.unit}</span>
                            </div>
                            <Progress value={krProgress} className="h-1.5" />
                          </div>
                          <Edit className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover/kr:opacity-100 transition-opacity" />
                        </div>
                      )
                    })
                  )}
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="w-full mt-2 text-xs h-8 hover:bg-primary/10 hover:text-primary border border-dashed border-border"
                    onClick={() => {
                      setSelectedOkrForKR(okr.id);
                      setIsKRModalOpen(true);
                    }}
                  >
                    <Plus className="w-3 h-3 mr-1" /> Añadir Key Result
                  </Button>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* DIALOG: CREATE OBJECTIVE */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo Objetivo (OKR)</DialogTitle>
            <DialogDescription>Define un objetivo inspirador e impactante.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Título del Objetivo</Label>
              <Input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Ej: Expandir mercado en LATAM" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button onClick={() => createMutation.mutate(newTitle)} disabled={!newTitle || createMutation.isPending}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG: EDIT OBJECTIVE */}
      <Dialog open={isEditOkrOpen} onOpenChange={setIsEditOkrOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Objetivo</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Título del Objetivo</Label>
              <Input value={editOkrTitle} onChange={e => setEditOkrTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Estado</Label>
              <select 
                value={editOkrStatus} 
                onChange={e => setEditOkrStatus(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="On Track">A Tiempo (On Track)</option>
                <option value="At Risk">En Riesgo (At Risk)</option>
                <option value="Behind">Retrasado (Behind)</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOkrOpen(false)}>Cancelar</Button>
            <Button onClick={() => selectedOkrForEdit && updateOkrMutation.mutate({ id: selectedOkrForEdit.id, title: editOkrTitle, status: editOkrStatus })} disabled={updateOkrMutation.isPending}>
              Guardar Cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG: ADD KEY RESULT */}
      <Dialog open={isKRModalOpen} onOpenChange={setIsKRModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Añadir Key Result</DialogTitle>
            <DialogDescription>Define una métrica cuantitativa para medir el éxito del objetivo.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Título del KR</Label>
              <Input value={newKRTitle} onChange={e => setNewKRTitle(e.target.value)} placeholder="Ej: Conseguir 15 nuevos clientes corporativos" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Valor Objetivo</Label>
                <Input type="number" value={newKRTarget} onChange={e => setNewKRTarget(parseFloat(e.target.value) || 0)} />
              </div>
              <div className="space-y-2">
                <Label>Unidad</Label>
                <Input value={newKRUnit} onChange={e => setNewKRUnit(e.target.value)} placeholder="Ej: %, USD, clientes" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsKRModalOpen(false)}>Cancelar</Button>
            <Button onClick={() => selectedOkrForKR && createKRMutation.mutate({ objectiveId: selectedOkrForKR, title: newKRTitle, target_value: newKRTarget, unit: newKRUnit })} disabled={!newKRTitle || createKRMutation.isPending}>
              Añadir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG: EDIT/UPDATE KEY RESULT */}
      <Dialog open={isEditKROpen} onOpenChange={setIsEditKROpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Actualizar Key Result</DialogTitle>
            <DialogDescription>Modifica el progreso o cambia los parámetros del resultado clave.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Título del KR</Label>
              <Input value={editKRTitle} onChange={e => setEditKRTitle(e.target.value)} />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Progreso Actual</Label>
                <Input type="number" value={editKRCurrent} onChange={e => setEditKRCurrent(parseFloat(e.target.value) || 0)} />
              </div>
              <div className="space-y-2">
                <Label>Meta Final</Label>
                <Input type="number" value={editKRTarget} onChange={e => setEditKRTarget(parseFloat(e.target.value) || 0)} />
              </div>
              <div className="space-y-2">
                <Label>Unidad</Label>
                <Input value={editKRUnit} onChange={e => setEditKRUnit(e.target.value)} />
              </div>
            </div>
          </div>
          <DialogFooter className="flex justify-between items-center w-full">
            <Button variant="destructive" onClick={() => { if(confirm("¿Eliminar este Key Result?")) selectedKRForEdit && deleteKRMutation.mutate(selectedKRForEdit.id); }} disabled={deleteKRMutation.isPending}>
              Eliminar
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditKROpen(false)}>Cancelar</Button>
              <Button onClick={() => selectedKRForEdit && updateKRMutation.mutate({ id: selectedKRForEdit.id, title: editKRTitle, current_value: editKRCurrent, target_value: editKRTarget, unit: editKRUnit })} disabled={updateKRMutation.isPending}>
                Guardar
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ReviewsTab({ userId }: { userId?: string }) {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Review Dialog State
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [selectedReview, setSelectedReview] = useState<PerformanceReview | null>(null);
  const [evalRating, setEvalRating] = useState(4);
  const [evalComments, setEvalComments] = useState("");

  const { data: reviews, isLoading } = useQuery({
    queryKey: ["grow_reviews", userId],
    queryFn: () => GrowAPI.getReviews(userId),
    enabled: !!userId
  });

  const createMutation = useMutation({
    mutationFn: () => GrowAPI.createReview({ employee_id: userId, manager_id: userId, cycle_name: "Evaluación Q1 2026", status: "Pendiente" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_reviews"] });
      toast.success("Evaluación iniciada");
      setIsModalOpen(false);
    }
  });

  const submitEvaluationMutation = useMutation({
    mutationFn: ({ id, rating, comments }: { id: string; rating: number; comments: string }) =>
      GrowAPI.updateReview(id, { 
        self_evaluation: { rating, comments }, 
        status: "Completada" 
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grow_reviews"] });
      toast.success("Evaluación de desempeño enviada");
      setIsReviewOpen(false);
    }
  });

  const handleOpenReview = (review: PerformanceReview) => {
    setSelectedReview(review);
    const existingEval = review.self_evaluation || {};
    setEvalRating(existingEval.rating || 4);
    setEvalComments(existingEval.comments || "");
    setIsReviewOpen(true);
  };

  if (isLoading) return <div className="text-muted-foreground">Cargando evaluaciones...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-card/40 p-4 rounded-xl border border-border/50">
        <div>
          <h3 className="font-bold text-lg text-foreground">Evaluaciones 360°</h3>
          <p className="text-sm text-muted-foreground">Completa tu auto-evaluación y revisa feedback de tu manager.</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="bg-primary text-white">
          Solicitar Evaluación
        </Button>
      </div>

      <div className="grid gap-4">
        {reviews?.length === 0 ? (
          <div className="text-center p-8 border border-dashed rounded-xl text-muted-foreground">
            No tienes evaluaciones pendientes o históricas.
          </div>
        ) : (
          reviews?.map((review: PerformanceReview) => (
            <div key={review.id} className="p-4 rounded-xl border border-border/60 bg-card flex justify-between items-center hover:bg-muted/20 transition-colors">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500">
                  <Star className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-semibold">{review.cycle_name}</h4>
                  <p className="text-sm text-muted-foreground">
                    Estado: <span className="text-foreground font-medium">{review.status}</span>
                  </p>
                </div>
              </div>
              <Button variant="outline" onClick={() => handleOpenReview(review)}>
                {review.status === "Completada" ? "Ver Formulario" : "Responder Formulario"}
              </Button>
            </div>
          ))
        )}
      </div>

      {/* DIALOG: REQUEST REVIEW */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Iniciar Ciclo de Evaluación</DialogTitle>
            <DialogDescription>¿Deseas solicitar una nueva evaluación de desempeño para Q1 2026?</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>Confirmar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG: REVIEW QUESTIONNAIRE */}
      <Dialog open={isReviewOpen} onOpenChange={setIsReviewOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Auto-Evaluación de Desempeño</DialogTitle>
            <DialogDescription>Completa este cuestionario para registrar tu autoevaluación en el ciclo.</DialogDescription>
          </DialogHeader>
          
          {selectedReview && (
            <div className="space-y-5 py-4">
              <div className="space-y-2">
                <Label className="text-sm font-semibold">Calificación General (1 al 5)</Label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      disabled={selectedReview.status === "Completada"}
                      onClick={() => setEvalRating(star)}
                      className={`text-2xl p-1 transition-transform ${
                        star <= evalRating ? "text-yellow-400 scale-110" : "text-muted border-transparent hover:text-yellow-200"
                      }`}
                    >
                      <StarIcon className="w-6 h-6 fill-current" />
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-semibold">Comentarios / Logros Clave</Label>
                <Textarea
                  disabled={selectedReview.status === "Completada"}
                  rows={5}
                  value={evalComments}
                  onChange={(e) => setEvalComments(e.target.value)}
                  placeholder="Comenta tus logros principales y áreas de mejora..."
                />
              </div>

              {selectedReview.status === "Completada" && selectedReview.manager_evaluation && (
                <div className="mt-4 p-4 bg-muted/30 border rounded-lg space-y-2">
                  <h5 className="font-bold text-xs uppercase tracking-wider text-muted-foreground">Evaluación del Manager</h5>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <StarIcon
                        key={star}
                        className={`w-4 h-4 ${
                          star <= (selectedReview.manager_evaluation.rating || 0) ? "text-yellow-400 fill-current" : "text-muted-foreground/30"
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-sm italic text-foreground mt-1">
                    {selectedReview.manager_evaluation.comments || "Sin comentarios adicionales."}
                  </p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsReviewOpen(false)}>Cerrar</Button>
            {selectedReview?.status !== "Completada" && (
              <Button
                onClick={() => selectedReview && submitEvaluationMutation.mutate({ id: selectedReview.id, rating: evalRating, comments: evalComments })}
                disabled={submitEvaluationMutation.isPending || !evalComments}
              >
                Enviar Autoevaluación
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <FeedbackModule />

      <TalentGrid />

      <CareerFramework />

      <OKRCascadingTree />

      <PulseSurvey />

      <SkillsMatrix />
    </div>
  );
}
