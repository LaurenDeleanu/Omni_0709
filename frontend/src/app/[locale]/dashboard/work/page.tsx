"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { WorkAPI, Project } from "@/lib/api";
import { Plus, Briefcase, Calendar, CheckCircle2, CircleDashed, Clock, ChevronRight, MoreHorizontal } from "lucide-react";
import { Link } from "@/i18n/routing";
import { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function ProjectsHub() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedProjectForEdit, setSelectedProjectForEdit] = useState<Project | null>(null);
  
  // Edit form states
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editBudget, setEditBudget] = useState(0);
  const [editStatus, setEditStatus] = useState("planning");

  const { data: projects, isLoading } = useQuery<Project[]>({
    queryKey: ["workProjects"],
    queryFn: WorkAPI.getProjects,
  });

  const createProjectMutation = useMutation<Project, Error, Partial<Project>>({
    mutationFn: WorkAPI.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workProjects"] });
      setIsModalOpen(false);
      toast.success("Proyecto creado con éxito");
    },
  });

  const updateProjectMutation = useMutation<Project, Error, { id: string; data: Partial<Project> }>({
    mutationFn: ({ id, data }) => WorkAPI.updateProject(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workProjects"] });
      setIsEditOpen(false);
      toast.success("Proyecto actualizado");
    }
  });

  const deleteProjectMutation = useMutation<any, Error, string>({
    mutationFn: (id: string) => WorkAPI.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workProjects"] });
      setIsEditOpen(false);
      toast.success("Proyecto eliminado");
    }
  });

  const handleCreateProject = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createProjectMutation.mutate({
      name: formData.get("name") as string,
      description: formData.get("description") as string,
      budget: parseFloat(formData.get("budget") as string) || 0,
      status: "planning",
    });
  };

  const handleEditProject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectForEdit) return;
    updateProjectMutation.mutate({
      id: selectedProjectForEdit.id,
      data: {
        name: editName,
        description: editDesc,
        budget: editBudget,
        status: editStatus,
      }
    });
  };

  const handleDeleteProject = (id: string) => {
    if (confirm("¿Seguro de que deseas eliminar este proyecto y todas sus tareas de forma permanente?")) {
      deleteProjectMutation.mutate(id);
    }
  };

  const getStatusBadge = (status: string) => {
    switch(status) {
      case 'active': return <span className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5"><CircleDashed className="w-3.5 h-3.5 animate-spin-slow" /> Activo</span>;
      case 'completed': return <span className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5" /> Completado</span>;
      case 'on_hold': return <span className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> En Pausa</span>;
      default: return <span className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5">Planificación</span>;
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Proyectos & Tareas</h1>
          <p className="text-muted-foreground mt-1">
            Gestiona la ejecución de proyectos, asigna tareas al equipo y haz seguimiento de entregables.
          </p>
        </div>

        <InlineCopilot
          moduleContext="projects"
          placeholder="Pregunta sobre proyectos o tareas..."
          quickActions={[
            { label: "Resumir estado de proyectos", message: "Resumir estado de proyectos" },
            { label: "Identificar proyectos bloqueados", message: "Identificar proyectos bloqueados" },
            { label: "Analizar carga del equipo", message: "Analizar carga del equipo" },
            { label: "Sugerir prioridades semanales", message: "Sugerir prioridades semanales" },
          ]}
        />

        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogTrigger render={<Button className="gap-2" />}>
              <Plus className="h-4 w-4" />
              Nuevo Proyecto
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Crear Nuevo Proyecto</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateProject} className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre del Proyecto</Label>
                <Input id="name" name="name" required placeholder="Ej: Migración Cloud Q3" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Descripción</Label>
                <Textarea id="description" name="description" placeholder="Objetivos y alcance del proyecto..." className="h-24" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="budget">Presupuesto Asignado ($)</Label>
                <Input id="budget" name="budget" type="number" min="0" defaultValue="0" />
              </div>
              <div className="pt-4 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={createProjectMutation.isPending}>
                  {createProjectMutation.isPending ? "Creando..." : "Crear Proyecto"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {isLoading ? (
          Array(4).fill(0).map((_, i) => (
            <div key={i} className="h-48 rounded-xl border border-border bg-card/50 animate-pulse" />
          ))
        ) : projects?.length === 0 ? (
          <div className="col-span-full py-16 text-center border border-dashed rounded-xl border-border bg-card/30">
            <Briefcase className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" />
            <h3 className="text-lg font-medium">No hay proyectos activos</h3>
            <p className="text-muted-foreground text-sm mt-1 mb-4">Comienza creando tu primer proyecto para el equipo.</p>
            <Button variant="outline" onClick={() => setIsModalOpen(true)}>Crear Proyecto</Button>
          </div>
        ) : (
          projects?.map((project: Project) => (
            <Link key={project.id} href={`/dashboard/work/${project.id}`}>
              <div className="group bg-card border border-border hover:border-primary/50 transition-all rounded-xl p-5 h-full flex flex-col hover:shadow-lg cursor-pointer relative">
                <div className="flex justify-between items-center mb-3">
                  {getStatusBadge(project.status)}
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-8 w-8 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity z-10"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setSelectedProjectForEdit(project);
                      setEditName(project.name);
                      setEditDesc(project.description || "");
                      setEditBudget(project.budget);
                      setEditStatus(project.status);
                      setIsEditOpen(true);
                    }}
                  >
                    <MoreHorizontal className="w-4 h-4" />
                  </Button>
                </div>
                
                <h3 className="font-bold text-lg leading-tight group-hover:text-primary transition-colors mb-2">
                  {project.name}
                </h3>
                
                {project.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                    {project.description}
                  </p>
                )}

                <div className="mt-auto space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center text-muted-foreground gap-1.5">
                      <Calendar className="w-4 h-4" />
                      <span>{new Date(project.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="font-semibold text-foreground">
                      ${project.budget.toLocaleString()}
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-border/60 flex items-center justify-between text-sm font-medium">
                    <span className="text-muted-foreground group-hover:text-foreground transition-colors">Ver Tablero</span>
                    <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </div>
            </Link>
          ))
        )}
      </div>

      {/* DIALOG: EDIT/DELETE PROJECT */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Editar Detalles del Proyecto</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditProject} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Nombre del Proyecto</Label>
              <Input id="edit-name" value={editName} onChange={e => setEditName(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-desc">Descripción</Label>
              <Textarea id="edit-desc" value={editDesc} onChange={e => setEditDesc(e.target.value)} className="h-24" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-budget">Presupuesto ($)</Label>
                <Input id="edit-budget" type="number" min="0" value={editBudget} onChange={e => setEditBudget(parseFloat(e.target.value) || 0)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-status">Estado</Label>
                <select 
                  id="edit-status" 
                  value={editStatus} 
                  onChange={e => setEditStatus(e.target.value)}
                  className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="planning">Planificación</option>
                  <option value="active">Activo</option>
                  <option value="on_hold">En Pausa</option>
                  <option value="completed">Completado</option>
                </select>
              </div>
            </div>
            
            <div className="pt-4 flex justify-between gap-2 border-t border-border mt-4">
              <Button type="button" variant="destructive" onClick={() => selectedProjectForEdit && handleDeleteProject(selectedProjectForEdit.id)} disabled={deleteProjectMutation.isPending}>
                Eliminar Proyecto
              </Button>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setIsEditOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={updateProjectMutation.isPending}>
                  {updateProjectMutation.isPending ? "Guardando..." : "Guardar Cambios"}
                </Button>
              </div>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
