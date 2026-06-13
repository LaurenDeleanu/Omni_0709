"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HireAPI, JobPosting } from "@/lib/api";
import { Plus, Briefcase, Users, MapPin, Building, ChevronRight } from "lucide-react";
import { Link } from "@/i18n/routing";
import { useState } from "react";

// Using basic shadcn/ui components (assuming they are installed or we use standard HTML fallback if not)
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { InlineCopilot } from "@/components/ai/InlineCopilot";
import { ScorecardBuilder } from "@/components/hire/ScorecardBuilder";
import { TalentCRM } from "@/components/hire/TalentCRM";
import { JobBoard } from "@/components/hire/JobBoard";
import { InterviewScheduler } from "@/components/hire/InterviewScheduler";
import { CandidatePoolManager } from "@/components/hire/CandidatePoolManager";
import { PageHeader } from "@/components/layout/PageHeader";

export default function HireDashboard() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: jobs, isLoading } = useQuery({
    queryKey: ["hireJobs"],
    queryFn: HireAPI.getJobs,
  });

  const createJobMutation = useMutation({
    mutationFn: HireAPI.createJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hireJobs"] });
      setIsModalOpen(false);
    },
  });

  const handleCreateJob = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createJobMutation.mutate({
      title: formData.get("title") as string,
      department: formData.get("department") as string,
      location: formData.get("location") as string,
      employment_type: formData.get("employment_type") as string,
      description: formData.get("description") as string,
    });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <PageHeader
        title="Reclutamiento"
        description="Gestiona vacantes y rastrea candidatos a través de tu proceso de selección (ATS)."
        action={
          <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
            <DialogTrigger render={<Button className="gap-2" />}>
                <Plus className="h-4 w-4" />
                Nueva Vacante
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">

            <DialogHeader>
              <DialogTitle>Crear Nueva Vacante</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateJob} className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="title">Título del Puesto</Label>
                <Input id="title" name="title" required placeholder="Ej: Senior Software Engineer" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="department">Departamento</Label>
                  <Input id="department" name="department" placeholder="Ej: Ingeniería" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="location">Ubicación</Label>
                  <Input id="location" name="location" placeholder="Ej: Remoto / Madrid" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="employment_type">Tipo de Contrato</Label>
                <Input id="employment_type" name="employment_type" placeholder="Ej: Tiempo Completo" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Descripción (Opcional)</Label>
                <Textarea id="description" name="description" placeholder="Responsabilidades, requisitos..." className="h-24" />
              </div>
              <div className="pt-4 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={createJobMutation.isPending}>
                  {createJobMutation.isPending ? "Creando..." : "Crear Vacante"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
        }
      />

      <InlineCopilot
        moduleContext="hire"
        placeholder="Pregunta sobre candidatos o vacantes..."
        quickActions={[
          { label: "Mostrar candidatos activos", message: "Mostrar candidatos activos" },
          { label: "Analizar pipeline de vacantes", message: "Analizar pipeline de vacantes" },
          { label: "Sugerir perfiles para nueva vacante", message: "Sugerir perfiles para nueva vacante" },
          { label: "Resumir estado del ATS", message: "Resumir estado del ATS" },
        ]}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          Array(3).fill(0).map((_, i) => (
            <div key={i} className="h-48 rounded-xl border border-border bg-card/50 animate-pulse" />
          ))
        ) : jobs?.length === 0 ? (
          <div className="col-span-full py-12 text-center border border-dashed rounded-xl border-border bg-card/30">
            <Briefcase className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" />
            <h3 className="text-lg font-medium">No hay vacantes abiertas</h3>
            <p className="text-muted-foreground text-sm mt-1 mb-4">Comienza creando tu primer anuncio de trabajo.</p>
            <Button variant="outline" onClick={() => setIsModalOpen(true)}>Crear Vacante</Button>
          </div>
        ) : (
          jobs?.map((job: JobPosting) => (
            <Link key={job.id} href={`/dashboard/hire/${job.id}`}>
              <div className="group bg-card border border-border hover:border-primary/50 transition-all rounded-xl p-6 h-full flex flex-col hover:shadow-md cursor-pointer">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-semibold text-lg line-clamp-2 group-hover:text-primary transition-colors">{job.title}</h3>
                  <div className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
                    job.status === 'open' ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' : 
                    job.status === 'draft' ? 'bg-amber-500/10 text-amber-600 border-amber-500/20' : 
                    'bg-slate-500/10 text-slate-600 border-slate-500/20'
                  }`}>
                    {job.status === 'open' ? 'Abierta' : job.status}
                  </div>
                </div>

                <div className="space-y-2 mt-auto">
                  {job.department && (
                    <div className="flex items-center text-sm text-muted-foreground gap-2">
                      <Building className="w-4 h-4" />
                      <span>{job.department}</span>
                    </div>
                  )}
                  {job.location && (
                    <div className="flex items-center text-sm text-muted-foreground gap-2">
                      <MapPin className="w-4 h-4" />
                      <span>{job.location}</span>
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-border/60 flex items-center justify-between">
                  <div className="flex items-center text-sm font-medium text-foreground gap-2">
                    <div className="bg-primary/10 p-1.5 rounded-md text-primary">
                      <Users className="w-4 h-4" />
                    </div>
                    <span>{job.candidate_count || 0} Candidatos</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            </Link>
          ))
        )}
      </div>

      <ScorecardBuilder />

      <TalentCRM />

      <CandidatePoolManager />

      <JobBoard />

      <InterviewScheduler />
    </div>
  );
}
