"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { WorkAPI, Task, KanbanBoard, WikiPage, Project } from "@/lib/api";
import { Plus, ArrowLeft, MoreHorizontal, Calendar, AlignLeft, BookOpen, LayoutDashboard, Edit, Trash } from "lucide-react";
import { Link } from "@/i18n/routing";
import { useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const TASK_STAGES = [
  { id: "todo", name: "To Do", color: "bg-slate-100 dark:bg-slate-800/50", border: "border-slate-200 dark:border-slate-700" },
  { id: "in_progress", name: "In Progress", color: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-200 dark:border-blue-800" },
  { id: "review", name: "Review", color: "bg-purple-50 dark:bg-purple-900/20", border: "border-purple-200 dark:border-purple-800" },
  { id: "done", name: "Done", color: "bg-emerald-50 dark:bg-emerald-900/20", border: "border-emerald-200 dark:border-emerald-800" },
];

export default function ProjectWorkspace() {
  const params = useParams();
  const projectId = params.projectId as string;
  const [activeTab, setActiveTab] = useState("kanban");

  // Fetch project details
  const { data: projects, isLoading: isLoadingProjects } = useQuery<Project[]>({
    queryKey: ["workProjects"],
    queryFn: WorkAPI.getProjects,
  });
  const project = projects?.find((p: Project) => p.id === projectId);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="h-auto border-b border-border bg-card/50 backdrop-blur-xl shrink-0">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard/work" className="p-2 hover:bg-muted rounded-full transition-colors text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold">{isLoadingProjects ? "Cargando..." : project?.name}</h1>
              <p className="text-xs text-muted-foreground line-clamp-1 max-w-md">
                {project?.description || "Espacio de trabajo del proyecto"}
              </p>
            </div>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="px-6 flex gap-6">
          <button
            onClick={() => setActiveTab("kanban")}
            className={`flex items-center gap-2 pb-3 px-1 text-sm font-semibold border-b-2 transition-all ${
              activeTab === "kanban" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground/80"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" /> Kanban Board
          </button>
          <button
            onClick={() => setActiveTab("wiki")}
            className={`flex items-center gap-2 pb-3 px-1 text-sm font-semibold border-b-2 transition-all ${
              activeTab === "wiki" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground/80"
            }`}
          >
            <BookOpen className="w-4 h-4" /> Wiki & Docs
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === "kanban" && <KanbanTab projectId={projectId} />}
        {activeTab === "wiki" && <WikiTab projectId={projectId} />}
      </div>
    </div>
  );
}

function KanbanTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditTaskOpen, setIsEditTaskOpen] = useState(false);
  const [selectedTaskForEdit, setSelectedTaskForEdit] = useState<Task | null>(null);

  // Edit task form states
  const [editTaskTitle, setEditTaskTitle] = useState("");
  const [editTaskDesc, setEditTaskDesc] = useState("");
  const [editTaskPriority, setEditTaskPriority] = useState("medium");

  const { data: tasks, isLoading: isLoadingTasks } = useQuery<Task[]>({
    queryKey: ["workTasks", projectId],
    queryFn: () => WorkAPI.getTasks(projectId),
  });

  const createTaskMutation = useMutation<Task, Error, Partial<Task>>({
    mutationFn: WorkAPI.createTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workTasks", projectId] });
      setIsModalOpen(false);
      toast.success("Tarea creada");
    },
  });

  const updateTaskMutation = useMutation<Task, Error, { id: string; data: Partial<Task> }>({
    mutationFn: ({ id, data }) => WorkAPI.updateTask(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workTasks", projectId] });
      setIsEditTaskOpen(false);
      toast.success("Tarea actualizada");
    }
  });

  const deleteTaskMutation = useMutation<any, Error, string>({
    mutationFn: (id: string) => WorkAPI.deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workTasks", projectId] });
      setIsEditTaskOpen(false);
      toast.success("Tarea eliminada");
    }
  });

  const updateTaskStatusMutation = useMutation<any, Error, { id: string; status: string }>({
    mutationFn: ({ id, status }) => WorkAPI.moveTask(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workTasks", projectId] });
    },
  });

  const handleCreateTask = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createTaskMutation.mutate({
      project_id: projectId,
      title: formData.get("title") as string,
      description: formData.get("description") as string,
      priority: formData.get("priority") as string,
      status: "todo",
    });
  };

  const handleEditTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTaskForEdit) return;
    updateTaskMutation.mutate({
      id: selectedTaskForEdit.id,
      data: {
        title: editTaskTitle,
        description: editTaskDesc,
        priority: editTaskPriority,
      }
    });
  };

  const handleDeleteTask = (id: string) => {
    if (confirm("¿Estás seguro de que deseas eliminar esta tarea?")) {
      deleteTaskMutation.mutate(id);
    }
  };

  const onDragStart = (e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData("taskId", taskId);
  };

  const onDragOver = (e: React.DragEvent) => e.preventDefault();

  const onDrop = (e: React.DragEvent, statusId: string) => {
    const taskId = e.dataTransfer.getData("taskId");
    if (taskId) {
      updateTaskStatusMutation.mutate({ id: taskId, status: statusId });
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-500 bg-red-500/10';
      case 'medium': return 'text-amber-500 bg-amber-500/10';
      case 'low': return 'text-blue-500 bg-blue-500/10';
      default: return 'text-slate-500 bg-slate-500/10';
    }
  };

  return (
    <div className="h-full flex flex-col bg-muted/10">
      <div className="p-4 flex justify-end">
        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogTrigger render={
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Nueva Tarea
            </Button>
          } />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Añadir Tarea al Sprint</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateTask} className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="title">Título de la Tarea</Label>
                <Input id="title" name="title" required placeholder="Ej: Diseñar wireframes" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Descripción</Label>
                <Textarea id="description" name="description" placeholder="Detalles, criterios de aceptación..." />
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority">Prioridad</Label>
                <select id="priority" name="priority" className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                  <option value="low">Baja</option>
                  <option value="medium">Media</option>
                  <option value="high">Alta</option>
                </select>
              </div>
              <div className="pt-4 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={createTaskMutation.isPending}>
                  {createTaskMutation.isPending ? "Guardando..." : "Crear Tarea"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6 pt-0">
        <div className="flex gap-6 h-full items-start w-max min-w-full">
          {TASK_STAGES.map((stage) => {
            const stageTasks = tasks?.filter((t: Task) => t.status === stage.id) || [];
            
            return (
              <div 
                key={stage.id} 
                className={`flex flex-col w-80 h-full max-h-full rounded-xl border ${stage.border} ${stage.color} p-3 shrink-0 transition-colors`}
                onDragOver={onDragOver}
                onDrop={(e) => onDrop(e, stage.id)}
              >
                <div className="flex items-center justify-between mb-4 px-2 pt-1">
                  <h3 className="font-semibold text-sm uppercase tracking-wider text-foreground/80">{stage.name}</h3>
                  <span className="bg-background text-muted-foreground text-xs font-medium py-0.5 px-2.5 rounded-full border border-border shadow-sm">
                    {stageTasks.length}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto space-y-3 pb-2 custom-scrollbar pr-1">
                  {stageTasks.map((task: Task) => (
                    <div 
                      key={task.id} 
                      draggable
                      onDragStart={(e) => onDragStart(e, task.id)}
                      className="bg-card border border-border/80 rounded-lg p-4 shadow-sm hover:border-primary/40 hover:shadow-md transition-all cursor-grab active:cursor-grabbing group relative"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider w-fit mb-2 ${getPriorityColor(task.priority)}`}>
                          {task.priority}
                        </div>
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTaskForEdit(task);
                            setEditTaskTitle(task.title);
                            setEditTaskDesc(task.description || "");
                            setEditTaskPriority(task.priority);
                            setIsEditTaskOpen(true);
                          }}
                          className="text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </div>
                      
                      <h4 className="font-medium text-sm text-foreground mb-2 leading-tight">{task.title}</h4>
                      
                      {task.description && (
                        <div className="flex items-start gap-1.5 text-xs text-muted-foreground mb-3 line-clamp-2">
                          <AlignLeft className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                          <span>{task.description}</span>
                        </div>
                      )}

                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/50">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Calendar className="w-3.5 h-3.5" />
                          <span>{new Date(task.created_at).toLocaleDateString()}</span>
                        </div>
                        <div className="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold border border-primary/30">
                          UN
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {stageTasks.length === 0 && !isLoadingTasks && (
                    <div className="h-24 rounded-lg border-2 border-dashed border-border/60 flex items-center justify-center text-xs text-muted-foreground/60">
                      Arrastra tareas aquí
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* DIALOG: EDIT/DELETE TASK */}
      <Dialog open={isEditTaskOpen} onOpenChange={setIsEditTaskOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Detalles de la Tarea</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditTask} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-task-title">Título de la Tarea</Label>
              <Input id="edit-task-title" value={editTaskTitle} onChange={e => setEditTaskTitle(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-task-desc">Descripción</Label>
              <Textarea id="edit-task-desc" value={editTaskDesc} onChange={e => setEditTaskDesc(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-task-priority">Prioridad</Label>
              <select 
                id="edit-task-priority" 
                value={editTaskPriority} 
                onChange={e => setEditTaskPriority(e.target.value)}
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="low">Baja</option>
                <option value="medium">Media</option>
                <option value="high">Alta</option>
              </select>
            </div>
            <div className="pt-4 flex justify-between gap-2 border-t border-border mt-4">
              <Button type="button" variant="destructive" onClick={() => selectedTaskForEdit && handleDeleteTask(selectedTaskForEdit.id)} disabled={deleteTaskMutation.isPending}>
                Eliminar Tarea
              </Button>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setIsEditTaskOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={updateTaskMutation.isPending}>
                  {updateTaskMutation.isPending ? "Guardando..." : "Guardar Cambios"}
                </Button>
              </div>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function WikiTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedPage, setSelectedPage] = useState<WikiPage | null>(null);

  // Wiki Edit States
  const [isWikiEditMode, setIsWikiEditMode] = useState(false);
  const [editWikiTitle, setEditWikiTitle] = useState("");
  const [editWikiContent, setEditWikiContent] = useState("");

  const { data: pages, isLoading } = useQuery<WikiPage[]>({
    queryKey: ["wikiPages", projectId],
    queryFn: () => WorkAPI.getWikiPages(projectId),
  });

  const createPageMutation = useMutation<WikiPage, Error, Partial<WikiPage>>({
    mutationFn: WorkAPI.createWikiPage,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["wikiPages", projectId] });
      setIsModalOpen(false);
      setSelectedPage(data as WikiPage);
      toast.success("Documento wiki creado");
    },
  });

  const updateWikiPageMutation = useMutation<WikiPage, Error, { id: string; data: Partial<WikiPage> }>({
    mutationFn: ({ id, data }) => WorkAPI.updateWikiPage(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["wikiPages", projectId] });
      setIsWikiEditMode(false);
      setSelectedPage(data as WikiPage);
      toast.success("Documento wiki actualizado");
    }
  });

  const deleteWikiPageMutation = useMutation<any, Error, string>({
    mutationFn: (id: string) => WorkAPI.deleteWikiPage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wikiPages", projectId] });
      setSelectedPage(null);
      toast.success("Documento wiki eliminado");
    }
  });

  const handleCreatePage = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createPageMutation.mutate({
      project_id: projectId,
      title: formData.get("title") as string,
      content: formData.get("content") as string,
    });
  };

  const handleUpdateWikiPage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPage) return;
    updateWikiPageMutation.mutate({
      id: selectedPage.id,
      data: {
        title: editWikiTitle,
        content: editWikiContent
      }
    });
  };

  const handleDeleteWikiPage = (id: string) => {
    if (confirm("¿Estás seguro de que deseas eliminar esta página Wiki de forma permanente?")) {
      deleteWikiPageMutation.mutate(id);
    }
  };

  return (
    <div className="h-full flex overflow-hidden">
      {/* Sidebar List */}
      <div className="w-64 border-r border-border bg-card/30 flex flex-col">
        <div className="p-4 border-b border-border flex justify-between items-center">
          <h3 className="font-semibold text-sm">Páginas</h3>
          <Button variant="ghost" size="icon" onClick={() => setIsModalOpen(true)}>
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoading ? (
            <div className="p-4 text-xs text-muted-foreground text-center">Cargando...</div>
          ) : pages?.length === 0 ? (
            <div className="p-4 text-xs text-muted-foreground text-center">No hay páginas.</div>
          ) : (
            pages?.map((page: WikiPage) => (
              <button
                key={page.id}
                onClick={() => {
                  setSelectedPage(page);
                  setIsWikiEditMode(false);
                }}
                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                  selectedPage?.id === page.id ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                }`}
              >
                {page.title}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Editor/Viewer */}
      <div className="flex-1 overflow-y-auto p-8 bg-background">
        {selectedPage ? (
          isWikiEditMode ? (
            <form onSubmit={handleUpdateWikiPage} className="max-w-3xl mx-auto space-y-4">
              <div className="space-y-2">
                <Label>Título del Documento</Label>
                <Input value={editWikiTitle} onChange={e => setEditWikiTitle(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label>Contenido (Markdown)</Label>
                <Textarea value={editWikiContent} onChange={e => setEditWikiContent(e.target.value)} className="h-[450px] font-mono text-sm" required />
              </div>
              <div className="flex gap-2 justify-end">
                <Button type="button" variant="outline" onClick={() => setIsWikiEditMode(false)}>Cancelar</Button>
                <Button type="submit" disabled={updateWikiPageMutation.isPending}>Guardar Cambios</Button>
              </div>
            </form>
          ) : (
            <div className="max-w-3xl mx-auto">
              <div className="flex justify-between items-center border-b border-border pb-4 mb-6">
                <h1 className="text-3xl font-bold">{selectedPage.title}</h1>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => {
                      setIsWikiEditMode(true);
                      setEditWikiTitle(selectedPage.title);
                      setEditWikiContent(selectedPage.content || "");
                    }}
                  >
                    <Edit className="w-4 h-4 mr-2" /> Editar
                  </Button>
                  <Button 
                    variant="destructive" 
                    size="sm"
                    onClick={() => handleDeleteWikiPage(selectedPage.id)}
                    disabled={deleteWikiPageMutation.isPending}
                  >
                    <Trash className="w-4 h-4 mr-2" /> Eliminar
                  </Button>
                </div>
              </div>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                {selectedPage.content ? (
                  <div className="whitespace-pre-wrap text-foreground leading-relaxed text-sm bg-muted/20 p-6 rounded-xl border border-border/50">{selectedPage.content}</div>
                ) : (
                  <p className="text-muted-foreground italic">Página vacía.</p>
                )}
              </div>
            </div>
          )
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <BookOpen className="w-12 h-12 mb-4 opacity-20" />
            <p>Selecciona o crea una página wiki</p>
          </div>
        )}
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[700px]">
          <DialogHeader>
            <DialogTitle>Nueva Página Wiki</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreatePage} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Título de la Página</Label>
              <Input name="title" required placeholder="Ej: Arquitectura del Sistema" />
            </div>
            <div className="space-y-2">
              <Label>Contenido (Markdown)</Label>
              <Textarea name="content" className="h-64 font-mono text-sm" placeholder="# Escribe aquí tu documentación..." />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={createPageMutation.isPending}>Guardar Página</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
