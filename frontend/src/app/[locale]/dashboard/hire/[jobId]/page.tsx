"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HireAPI, UserAPI, Candidate, Employee } from "@/lib/api";
import {
  Plus, ArrowLeft, MoreHorizontal, Mail, Phone, Calendar, User, Search,
  Briefcase, Building2, MapPin, ChevronRight, Star, ExternalLink, FileText,
  Trash2, Award, ClipboardList, CheckCircle2, AlertCircle, Loader2, Sparkles,
  ArrowRight, UserCheck, ShieldAlert, Eye, EyeOff, Tag, X, Laptop
} from "lucide-react";
import { Link } from "@/i18n/routing";
import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

function getInitials(name: string) {
  return name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "?";
}

const KANBAN_STAGES = [
  { id: "applied", name: "Nuevos", color: "bg-slate-50 dark:bg-slate-900/10 border-slate-200/60 dark:border-slate-800/40" },
  { id: "screening", name: "Screening", color: "bg-blue-50/40 dark:bg-blue-900/5 border-blue-200/50 dark:border-blue-900/10" },
  { id: "interview", name: "Entrevistas", color: "bg-purple-50/40 dark:bg-purple-900/5 border-purple-200/50 dark:border-purple-900/10" },
  { id: "offer", name: "Oferta", color: "bg-amber-50/40 dark:bg-amber-900/5 border-amber-200/50 dark:border-amber-900/10" },
  { id: "hired", name: "Contratados", color: "bg-emerald-50/40 dark:bg-emerald-900/5 border-emerald-200/50 dark:border-emerald-900/10" },
  { id: "rejected", name: "Rechazados", color: "bg-red-50/40 dark:bg-red-900/5 border-red-200/50 dark:border-red-900/10" },
];

export default function KanbanBoard() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;
  const queryClient = useQueryClient();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Drawer States
  const [sheetOpen, setSheetOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [notesText, setNotesText] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [currentTags, setCurrentTags] = useState<string[]>([]);

  // Onboarding options
  const [onboardOptions, setOnboardOptions] = useState({
    assign_onboarding_plan: true,
    enroll_in_training: true,
    request_it_equipment: false,
    it_equipment_type: "laptop",
    it_equipment_quantity: 1,
  });
  
  // Interview Scheduler States
  const [interviewForm, setInterviewForm] = useState({
    interviewer_id: "",
    scheduled_at: "",
    duration_minutes: 60,
    interview_type: "Technical",
    feedback_notes: "",
    score: 5,
  });

  // Onboarding Wizard States
  const [onboardOpen, setOnboardOpen] = useState(false);
  const [onboardForm, setOnboardForm] = useState({
    password: "",
    phone_number: "",
    address: "",
    contract_type: "Indefinido",
    hire_date: new Date().toISOString().split("T")[0],
    base_salary: 50000,
    social_security_number: "",
    iban: "",
    country: "ES",
    role: "employee",
  });

  // Active query definitions
  const { data: job, isLoading: isLoadingJob } = useQuery({
    queryKey: ["hireJob", jobId],
    queryFn: () => HireAPI.getJob(jobId),
  });

  const { data: candidates, isLoading: isLoadingCandidates } = useQuery({
    queryKey: ["hireCandidates", jobId],
    queryFn: () => HireAPI.getCandidates(jobId),
  });

  const { data: employees } = useQuery<Employee[]>({
    queryKey: ["employees"],
    queryFn: UserAPI.getEmployees,
  });

  const { data: interviews, isLoading: isLoadingInterviews } = useQuery({
    queryKey: ["candidateInterviews", selectedCandidate?.id],
    queryFn: () => HireAPI.getInterviews(selectedCandidate!.id),
    enabled: !!selectedCandidate,
  });

  // Mutations
  const addCandidateMutation = useMutation({
    mutationFn: HireAPI.addCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hireCandidates", jobId] });
      setIsModalOpen(false);
      toast.success("Candidato registrado con éxito");
    },
    onError: () => toast.error("Error al registrar el candidato")
  });

  const updateCandidateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Candidate> }) => HireAPI.updateCandidate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hireCandidates", jobId] });
      toast.success("Notas del candidato guardadas");
    },
    onError: () => toast.error("Error al actualizar la ficha")
  });

  const updateStageMutation = useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: string }) => HireAPI.updateCandidateStage(id, stage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hireCandidates", jobId] });
      toast.success("Estado actualizado");
    },
  });

  const toggleJobStatusMutation = useMutation({
    mutationFn: () => {
      const nextStatus = job?.status === "open" ? "closed" : "open";
      return HireAPI.updateJob(jobId, { status: nextStatus });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hireJob", jobId] });
      toast.success(job?.status === "open" ? "Vacante cerrada con éxito" : "Vacante reabierta con éxito");
    },
    onError: () => toast.error("Error al actualizar el estado de la vacante"),
  });

  const scheduleInterviewMutation = useMutation({
    mutationFn: ({ candidateId, data }: { candidateId: string; data: any }) => HireAPI.createInterview(candidateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidateInterviews", selectedCandidate?.id] });
      setInterviewForm({
        interviewer_id: "",
        scheduled_at: "",
        duration_minutes: 60,
        interview_type: "Technical",
        feedback_notes: "",
        score: 5,
      });
      toast.success("Entrevista agendada correctamente");
    },
    onError: () => toast.error("Error al agendar entrevista")
  });

  const deleteInterviewMutation = useMutation({
    mutationFn: ({ candidateId, interviewId }: { candidateId: string; interviewId: string }) =>
      HireAPI.deleteInterview(candidateId, interviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidateInterviews", selectedCandidate?.id] });
      toast.success("Entrevista cancelada");
    },
  });

  const promoteMutation = useMutation({
    mutationFn: ({ candidateId, data }: { candidateId: string; data: any }) =>
      HireAPI.promoteCandidate(candidateId, data),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["hireCandidates", jobId] });
      setOnboardOpen(false);
      setSheetOpen(false);
      const parts = ["¡Candidato contratado y promocionado a Personal con éxito!"];
      if (data.onboarding?.plan) parts.push("Plan de onboarding generado.");
      if (data.onboarding?.training) parts.push(`${data.onboarding.training.courses} cursos asignados.`);
      if (data.onboarding?.it_equipment) parts.push(`Equipo IT solicitado: ${data.onboarding.it_equipment.quantity}x ${data.onboarding.it_equipment.item}.`);
      toast.success(parts.join(" "));
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al promocionar al candidato. Verifica si el email ya existe.");
    }
  });

  const saveTagsMutation = useMutation({
    mutationFn: ({ candidateId, tags }: { candidateId: string; tags: string[] }) =>
      HireAPI.updateCrmData(candidateId, { tags: JSON.stringify(tags) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hireCandidates", jobId] });
      toast.success("Tags updated");
    },
    onError: () => toast.error("Error saving tags"),
  });

  const addTag = () => {
    const trimmed = tagInput.trim();
    if (!trimmed || !selectedCandidate) return;
    if (currentTags.includes(trimmed)) { setTagInput(""); return; }
    const newTags = [...currentTags, trimmed];
    setCurrentTags(newTags);
    setTagInput("");
    saveTagsMutation.mutate({ candidateId: selectedCandidate.id, tags: newTags });
  };

  const removeTag = (tag: string) => {
    if (!selectedCandidate) return;
    const newTags = currentTags.filter(t => t !== tag);
    setCurrentTags(newTags);
    saveTagsMutation.mutate({ candidateId: selectedCandidate.id, tags: newTags });
  };

  // Action handlers
  const handleAddCandidate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    addCandidateMutation.mutate({
      job_id: jobId,
      first_name: formData.get("first_name") as string,
      last_name: formData.get("last_name") as string,
      email: formData.get("email") as string,
      phone: formData.get("phone") as string,
      source: "Manual",
    });
  };

  const handleNotesSave = () => {
    if (selectedCandidate) {
      updateCandidateMutation.mutate({ id: selectedCandidate.id, data: { notes: notesText } });
    }
  };

  const handleScheduleInterview = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;
    if (!interviewForm.interviewer_id || !interviewForm.scheduled_at) {
      toast.error("Por favor, selecciona entrevistador y fecha");
      return;
    }
    scheduleInterviewMutation.mutate({
      candidateId: selectedCandidate.id,
      data: {
        ...interviewForm,
        score: Number(interviewForm.score),
        scheduled_at: new Date(interviewForm.scheduled_at).toISOString(),
      }
    });
  };

  const handlePromoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;

    // Validate IBAN
    if (onboardForm.iban) {
      const cleanIban = onboardForm.iban.replace(/\s+/g, "").toUpperCase();
      if (!/^ES\d{22}$/.test(cleanIban)) {
        toast.error("Introduce un IBAN español válido (ES + 22 dígitos)");
        return;
      }
    }

    if (!onboardForm.password || onboardForm.password.length < 6) {
      toast.error("La contraseña inicial debe tener al menos 6 caracteres");
      return;
    }

    promoteMutation.mutate({
      candidateId: selectedCandidate.id,
      data: {
        ...onboardForm,
        phone_number: onboardForm.phone_number || selectedCandidate.phone || "",
        base_salary: Number(onboardForm.base_salary),
        hire_date: onboardForm.hire_date ? new Date(onboardForm.hire_date).toISOString() : null,
        ...onboardOptions,
      }
    });
  };

  // Drag & Drop
  const onDragStart = (e: React.DragEvent, candidateId: string) => {
    e.dataTransfer.setData("candidateId", candidateId);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const onDrop = (e: React.DragEvent, stageId: string) => {
    const candidateId = e.dataTransfer.getData("candidateId");
    if (candidateId) {
      updateStageMutation.mutate({ id: candidateId, stage: stageId });
    }
  };

  const filteredCandidates = useMemo(() => {
    if (!candidates) return [];
    if (!searchQuery) return candidates;
    const lower = searchQuery.toLowerCase();
    return candidates.filter((c: Candidate) => 
      c.first_name.toLowerCase().includes(lower) || 
      c.last_name.toLowerCase().includes(lower) || 
      c.email.toLowerCase().includes(lower)
    );
  }, [candidates, searchQuery]);

  const openCandidateDrawer = (c: Candidate) => {
    setSelectedCandidate(c);
    setNotesText(c.notes || "");
    try {
      setCurrentTags(c.tags ? JSON.parse(c.tags) : []);
    } catch {
      setCurrentTags([]);
    }
    setTagInput("");
    setOnboardOptions({
      assign_onboarding_plan: true,
      enroll_in_training: true,
      request_it_equipment: false,
      it_equipment_type: "laptop",
      it_equipment_quantity: 1,
    });
    // Fill onboarding wizard with defaults
    setOnboardForm({
      password: Math.random().toString(36).slice(-8), // Random initial pass
      phone_number: c.phone || "",
      address: "",
      contract_type: "Indefinido",
      hire_date: new Date().toISOString().split("T")[0],
      base_salary: 50000,
      social_security_number: "",
      iban: "",
      country: "ES",
      role: "employee",
    });
    setSheetOpen(true);
  };

  // Real-time IBAN validation check
  const isIbanValid = useMemo(() => {
    if (!onboardForm.iban) return true;
    const cleanIban = onboardForm.iban.replace(/\s+/g, "").toUpperCase();
    return /^ES\d{22}$/.test(cleanIban);
  }, [onboardForm.iban]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="h-20 border-b border-border/80 bg-card/40 backdrop-blur-xl px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/hire" className="p-2 hover:bg-muted rounded-full transition-colors text-muted-foreground hover:text-foreground">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight">{isLoadingJob ? "Cargando..." : job?.title}</h1>
              {!isLoadingJob && job && (
                <Badge
                  variant="outline"
                  className={`text-[10px] font-semibold px-2 py-0.5 ${
                    job.status === "open"
                      ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                      : "bg-slate-500/10 text-slate-500 border-slate-500/20"
                  }`}
                >
                  {job.status === "open" ? "Abierta" : "Cerrada"}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
              {job?.department} • {job?.location} • {job?.employment_type}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative hidden md:block">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input 
              placeholder="Buscar candidato..." 
              className="pl-9 w-64 bg-background"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {!isLoadingJob && job && (
            <Button
              variant="outline"
              size="sm"
              className="border-border hover:bg-muted text-xs h-9 gap-1.5 shadow-xs"
              onClick={() => toggleJobStatusMutation.mutate()}
              disabled={toggleJobStatusMutation.isPending}
            >
              {toggleJobStatusMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : job.status === "open" ? (
                <>
                  <EyeOff className="w-3.5 h-3.5 text-muted-foreground" />
                  Cerrar Vacante
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5 text-primary" />
                  Reabrir Vacante
                </>
              )}
            </Button>
          )}
          
          <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
            <DialogTrigger render={<Button className="gap-2 bg-primary hover:bg-primary/95 transition-all shadow-xs" />}>
                <Plus className="h-4 w-4" />
                Añadir Candidato
            </DialogTrigger>
            <DialogContent className="sm:max-w-[450px]">
              <DialogHeader>
                <DialogTitle>Añadir Candidato Manualmente</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleAddCandidate} className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">Nombre *</Label>
                    <Input id="first_name" name="first_name" required placeholder="Ej: Juan" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Apellidos *</Label>
                    <Input id="last_name" name="last_name" required placeholder="Ej: Pérez" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input id="email" name="email" type="email" required placeholder="ejemplo@candidato.com" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Teléfono (Opcional)</Label>
                  <Input id="phone" name="phone" placeholder="Ej: 600111222" />
                </div>
                <div className="pt-4 flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                  <Button type="submit" disabled={addCandidateMutation.isPending}>
                    {addCandidateMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    Guardar Candidato
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Kanban Board Area */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6 bg-slate-50/50 dark:bg-background/20">
        <div className="flex gap-6 h-full items-start w-max min-w-full">
          {KANBAN_STAGES.map((stage) => {
            const stageCandidates = filteredCandidates.filter((c: Candidate) => c.stage === stage.id);
            
            return (
              <div 
                key={stage.id} 
                className={`flex flex-col w-80 h-full max-h-full rounded-2xl border backdrop-blur-md bg-card/60 p-4 shrink-0 transition-colors shadow-xs ${stage.color}`}
                onDragOver={onDragOver}
                onDrop={(e) => onDrop(e, stage.id)}
              >
                <div className="flex items-center justify-between mb-4 px-2 pt-1">
                  <h3 className="font-bold text-xs uppercase tracking-wider text-muted-foreground">{stage.name}</h3>
                  <span className="bg-card text-foreground text-xs font-semibold py-0.5 px-2.5 rounded-full border border-border shadow-xs">
                    {stageCandidates.length}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto space-y-3 pb-2 custom-scrollbar pr-1">
                  {stageCandidates.map((c: Candidate) => (
                    <div 
                      key={c.id} 
                      draggable
                      onDragStart={(e) => onDragStart(e, c.id)}
                      onClick={() => openCandidateDrawer(c)}
                      className="bg-card border border-border/80 hover:border-primary/40 rounded-xl p-4 shadow-xs hover:shadow-md transition-all cursor-grab active:cursor-grabbing group relative overflow-hidden"
                    >
                      {/* Visual HSL indicator */}
                      <div className="absolute top-0 left-0 bottom-0 w-1 bg-primary/20 group-hover:bg-primary transition-colors" />
                      
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-bold text-sm text-foreground group-hover:text-primary transition-colors">
                          {c.first_name} {c.last_name}
                        </h4>
                        <button className="text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="space-y-1.5 mt-3 text-xs text-muted-foreground">
                        <div className="flex items-center gap-2">
                          <Mail className="w-3.5 h-3.5" />
                          <span className="truncate">{c.email}</span>
                        </div>
                        {c.phone && (
                          <div className="flex items-center gap-2">
                            <Phone className="w-3.5 h-3.5" />
                            <span>{c.phone}</span>
                          </div>
                        )}
                        
                        <div className="flex items-center justify-between gap-2 mt-2 pt-2 border-t border-border/50 text-[10px]">
                          <span className="bg-muted px-2 py-0.5 rounded-md font-medium text-foreground capitalize">
                            {c.source || "Manual"}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(c.created_at).toLocaleDateString("es-ES")}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {stageCandidates.length === 0 && !isLoadingCandidates && (
                    <div className="h-24 rounded-xl border-2 border-dashed border-border/40 flex items-center justify-center text-xs text-muted-foreground/50 bg-muted/5">
                      Arrastrar candidatos aquí
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Candidate Details Drawer (Ficha de Candidato Premium) */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-full sm:max-w-xl overflow-y-auto max-h-screen pb-10">
          {selectedCandidate && (
            <>
              <SheetHeader className="pb-4 border-b">
                <SheetTitle className="text-2xl font-bold flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 font-extrabold text-primary text-sm">
                    {getInitials(`${selectedCandidate.first_name} ${selectedCandidate.last_name}`)}
                  </div>
                  <div>
                    <div>{selectedCandidate.first_name} {selectedCandidate.last_name}</div>
                    <span className="text-xs text-muted-foreground font-normal">Candidatura en proceso</span>
                  </div>
                </SheetTitle>
                <SheetDescription className="flex items-center gap-2 mt-2">
                  <Badge variant="outline" className="capitalize">
                    Fase: {KANBAN_STAGES.find(s => s.id === selectedCandidate.stage)?.name}
                  </Badge>
                  <span className="text-xs text-muted-foreground">Origen: {selectedCandidate.source || "Manual"}</span>
                </SheetDescription>
              </SheetHeader>

              {/* Onboarding Trigger Button (Promo) */}
              {(selectedCandidate.stage === "offer" || selectedCandidate.stage === "hired" || selectedCandidate.stage === "interview") && (
                <div className="mt-4 p-4 border border-emerald-500/25 bg-emerald-500/5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                      <Sparkles className="w-4 h-4 animate-spin-slow" /> Candidato Listo para Contratación
                    </h4>
                    <p className="text-[10px] text-muted-foreground">
                      Promociona al candidato de forma directa al Centro de Personal estructurando su onboarding español.
                    </p>
                  </div>
                  <Button
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 shrink-0 shadow-sm"
                    onClick={() => setOnboardOpen(true)}
                  >
                    <UserCheck className="w-4 h-4" /> Promocionar a Personal
                  </Button>
                </div>
              )}

              <div className="py-6 space-y-6">
                {/* Section A: Ficha de Contacto y Perfil */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-primary border-l-2 border-primary pl-2 flex items-center justify-between">
                    Información de Perfil
                    <User className="w-4 h-4 text-muted-foreground" />
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-muted/20 border rounded-xl p-3.5 text-xs space-y-1 sm:space-y-0">
                    <div>
                      <span className="text-muted-foreground font-semibold">Correo Electrónico:</span>
                      <p className="font-medium text-foreground truncate">{selectedCandidate.email}</p>
                    </div>
                    {selectedCandidate.phone && (
                      <div>
                        <span className="text-muted-foreground font-semibold">Teléfono Móvil:</span>
                        <p className="font-medium text-foreground">{selectedCandidate.phone}</p>
                      </div>
                    )}
                    <div className="sm:col-span-2 pt-2 border-t flex flex-wrap gap-3">
                      <Button variant="outline" size="xs" className="h-7 text-[10px] gap-1 shadow-xs" onClick={() => window.open(`mailto:${selectedCandidate.email}`)}>
                        <Mail className="w-3.5 h-3.5" /> Enviar Correo
                      </Button>
                      {selectedCandidate.linkedin_url && (
                        <Button variant="outline" size="xs" className="h-7 text-[10px] gap-1 shadow-xs" onClick={() => window.open(selectedCandidate.linkedin_url)}>
                          <ExternalLink className="w-3.5 h-3.5 text-blue-500" /> LinkedIn
                        </Button>
                      )}
                      {selectedCandidate.portfolio_url && (
                        <Button variant="outline" size="xs" className="h-7 text-[10px] gap-1 shadow-xs" onClick={() => window.open(selectedCandidate.portfolio_url)}>
                          <FileText className="w-3.5 h-3.5 text-purple-500" /> Portafolio
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-primary border-l-2 border-primary pl-2 flex items-center justify-between">
                    Tags / Etiquetas
                    <Tag className="w-4 h-4 text-muted-foreground" />
                  </h3>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {currentTags.map((tag) => (
                      <Badge key={tag} className="bg-blue-500/10 text-blue-600 border-blue-500/20 gap-1 pr-1 text-xs">
                        {tag}
                        <button onClick={() => removeTag(tag)} className="hover:text-red-500 ml-0.5">
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Type tag and press Enter..."
                      className="h-8 text-xs"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
                    />
                    <Button size="xs" variant="outline" className="h-8 text-xs" onClick={addTag}>
                      Add
                    </Button>
                  </div>
                </div>

                {/* Section B: Notas de Seguimiento Internas */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">
                    Notas Internas del Candidato
                  </h3>
                  <div className="space-y-2">
                    <Textarea
                      placeholder="Redacta notas sobre la trayectoria del candidato, expectativas salariales, fortalezas..."
                      className="min-h-24 bg-card"
                      value={notesText}
                      onChange={(e) => setNotesText(e.target.value)}
                    />
                    <div className="flex justify-end">
                      <Button
                        size="xs"
                        onClick={handleNotesSave}
                        disabled={updateCandidateMutation.isPending}
                        className="h-8 shadow-xs"
                      >
                        {updateCandidateMutation.isPending && <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />}
                        Guardar Notas
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Section C: Entrevistas & Calificaciones */}
                <div className="space-y-4 pt-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-primary border-l-2 border-primary pl-2 flex items-center justify-between">
                    Entrevistas y Evaluaciones
                    <ClipboardList className="w-4 h-4 text-muted-foreground" />
                  </h3>

                  {/* Scheduled Interviews List */}
                  {isLoadingInterviews ? (
                    <div className="flex justify-center py-4 text-xs text-muted-foreground gap-1.5">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" /> Cargando evaluaciones...
                    </div>
                  ) : !interviews || interviews.length === 0 ? (
                    <div className="text-xs text-muted-foreground italic text-center bg-muted/20 border border-dashed rounded-xl py-6">
                      No se han agendado entrevistas para este candidato todavía.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {interviews.map((inv: any) => (
                        <div key={inv.id} className="border bg-card/40 rounded-xl p-3.5 text-xs shadow-xs relative group/inv">
                          <div className="flex items-start justify-between gap-4">
                            <div className="space-y-1.5 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-bold text-foreground">{inv.interview_type} Interview</span>
                                <Badge variant="secondary" className="text-[9px] px-1.5 py-0.2">{inv.duration_minutes} min</Badge>
                                
                                {/* Score stars representation */}
                                {inv.score !== null && (
                                  <div className="flex items-center gap-0.5 ml-1">
                                    {Array(5).fill(0).map((_, i) => (
                                      <Star
                                        key={i}
                                        className={`w-3.5 h-3.5 ${
                                          i < Math.round(inv.score)
                                            ? "text-amber-400 fill-amber-400"
                                            : "text-muted"
                                        }`}
                                      />
                                    ))}
                                    <span className="font-semibold text-foreground text-[10px] ml-1">({inv.score}/5)</span>
                                  </div>
                                )}
                              </div>
                              <div className="text-muted-foreground text-[10px]">
                                Evaluador: <span className="font-semibold text-foreground">{inv.interviewer_name}</span> • Fecha: {new Date(inv.scheduled_at).toLocaleString("es-ES")}
                              </div>
                              {inv.feedback_notes && (
                                <p className="text-[11px] text-muted-foreground italic bg-muted/20 rounded border-l-2 border-primary/50 pl-2 py-1 mt-2">
                                  "{inv.feedback_notes}"
                                </p>
                              )}
                            </div>
                            
                            <Button
                              variant="ghost"
                              size="xs"
                              className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive opacity-0 group-hover/inv:opacity-100 transition-opacity"
                              onClick={() => {
                                if (confirm("¿Cancelar esta entrevista programada?")) {
                                  deleteInterviewMutation.mutate({ candidateId: selectedCandidate.id, interviewId: inv.id });
                                }
                              }}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Schedule Interview Form */}
                  <form onSubmit={handleScheduleInterview} className="border border-border/80 rounded-2xl p-4 bg-muted/10 space-y-4 pt-4">
                    <h4 className="text-xs font-bold text-foreground">Programar y Calificar Nueva Entrevista</h4>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="inv-interviewer" className="text-[11px]">Entrevistador (Personal) *</Label>
                        <Select
                          value={interviewForm.interviewer_id}
                          onValueChange={(v) => setInterviewForm({ ...interviewForm, interviewer_id: v || "" })}
                        >
                          <SelectTrigger id="inv-interviewer" className="h-8 text-xs bg-card">
                            <SelectValue placeholder="Seleccionar" />
                          </SelectTrigger>
                          <SelectContent>
                            {employees?.filter(e => e.is_active).map((e) => (
                              <SelectItem key={e.id} value={e.id}>{e.full_name || e.email}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1.5">
                        <Label htmlFor="inv-date" className="text-[11px]">Fecha y Hora *</Label>
                        <Input
                          id="inv-date"
                          type="datetime-local"
                          className="h-8 text-xs bg-card"
                          value={interviewForm.scheduled_at}
                          onChange={(e) => setInterviewForm({ ...interviewForm, scheduled_at: e.target.value })}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="inv-type" className="text-[11px]">Tipo de Sesión</Label>
                        <Select
                          value={interviewForm.interview_type}
                          onValueChange={(v) => setInterviewForm({ ...interviewForm, interview_type: v || "" })}
                        >
                          <SelectTrigger id="inv-type" className="h-8 text-xs bg-card">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Technical">Técnica</SelectItem>
                            <SelectItem value="Cultural">Cultural</SelectItem>
                            <SelectItem value="HR">Recursos Humanos</SelectItem>
                            <SelectItem value="Offer">Revisión de Oferta</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1.5">
                        <Label htmlFor="inv-duration" className="text-[11px]">Duración (Minutos)</Label>
                        <Input
                          id="inv-duration"
                          type="number"
                          min="15"
                          step="15"
                          className="h-8 text-xs bg-card"
                          value={interviewForm.duration_minutes}
                          onChange={(e) => setInterviewForm({ ...interviewForm, duration_minutes: parseInt(e.target.value) || 60 })}
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label htmlFor="inv-score" className="text-[11px]">Score / Puntuación (1-5)</Label>
                        <Select
                          value={String(interviewForm.score)}
                          onValueChange={(v) => setInterviewForm({ ...interviewForm, score: parseInt(v || "5") })}
                        >
                          <SelectTrigger id="inv-score" className="h-8 text-xs bg-card">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="5">⭐⭐⭐⭐⭐ (Excelente)</SelectItem>
                            <SelectItem value="4">⭐⭐⭐⭐ (Muy Bueno)</SelectItem>
                            <SelectItem value="3">⭐⭐⭐ (Aceptable)</SelectItem>
                            <SelectItem value="2">⭐⭐ (Insuficiente)</SelectItem>
                            <SelectItem value="1">⭐ (No apto)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="inv-notes" className="text-[11px]">Feedback / Observaciones de la Evaluación</Label>
                      <Input
                        id="inv-notes"
                        placeholder="Excelentes conocimientos en React Hooks y SQL. Muy motivado..."
                        className="h-8 text-xs bg-card"
                        value={interviewForm.feedback_notes}
                        onChange={(e) => setInterviewForm({ ...interviewForm, feedback_notes: e.target.value })}
                      />
                    </div>

                    <div className="flex justify-end">
                      <Button
                        type="submit"
                        size="sm"
                        disabled={scheduleInterviewMutation.isPending}
                        className="gap-1 shadow-xs h-8 text-xs"
                      >
                        {scheduleInterviewMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />}
                        Agendar y Registrar Score
                      </Button>
                    </div>
                  </form>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Onboarding Wizard Dialog (Contratación Completa Española) */}
      <Dialog open={onboardOpen} onOpenChange={setOnboardOpen}>
        <DialogContent className="sm:max-w-xl max-h-screen overflow-y-auto pb-10">
          <DialogHeader className="pb-3 border-b">
            <DialogTitle className="text-xl font-bold flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-emerald-500" />
              Asistente de Contratación: {selectedCandidate?.first_name} {selectedCandidate?.last_name}
            </DialogTitle>
            <SheetDescription>
              Crea atómicamente la cuenta del empleado en el Centro de Personal, pre-poblando sus datos y configurando su cumplimiento bajo normativa española.
            </SheetDescription>
          </DialogHeader>

          {selectedCandidate && (
            <form onSubmit={handlePromoteSubmit} className="space-y-5 py-4">
              {/* Sección 1: Datos Personales Pre-poblados */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">
                  1. Perfil del Candidato (Importado)
                </h4>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs bg-muted/20 p-3 rounded-xl border">
                  <div>
                    <span className="text-muted-foreground">Nombre Completo:</span>
                    <p className="font-bold text-foreground">{selectedCandidate.first_name} {selectedCandidate.last_name}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Email de Candidato:</span>
                    <p className="font-bold text-foreground">{selectedCandidate.email}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="o-phone" className="text-xs">Teléfono Móvil</Label>
                    <Input
                      id="o-phone"
                      value={onboardForm.phone_number}
                      onChange={(e) => setOnboardForm({ ...onboardForm, phone_number: e.target.value })}
                      placeholder="Ej: +34 600000000"
                    />
                  </div>
                  
                  <div className="space-y-1.5">
                    <Label htmlFor="o-password" className="text-xs">Contraseña de Primer Acceso *</Label>
                    <Input
                      id="o-password"
                      required
                      placeholder="Mínimo 6 caracteres"
                      value={onboardForm.password}
                      onChange={(e) => setOnboardForm({ ...onboardForm, password: e.target.value })}
                    />
                    <p className="text-[10px] text-muted-foreground">
                      Se registrará en el sistema y se le enviará un correo automático.
                    </p>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="o-address" className="text-xs">Dirección Física de Residencia</Label>
                  <Input
                    id="o-address"
                    placeholder="Calle Alcalá 23, 4º C, 28014 Madrid"
                    value={onboardForm.address}
                    onChange={(e) => setOnboardForm({ ...onboardForm, address: e.target.value })}
                  />
                </div>
              </div>

              {/* Sección 2: Cumplimiento Laboral y Bancario (España) */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">
                  2. Configuración Laboral y de Nóminas (España)
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="o-contract" className="text-xs">Tipo de Contrato</Label>
                    <Select
                      value={onboardForm.contract_type}
                      onValueChange={(v) => setOnboardForm({ ...onboardForm, contract_type: v || "Indefinido" })}
                    >
                      <SelectTrigger id="o-contract" className="bg-card">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Indefinido">Indefinido (Ordinario)</SelectItem>
                        <SelectItem value="Temporal">Temporal</SelectItem>
                        <SelectItem value="Beca">Prácticas / Beca</SelectItem>
                        <SelectItem value="Autónomo">Autónomo / Freelance</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="o-hire" className="text-xs">Fecha de Incorporación</Label>
                    <Input
                      id="o-hire"
                      type="date"
                      value={onboardForm.hire_date}
                      onChange={(e) => setOnboardForm({ ...onboardForm, hire_date: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="o-salary" className="text-xs">Salario Base Anual (€)</Label>
                    <Input
                      id="o-salary"
                      type="number"
                      min="0"
                      value={onboardForm.base_salary}
                      onChange={(e) => setOnboardForm({ ...onboardForm, base_salary: parseFloat(e.target.value) || 0 })}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="o-ssn" className="text-xs">Nº de Seguridad Social (NUSS)</Label>
                    <Input
                      id="o-ssn"
                      placeholder="Ej: 281234567890"
                      value={onboardForm.social_security_number}
                      onChange={(e) => setOnboardForm({ ...onboardForm, social_security_number: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="o-iban" className="text-xs">IBAN Cuenta de Cobro</Label>
                    {onboardForm.iban && (
                      isIbanValid ? (
                        <span className="text-[10px] text-emerald-500 font-semibold flex items-center gap-0.5">
                          <CheckCircle2 className="w-3.5 h-3.5" /> IBAN Español Válido
                        </span>
                      ) : (
                        <span className="text-[10px] text-destructive font-semibold flex items-center gap-0.5">
                          <AlertCircle className="w-3.5 h-3.5" /> Formato ES + 22 dígitos
                        </span>
                      )
                    )}
                  </div>
                  <Input
                    id="o-iban"
                    placeholder="ES91 2100 0418 4502 0005 6789"
                    value={onboardForm.iban}
                    onChange={(e) => setOnboardForm({ ...onboardForm, iban: e.target.value })}
                    className={onboardForm.iban && !isIbanValid ? "border-destructive/80" : ""}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="o-role" className="text-xs">Rol en Sistema</Label>
                    <Select
                      value={onboardForm.role}
                      onValueChange={(v) => setOnboardForm({ ...onboardForm, role: v || "employee" })}
                    >
                      <SelectTrigger id="o-role" className="bg-card">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="employee">Empleado</SelectItem>
                        <SelectItem value="hr_admin">HR Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="o-country" className="text-xs">País Fiscal</Label>
                    <Input
                      id="o-country"
                      value={onboardForm.country}
                      onChange={(e) => setOnboardForm({ ...onboardForm, country: e.target.value.toUpperCase().slice(0, 2) })}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">
                  3. Onboarding Options
                </h4>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={onboardOptions.assign_onboarding_plan}
                      onChange={(e) => setOnboardOptions({ ...onboardOptions, assign_onboarding_plan: e.target.checked })}
                      className="rounded"
                    />
                    <span className="text-xs">Assign AI-generated onboarding plan</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={onboardOptions.enroll_in_training}
                      onChange={(e) => setOnboardOptions({ ...onboardOptions, enroll_in_training: e.target.checked })}
                      className="rounded"
                    />
                    <span className="text-xs">Auto-enroll in required training courses</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={onboardOptions.request_it_equipment}
                      onChange={(e) => setOnboardOptions({ ...onboardOptions, request_it_equipment: e.target.checked })}
                      className="rounded"
                    />
                    <span className="text-xs">Request IT equipment</span>
                  </label>
                  {onboardOptions.request_it_equipment && (
                    <div className="grid grid-cols-2 gap-3 ml-6 p-3 bg-muted/20 rounded-lg border">
                      <div className="space-y-1.5">
                        <Label className="text-[10px]">Hardware Type</Label>
                        <Select
                          value={onboardOptions.it_equipment_type}
                          onValueChange={(v) => setOnboardOptions({ ...onboardOptions, it_equipment_type: v ?? "" })}
                        >
                          <SelectTrigger className="h-8 text-xs bg-card">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="laptop">Laptop</SelectItem>
                            <SelectItem value="desktop">Desktop</SelectItem>
                            <SelectItem value="monitor">Monitor</SelectItem>
                            <SelectItem value="keyboard">Keyboard</SelectItem>
                            <SelectItem value="mouse">Mouse</SelectItem>
                            <SelectItem value="headset">Headset</SelectItem>
                            <SelectItem value="docking_station">Docking Station</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-[10px]">Quantity</Label>
                        <Input
                          type="number"
                          min="1"
                          max="10"
                          className="h-8 text-xs bg-card"
                          value={onboardOptions.it_equipment_quantity}
                          onChange={(e) => setOnboardOptions({ ...onboardOptions, it_equipment_quantity: parseInt(e.target.value) || 1 })}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-2 border-t">
                <Button type="button" variant="outline" onClick={() => setOnboardOpen(false)}>Cancelar</Button>
                <Button
                  type="submit"
                  disabled={promoteMutation.isPending || (!!onboardForm.iban && !isIbanValid)}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                >
                  {promoteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Dar de Alta en Plantilla Activa
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Scrollbar styling */}
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: rgba(156, 163, 175, 0.25);
          border-radius: 20px;
        }
      `}} />
    </div>
  );
}
