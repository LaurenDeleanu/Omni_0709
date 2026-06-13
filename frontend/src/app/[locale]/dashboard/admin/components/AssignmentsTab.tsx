"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AdminAPI } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Loader2, GraduationCap, CalendarClock, Activity, Send, CheckCircle2, Clock } from "lucide-react";
import { toast } from "sonner";

interface AssignmentsTabProps {
  users: any[];
  courses: any[];
  assignments: any;
  loadingUsers: boolean;
  loadingCourses: boolean;
  loadingAssignments: boolean;
}

export function AssignmentsTab({ users, courses, assignments, loadingUsers, loadingCourses, loadingAssignments }: AssignmentsTabProps) {
  const queryClient = useQueryClient();

  // Course assignment state
  const [selectedUsersForCourse, setSelectedUsersForCourse] = useState<string[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [searchCourses, setSearchCourses] = useState("");
  const [searchTasks, setSearchTasks] = useState("");

  // Task assignment state
  const [selectedUsersForTask, setSelectedUsersForTask] = useState<string[]>([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDesc, setTaskDesc] = useState("");
  const [taskDueDate, setTaskDueDate] = useState("");
  const [taskPriority, setTaskPriority] = useState("medium");

  const filteredCourses = assignments?.courses?.filter((c: any) =>
    c.employee_name?.toLowerCase().includes(searchCourses.toLowerCase()) ||
    c.course_title?.toLowerCase().includes(searchCourses.toLowerCase())
  );

  const filteredTasks = assignments?.tasks?.filter((t: any) =>
    t.employee_name?.toLowerCase().includes(searchTasks.toLowerCase()) ||
    t.title?.toLowerCase().includes(searchTasks.toLowerCase())
  );

  const assignCourseMutation = useMutation({
    mutationFn: (data: { user_ids: string[]; course_id: string }) => AdminAPI.assignCourse(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminAssignmentsStatus"] });
      setSelectedUsersForCourse([]);
      setSelectedCourse("");
      toast.success("Curso Asignado", { description: "El curso se asignó correctamente en lote." });
    },
    onError: () => toast.error("Error", { description: "No se pudo realizar la asignación de curso." }),
  });

  const assignTaskMutation = useMutation({
    mutationFn: (data: { user_ids: string[]; title: string; description?: string; due_date?: string; priority?: string }) => AdminAPI.assignTask(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminAssignmentsStatus"] });
      setSelectedUsersForTask([]);
      setTaskTitle("");
      setTaskDesc("");
      setTaskDueDate("");
      setTaskPriority("medium");
      toast.success("Tarea Asignada", { description: "La tarea se asignó correctamente en lote." });
    },
    onError: () => toast.error("Error", { description: "No se pudo realizar la asignación de tarea." }),
  });

  const handleAssignCourse = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourse || selectedUsersForCourse.length === 0) {
      toast.warning("Incompleto", { description: "Selecciona un curso y al menos un empleado." });
      return;
    }
    assignCourseMutation.mutate({ user_ids: selectedUsersForCourse, course_id: selectedCourse });
  };

  const handleAssignTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskTitle || selectedUsersForTask.length === 0) {
      toast.warning("Incompleto", { description: "Escribe un título y selecciona al menos un empleado." });
      return;
    }
    assignTaskMutation.mutate({
      user_ids: selectedUsersForTask,
      title: taskTitle,
      description: taskDesc,
      due_date: taskDueDate || undefined,
      priority: taskPriority,
    });
  };

  const handleUserSelectionForCourse = (userId: string) => {
    setSelectedUsersForCourse(prev => prev.includes(userId) ? prev.filter(id => id !== userId) : [...prev, userId]);
  };

  const handleUserSelectionForTask = (userId: string) => {
    setSelectedUsersForTask(prev => prev.includes(userId) ? prev.filter(id => id !== userId) : [...prev, userId]);
  };

  return (
    <div className="space-y-8">
      <div className="grid gap-6 md:grid-cols-2">
        {/* COURSE ASSIGNER */}
        <Card className="border border-border/50 bg-card/25 backdrop-blur-md shadow-md">
          <CardHeader>
            <CardTitle className="flex gap-2 items-center"><GraduationCap className="w-5 h-5 text-indigo-400 animate-bounce" /> Asignar Cursos en Lote</CardTitle>
            <CardDescription>Selecciona un curso formativo e inscríbelo simultáneamente a múltiples empleados.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAssignCourse} className="space-y-6">
              <div className="space-y-2.5">
                <Label htmlFor="courseSelect" className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Curso Formativo en Catálogo</Label>
                <select id="courseSelect" value={selectedCourse} onChange={(e) => setSelectedCourse(e.target.value)}
                  className="w-full rounded-md border border-border/80 bg-card/60 px-3 py-2 text-sm text-foreground focus:ring-1 focus:ring-primary focus:outline-none transition-colors">
                  <option value="">-- Selecciona un Curso --</option>
                  {courses?.map((c: any) => (
                    <option key={c.id} value={c.id}>{c.title} {c.is_fundae_eligible ? " (Bonificable FUNDAE)" : ""}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2.5">
                <Label className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Seleccionar Destinatarios</Label>
                <div className="max-h-[200px] overflow-y-auto border border-border/60 rounded-lg p-2.5 bg-card/30 space-y-2 shadow-inner">
                  {loadingUsers ? <div className="text-xs text-muted-foreground p-2">Cargando directorio...</div> :
                    users?.map((u: any) => (
                      <div key={u.id} className={`flex items-center space-x-3 px-3 py-2 rounded-md cursor-pointer transition-colors ${selectedUsersForCourse.includes(u.id) ? "bg-indigo-500/10 text-indigo-300" : "hover:bg-muted/30"}`}
                        onClick={() => handleUserSelectionForCourse(u.id)}>
                        <input type="checkbox" checked={selectedUsersForCourse.includes(u.id)} onChange={() => {}} className="rounded border-border text-primary focus:ring-primary w-4 h-4 cursor-pointer" />
                        <div className="text-xs flex-1 flex items-center justify-between">
                          <span className="font-semibold">{u.full_name}</span>
                          <span className="text-muted-foreground text-[10px] bg-card border px-2 py-0.5 rounded">{u.department || "General"}</span>
                        </div>
                      </div>
                    ))
                  }
                </div>
              </div>
              <Button type="submit" disabled={assignCourseMutation.isPending} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white transition-colors cursor-pointer shadow-md shadow-indigo-600/15">
                {assignCourseMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Send className="w-4 h-4 mr-2" /> Asignar Curso Formativo
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* TASK ASSIGNER */}
        <Card className="border border-border/50 bg-card/25 backdrop-blur-md shadow-md">
          <CardHeader>
            <CardTitle className="flex gap-2 items-center"><CalendarClock className="w-5 h-5 text-amber-400 animate-bounce" /> Asignar Tareas del Personal</CardTitle>
            <CardDescription>Crea una tarea corporativa del calendario y asígnala en lote.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAssignTask} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="taskTitle" className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Título de la Tarea</Label>
                  <Input id="taskTitle" placeholder="Ej: Firmar contrato o enviar tique" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} className="bg-card/60" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="taskDueDate" className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Fecha Limite</Label>
                  <Input id="taskDueDate" type="date" value={taskDueDate} onChange={(e) => setTaskDueDate(e.target.value)} className="bg-card/60 cursor-pointer" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="taskDesc" className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Instrucciones / Descripción</Label>
                <textarea id="taskDesc" rows={2} placeholder="Escribe aquí las pautas de realización de la tarea..." value={taskDesc} onChange={(e) => setTaskDesc(e.target.value)}
                  className="w-full rounded-md border border-border/80 bg-card/60 px-3 py-2 text-sm text-foreground focus:ring-1 focus:ring-primary focus:outline-none transition-colors" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="taskPriority" className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Prioridad</Label>
                  <select id="taskPriority" value={taskPriority} onChange={(e) => setTaskPriority(e.target.value)}
                    className="w-full rounded-md border border-border/80 bg-card/60 px-3 py-2 text-sm text-foreground focus:ring-1 focus:ring-primary focus:outline-none">
                    <option value="low">Baja</option>
                    <option value="medium">Media</option>
                    <option value="high">Alta</option>
                    <option value="urgent">Urgente</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Destinatarios</Label>
                  <div className="max-h-[105px] overflow-y-auto border border-border/60 rounded-lg p-1.5 bg-card/30 space-y-1 shadow-inner">
                    {loadingUsers ? <div className="text-xs text-muted-foreground p-1">Cargando directorio...</div> :
                      users?.map((u: any) => (
                        <div key={u.id} className={`flex items-center space-x-2 px-2 py-1 rounded cursor-pointer transition-colors ${selectedUsersForTask.includes(u.id) ? "bg-amber-500/10 text-amber-300" : "hover:bg-muted/30"}`}
                          onClick={() => handleUserSelectionForTask(u.id)}>
                          <input type="checkbox" checked={selectedUsersForTask.includes(u.id)} onChange={() => {}} className="rounded border-border text-primary focus:ring-primary w-3.5 h-3.5 cursor-pointer" />
                          <span className="text-xs font-semibold">{u.full_name}</span>
                        </div>
                      ))
                    }
                  </div>
                </div>
              </div>
              <Button type="submit" disabled={assignTaskMutation.isPending} className="w-full bg-amber-600 hover:bg-amber-700 text-white transition-colors cursor-pointer mt-2 shadow-md shadow-amber-600/15">
                {assignTaskMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Send className="w-4 h-4 mr-2" /> Asignar Tarea de Calendario
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* ASSIGNMENT MONITOR */}
      <Card className="border border-border/50 bg-card/25 backdrop-blur-md shadow-md">
        <CardHeader>
          <CardTitle className="text-lg font-bold flex gap-2 items-center"><Activity className="w-5 h-5 text-primary" /> Matriz de Monitoreo de Asignaciones</CardTitle>
          <CardDescription>Visualiza y supervisa el avance y el estado de cumplimiento en tiempo real.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Courses Matrix */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground px-1 flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-indigo-400" /> Cursos Matriculados</h3>
                <Input placeholder="Buscar curso o empleado..." className="h-7 text-xs w-[200px]" value={searchCourses} onChange={e => setSearchCourses(e.target.value)} />
              </div>
              <div className="border border-border/60 rounded-lg overflow-x-auto bg-card/20 max-h-[300px] overflow-y-auto shadow-inner">
                {loadingAssignments ? <div className="text-xs text-muted-foreground p-6 text-center">Cargando matriz formativa...</div> :
                  filteredCourses?.length === 0 ? <div className="text-xs text-muted-foreground p-6 text-center">Sin asignaciones formativas vigentes.</div> :
                    <table className="w-full text-xs text-left border-collapse">
                      <thead className="bg-muted/75 text-muted-foreground sticky top-0 border-b border-border/60">
                        <tr>
                          <th className="p-3 font-semibold uppercase tracking-wider">Empleado</th>
                          <th className="p-3 font-semibold uppercase tracking-wider">Curso</th>
                          <th className="p-3 text-right font-semibold uppercase tracking-wider">Progreso</th>
                          <th className="p-3 text-center font-semibold uppercase tracking-wider">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {filteredCourses?.map((c: any) => (
                          <tr key={c.enrollment_id} className="hover:bg-muted/20 transition-colors">
                            <td className="p-3 font-semibold text-foreground">{c.employee_name}</td>
                            <td className="p-3 text-muted-foreground">{c.course_title}</td>
                            <td className="p-3 text-right font-mono font-bold text-foreground/80">{c.progress.toFixed(0)}%</td>
                            <td className="p-3 text-center">
                              <span className={`px-2.5 py-0.5 rounded-full text-[10px] uppercase font-extrabold border ${c.status === "completed" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                                  c.status === "in_progress" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                                    "bg-blue-500/10 text-blue-400 border-blue-500/20"}`}>
                                {c.status === "completed" ? "completado" : c.status === "in_progress" ? "cursando" : "asignado"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                }
              </div>
            </div>

            {/* Tasks Matrix */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground px-1 flex items-center gap-1.5"><Clock className="w-4 h-4 text-amber-400" /> Tareas Asignadas</h3>
                <Input placeholder="Buscar tarea o empleado..." className="h-7 text-xs w-[200px]" value={searchTasks} onChange={e => setSearchTasks(e.target.value)} />
              </div>
              <div className="border border-border/60 rounded-lg overflow-x-auto bg-card/20 max-h-[300px] overflow-y-auto shadow-inner">
                {loadingAssignments ? <div className="text-xs text-muted-foreground p-6 text-center">Cargando matriz de tareas...</div> :
                  filteredTasks?.length === 0 ? <div className="text-xs text-muted-foreground p-6 text-center">Sin tareas asignadas vigentes.</div> :
                    <table className="w-full text-xs text-left border-collapse">
                      <thead className="bg-muted/75 text-muted-foreground sticky top-0 border-b border-border/60">
                        <tr>
                          <th className="p-3 font-semibold uppercase tracking-wider">Empleado</th>
                          <th className="p-3 font-semibold uppercase tracking-wider">Título</th>
                          <th className="p-3 font-semibold uppercase tracking-wider">Prioridad</th>
                          <th className="p-3 text-center font-semibold uppercase tracking-wider">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {filteredTasks?.map((t: any) => (
                          <tr key={t.task_id} className="hover:bg-muted/20 transition-colors">
                            <td className="p-3 font-semibold text-foreground">{t.employee_name}</td>
                            <td className="p-3 text-muted-foreground truncate max-w-[140px]">{t.title}</td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-black border ${t.priority === "urgent" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                                  t.priority === "high" ? "bg-orange-500/10 text-orange-400 border-orange-500/20" :
                                    t.priority === "medium" ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" :
                                      "bg-blue-500/10 text-blue-400 border-blue-500/20"}`}>
                                {t.priority === "urgent" ? "urgente" : t.priority === "high" ? "alta" : t.priority === "medium" ? "media" : "baja"}
                              </span>
                            </td>
                            <td className="p-3 text-center">
                              <span className={`px-2.5 py-0.5 rounded-full text-[10px] uppercase font-extrabold border ${t.status === "done" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                                  t.status === "in_progress" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                                    "bg-red-500/10 text-red-400 border-red-500/20"}`}>
                                {t.status === "done" ? "completado" : t.status === "in_progress" ? "en curso" : "pendiente"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                }
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
