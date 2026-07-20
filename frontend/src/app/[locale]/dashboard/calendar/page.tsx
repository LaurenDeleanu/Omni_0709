"use client";

import { useState, useEffect } from "react";
import {
  CalendarAPI,
  UserAPI,
  Employee,
  CalendarEvent,
  VacationRequest,
  Meeting,
  Task
} from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Clock,
  Plus,
  Trash2,
  CheckCircle2,
  Circle,
  AlertCircle,
  User,
  MapPin,
  ListTodo,
  Sparkles
} from "lucide-react";
import { toast } from "sonner";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"vacations" | "meetings" | "tasks">("vacations");

  // Forms states
  const [vacationStart, setVacationStart] = useState("");
  const [vacationEnd, setVacationEnd] = useState("");
  const [vacationReason, setVacationReason] = useState("");

  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDesc, setMeetingDesc] = useState("");
  const [meetingStart, setMeetingStart] = useState("");
  const [meetingEnd, setMeetingEnd] = useState("");
  const [meetingLocation, setMeetingLocation] = useState("");
  const [meetingAttendees, setMeetingAttendees] = useState<string[]>([]);

  const [taskTitle, setTaskTitle] = useState("");
  const [taskDesc, setTaskDesc] = useState("");
  const [taskAssignee, setTaskAssignee] = useState("");
  const [taskDueDate, setTaskDueDate] = useState("");
  const [taskPriority, setTaskPriority] = useState<"low" | "medium" | "high" | "urgent">("medium");

  const [currentUserRole, setCurrentUserRole] = useState("employee");
  const [currentUserId, setCurrentUserId] = useState("");

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const monthNames = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
  ];

  const daysOfWeek = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

  useEffect(() => {
    // Fetch user details from localStorage (mock login state)
    if (typeof window !== "undefined") {
      const localUserStr = localStorage.getItem("local_user");
      if (localUserStr) {
        try {
          const localUser = JSON.parse(localUserStr);
          setCurrentUserRole(localUser.role || "employee");
          setCurrentUserId(localUser.id || "");
        } catch (e) {
          // fallback defaults
        }
      }
    }

    loadData();
  }, [currentDate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const monthStr = `${year}-${String(month + 1).padStart(2, "0")}`;
      const [eventsData, employeesData] = await Promise.all([
        CalendarAPI.getEvents(monthStr),
        UserAPI.getEmployees()
      ]);
      setEvents(eventsData);
      setEmployees(employeesData);
    } catch (error) {
      console.error(error);
      toast.error("Error al cargar los datos del calendario");
    } finally {
      setLoading(false);
    }
  };

  // Calendar Math
  const getDaysInMonth = (y: number, m: number) => new Date(y, m + 1, 0).getDate();
  const getFirstDayOfMonth = (y: number, m: number) => {
    const day = new Date(y, m, 1).getDay();
    return day === 0 ? 6 : day - 1; // Monday indexed
  };

  const daysInMonth = getDaysInMonth(year, month);
  const firstDayIndex = getFirstDayOfMonth(year, month);

  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const isToday = (d: number) => {
    const today = new Date();
    return today.getDate() === d && today.getMonth() === month && today.getFullYear() === year;
  };

  const isSelected = (d: number) => {
    return selectedDate.getDate() === d && selectedDate.getMonth() === month && selectedDate.getFullYear() === year;
  };

  // Event handlers
  const handleSelectDay = (day: number) => {
    setSelectedDate(new Date(year, month, day));
  };

  const getEventsForDay = (day: number) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return events.filter(e => e.start.startsWith(dateStr));
  };

  const getSelectedDayEvents = () => {
    const dStr = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, "0")}-${String(selectedDate.getDate()).padStart(2, "0")}`;
    return events.filter(e => e.start.startsWith(dStr));
  };

  // Submissions
  const handleRequestVacation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vacationStart || !vacationEnd) {
      toast.error("Por favor, selecciona las fechas");
      return;
    }
    try {
      await CalendarAPI.createVacation({
        start_date: vacationStart,
        end_date: vacationEnd,
        reason: vacationReason
      });
      toast.success("Solicitud de vacaciones enviada con éxito");
      setVacationStart("");
      setVacationEnd("");
      setVacationReason("");
      loadData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Error al solicitar vacaciones");
    }
  };

  const handleCreateMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!meetingTitle || !meetingStart || !meetingEnd) {
      toast.error("Completa los campos obligatorios");
      return;
    }
    try {
      await CalendarAPI.createMeeting({
        title: meetingTitle,
        description: meetingDesc,
        start_datetime: meetingStart,
        end_datetime: meetingEnd,
        location: meetingLocation,
        attendees: meetingAttendees
      });
      toast.success("Reunión programada con éxito");
      setMeetingTitle("");
      setMeetingDesc("");
      setMeetingStart("");
      setMeetingEnd("");
      setMeetingLocation("");
      setMeetingAttendees([]);
      loadData();
    } catch (err: any) {
      toast.error("Error al programar la reunión");
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskTitle || !taskAssignee) {
      toast.error("Completa el título y el responsable");
      return;
    }
    try {
      await CalendarAPI.createTask({
        title: taskTitle,
        description: taskDesc,
        assigned_to: taskAssignee,
        due_date: taskDueDate || null,
        priority: taskPriority,
        status: "todo"
      });
      toast.success("Tarea creada y asignada");
      setTaskTitle("");
      setTaskDesc("");
      setTaskAssignee("");
      setTaskDueDate("");
      setTaskPriority("medium");
      loadData();
    } catch (err: any) {
      toast.error("Error al crear la tarea");
    }
  };

  const handleReviewVacation = async (vacationId: string, status: "approved" | "rejected") => {
    try {
      await CalendarAPI.reviewVacation(vacationId, status);
      toast.success(`Solicitud ${status === "approved" ? "aprobada" : "rechazada"}`);
      loadData();
    } catch (err) {
      toast.error("Error al procesar la solicitud");
    }
  };

  const handleDeleteMeeting = async (meetingId: string) => {
    if (!confirm("¿Seguro que quieres eliminar esta reunión?")) return;
    try {
      await CalendarAPI.deleteMeeting(meetingId);
      toast.success("Reunión eliminada");
      loadData();
    } catch (err) {
      toast.error("Error al eliminar la reunión");
    }
  };

  const handleToggleTaskStatus = async (task: CalendarEvent) => {
    const nextStatus = task.status === "todo" ? "in_progress" : task.status === "in_progress" ? "done" : "todo";
    try {
      await CalendarAPI.updateTask(task.id, { status: nextStatus });
      toast.success(`Estado de tarea actualizado a: ${nextStatus}`);
      loadData();
    } catch (err) {
      toast.error("Error al actualizar la tarea");
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm("¿Seguro que quieres eliminar esta tarea?")) return;
    try {
      await CalendarAPI.deleteTask(taskId);
      toast.success("Tarea eliminada");
      loadData();
    } catch (err) {
      toast.error("Error al eliminar la tarea");
    }
  };

  const handleAttendeeCheckbox = (empId: string) => {
    if (meetingAttendees.includes(empId)) {
      setMeetingAttendees(meetingAttendees.filter(id => id !== empId));
    } else {
      setMeetingAttendees([...meetingAttendees, empId]);
    }
  };

  // Render helpers
  const getEventBadge = (type: string, status?: string) => {
    if (type === "vacation") {
      return status === "approved" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
             status === "rejected" ? "bg-rose-500/10 text-rose-500 border-rose-500/20" :
             "bg-amber-500/10 text-amber-500 border-amber-500/20";
    }
    if (type === "meeting") return "bg-blue-500/10 text-blue-500 border-blue-500/20";
    return "bg-purple-500/10 text-purple-500 border-purple-500/20";
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-500 animate-pulse" />
            Calendario Corporativo
          </h2>
          <p className="text-muted-foreground text-sm">
            Gestión centralizada de vacaciones, reuniones de equipo y tareas asignadas.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="px-3 py-1">
            Rol: {currentUserRole === "hr_admin" ? "Administrador HR" : "Colaborador"}
          </Badge>
        </div>
      </div>

      <InlineCopilot
        moduleContext="calendar"
        placeholder="Pregunta sobre vacaciones, reuniones o eventos..."
        quickActions={[
          { label: "Ver mis vacaciones pendientes", message: "Ver mis vacaciones pendientes" },
          { label: "Solicitar días libres", message: "Solicitar días libres" },
          { label: "Resumir eventos de esta semana", message: "Resumir eventos de esta semana" },
          { label: "Buscar hueco para reunión", message: "Buscar hueco para reunión" },
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left/Middle: Calendar Grid */}
        <Card className="lg:col-span-2 glass shadow-lg border-border/40 overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-border/30 bg-card/20">
            <div className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5 text-indigo-500" />
              <CardTitle className="text-lg font-bold">
                {monthNames[month]} {year}
              </CardTitle>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="icon" onClick={prevMonth} className="h-8 w-8 hover:bg-muted/80">
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setCurrentDate(new Date())} className="h-8 hover:bg-muted/80">
                Hoy
              </Button>
              <Button variant="outline" size="icon" onClick={nextMonth} className="h-8 w-8 hover:bg-muted/80">
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-4 bg-card/5">
            {/* Days of week */}
            <div className="grid grid-cols-7 gap-1 text-center font-semibold text-xs text-muted-foreground mb-2">
              {daysOfWeek.map((day, i) => (
                <div key={i} className="py-2">{day}</div>
              ))}
            </div>

            {/* Grid */}
            <div className="grid grid-cols-7 gap-1.5">
              {/* Padding empty slots for offset */}
              {Array(firstDayIndex)
                .fill(null)
                .map((_, i) => (
                  <div key={`empty-${i}`} className="aspect-square bg-muted/10 rounded-md border border-border/10 opacity-30" />
                ))}

              {/* Real Days */}
              {Array(daysInMonth)
                .fill(null)
                .map((_, i) => {
                  const day = i + 1;
                  const dayEvents = getDaysInMonth(year, month) >= day ? getEventsForDay(day) : [];
                  const isDaySelected = isSelected(day);
                  const isDayToday = isToday(day);

                  return (
                    <button
                      key={`day-${day}`}
                      onClick={() => handleSelectDay(day)}
                      className={`aspect-square p-1.5 rounded-md border flex flex-col justify-between transition-all duration-200 cursor-pointer relative group text-left
                        ${isDaySelected
                          ? "bg-primary text-primary-foreground border-primary shadow-md scale-105 z-10"
                          : isDayToday
                            ? "bg-indigo-500/10 border-indigo-500 text-indigo-600 dark:text-indigo-400 font-bold hover:bg-indigo-500/20"
                            : "bg-card/40 border-border/30 hover:bg-muted/50 hover:border-border text-foreground"
                        }
                      `}
                    >
                      <span className="text-xs font-medium">{day}</span>
                      
                      {/* Event Dot Indicators */}
                      {dayEvents.length > 0 && (
                        <div className="flex flex-wrap gap-0.5 mt-1 max-h-5 overflow-hidden">
                          {dayEvents.slice(0, 3).map((e) => (
                            <span
                              key={e.id}
                              className={`w-2 h-2 rounded-full border border-background
                                ${e.type === "vacation"
                                  ? e.status === "approved"
                                    ? "bg-emerald-500"
                                    : "bg-amber-500"
                                  : e.type === "meeting"
                                    ? "bg-blue-500"
                                    : "bg-purple-500"
                                }
                              `}
                              title={e.title}
                            />
                          ))}
                          {dayEvents.length > 3 && (
                            <span className="text-[8px] leading-none text-muted-foreground font-bold">
                              +{dayEvents.length - 3}
                            </span>
                          )}
                        </div>
                      )}
                    </button>
                  );
                })}
            </div>
          </CardContent>
        </Card>

        {/* Right: Selected Day Details Panel */}
        <Card className="glass shadow-lg border-border/40 flex flex-col h-[480px]">
          <CardHeader className="border-b border-border/30 bg-card/25 pb-4">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Clock className="h-4 w-4 text-indigo-500" />
              Detalles del Día
            </CardTitle>
            <CardDescription className="text-xs text-foreground/80 font-medium">
              {selectedDate.toLocaleDateString("es-ES", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric"
              })}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <div className="animate-spin h-5 w-5 rounded-full border-2 border-primary border-t-transparent" />
              </div>
            ) : getSelectedDayEvents().length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground py-8">
                <CalendarIcon className="h-10 w-10 text-muted-foreground/30 mb-2" />
                <p className="text-xs">No hay eventos programados para este día.</p>
              </div>
            ) : (
              getSelectedDayEvents().map((e) => (
                <div key={e.id} className="p-3 rounded-lg border border-border/40 bg-card/20 hover:bg-card/40 transition-colors flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline" className={`text-[10px] py-0 px-2 uppercase ${getEventBadge(e.type, e.status)}`}>
                      {e.type}
                    </Badge>
                    {e.type === "meeting" && (
                      <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive hover:bg-destructive/10" onClick={() => handleDeleteMeeting(e.id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {e.type === "task" && (
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={() => handleToggleTaskStatus(e)}>
                          {e.status === "done" ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                          ) : (
                            <Circle className="h-3.5 w-3.5" />
                          )}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive hover:bg-destructive/10" onClick={() => handleDeleteTask(e.id)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>
                  <h4 className="text-sm font-semibold text-foreground leading-tight">{e.title}</h4>
                  {e.extra?.description && <p className="text-xs text-muted-foreground truncate">{e.extra.description}</p>}
                  {e.extra?.reason && <p className="text-xs text-muted-foreground italic">&quot; {e.extra.reason} &quot;</p>}
                  
                  {/* Detailed Meta */}
                  <div className="flex flex-col gap-1 text-[11px] text-muted-foreground pt-1.5 border-t border-border/20 mt-1">
                    {e.type === "meeting" && (
                      <>
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-indigo-400" />
                          {new Date(e.start).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })} - {e.end ? new Date(e.end).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }) : ""}
                        </div>
                        {e.extra?.location && (
                          <div className="flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5 text-indigo-400" />
                            {e.extra.location}
                          </div>
                        )}
                      </>
                    )}
                    {e.type === "task" && (
                      <>
                        {e.priority && (
                          <div className="flex items-center gap-1">
                            <AlertCircle className={`w-3.5 h-3.5 ${e.priority === "urgent" || e.priority === "high" ? "text-rose-500" : "text-muted-foreground"}`} />
                            Prioridad: <span className="font-semibold uppercase text-[10px]">{e.priority}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-1">
                          <User className="w-3.5 h-3.5 text-purple-400" />
                          Asignado: {employees.find(emp => emp.id === e.extra?.assigned_to)?.full_name || "Desconocido"}
                        </div>
                      </>
                    )}
                    {e.type === "vacation" && (
                      <div className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5 text-emerald-400" />
                        Colaborador: {employees.find(emp => emp.id === e.extra?.user_id)?.full_name || "Desconocido"}
                      </div>
                    )}
                  </div>

                  {/* Vacation review block (Admin only) */}
                  {e.type === "vacation" && e.status === "pending" && currentUserRole === "hr_admin" && (
                    <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-border/20">
                      <Button size="sm" className="bg-primary hover:bg-primary/90 text-white text-[10px] h-7 py-1 px-3" onClick={() => handleReviewVacation(e.id, "approved")}>
                        Aprobar
                      </Button>
                      <Button size="sm" variant="destructive" className="text-[10px] h-7 py-1 px-3" onClick={() => handleReviewVacation(e.id, "rejected")}>
                        Rechazar
                      </Button>
                    </div>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tabs / Actions Block */}
      <Card className="glass shadow-lg border-border/40 overflow-hidden">
        <div className="flex border-b border-border/30 bg-card/20">
          <button
            onClick={() => setActiveTab("vacations")}
            className={`flex-1 py-3 text-center text-sm font-semibold transition-all duration-200 border-b-2
              ${activeTab === "vacations"
                ? "border-indigo-500 text-indigo-600 dark:text-indigo-400 bg-card/50"
                : "border-transparent text-muted-foreground hover:text-foreground"
              }
            `}
          >
            Solicitudes de Vacaciones
          </button>
          <button
            onClick={() => setActiveTab("meetings")}
            className={`flex-1 py-3 text-center text-sm font-semibold transition-all duration-200 border-b-2
              ${activeTab === "meetings"
                ? "border-indigo-500 text-indigo-600 dark:text-indigo-400 bg-card/50"
                : "border-transparent text-muted-foreground hover:text-foreground"
              }
            `}
          >
            Reuniones y Calendario
          </button>
          <button
            onClick={() => setActiveTab("tasks")}
            className={`flex-1 py-3 text-center text-sm font-semibold transition-all duration-200 border-b-2
              ${activeTab === "tasks"
                ? "border-indigo-500 text-indigo-600 dark:text-indigo-400 bg-card/50"
                : "border-transparent text-muted-foreground hover:text-foreground"
              }
            `}
          >
            Tareas del Equipo
          </button>
        </div>

        <CardContent className="p-6 bg-card/5">
          {/* Vacations Tab */}
          {activeTab === "vacations" && (
            <div className="grid gap-6 md:grid-cols-2">
              {/* Form */}
              <div className="space-y-4">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <CalendarIcon className="h-4 w-4 text-emerald-500" />
                  Nueva Solicitud de Vacaciones
                </h3>
                <form onSubmit={handleRequestVacation} className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="vStart">Fecha Inicio</Label>
                      <Input id="vStart" type="date" value={vacationStart} onChange={e => setVacationStart(e.target.value)} required />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="vEnd">Fecha Fin</Label>
                      <Input id="vEnd" type="date" value={vacationEnd} onChange={e => setVacationEnd(e.target.value)} required />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="vReason">Motivo / Comentarios</Label>
                    <Input id="vReason" type="text" placeholder="Asuntos personales, viaje familiar..." value={vacationReason} onChange={e => setVacationReason(e.target.value)} />
                  </div>
                  <Button type="submit" className="w-full bg-primary hover:bg-primary/90 text-white">
                    Enviar Solicitud
                  </Button>
                </form>
              </div>

              {/* Status List */}
              <div className="space-y-4">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-500" />
                  Historial de Solicitudes
                </h3>
                <div className="max-h-[220px] overflow-y-auto space-y-2 border border-border/40 rounded-lg p-3 bg-card/20">
                  {events.filter(e => e.type === "vacation").length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-8">No hay solicitudes registradas.</p>
                  ) : (
                    events
                      .filter(e => e.type === "vacation")
                      .map((v) => (
                        <div key={v.id} className="flex items-center justify-between p-2 rounded border border-border/20 bg-card/30 text-xs">
                          <div>
                            <p className="font-semibold text-foreground">
                              {employees.find(emp => emp.id === v.extra?.user_id)?.full_name || "Colaborador"}
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              Del {new Date(v.start).toLocaleDateString()} al {v.end ? new Date(v.end).toLocaleDateString() : ""}
                            </p>
                          </div>
                          <Badge variant="outline" className={`text-[10px] px-2 py-0.5 uppercase ${getEventBadge("vacation", v.status)}`}>
                            {v.status}
                          </Badge>
                        </div>
                      ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Meetings Tab */}
          {activeTab === "meetings" && (
            <div className="grid gap-6 md:grid-cols-2">
              {/* Form */}
              <div className="space-y-4">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <Plus className="h-4 w-4 text-blue-500" />
                  Programar Reunión
                </h3>
                <form onSubmit={handleCreateMeeting} className="space-y-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="mTitle">Título de la reunión</Label>
                    <Input id="mTitle" type="text" placeholder="Daily Scrum, 1-on-1, Sync..." value={meetingTitle} onChange={e => setMeetingTitle(e.target.value)} required />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="mDesc">Descripción</Label>
                    <Input id="mDesc" type="text" placeholder="Temas a tratar..." value={meetingDesc} onChange={e => setMeetingDesc(e.target.value)} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="mStart">Fecha y Hora Inicio</Label>
                      <Input id="mStart" type="datetime-local" value={meetingStart} onChange={e => setMeetingStart(e.target.value)} required />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="mEnd">Fecha y Hora Fin</Label>
                      <Input id="mEnd" type="datetime-local" value={meetingEnd} onChange={e => setMeetingEnd(e.target.value)} required />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="mLoc">Ubicación / Enlace de videollamada</Label>
                    <Input id="mLoc" type="text" placeholder="Sala A, Google Meet..." value={meetingLocation} onChange={e => setMeetingLocation(e.target.value)} />
                  </div>

                  {/* Attendees Selection */}
                  <div className="space-y-2">
                    <Label className="text-xs">Invitar Asistentes</Label>
                    <div className="grid grid-cols-2 gap-2 max-h-[100px] overflow-y-auto border border-border/40 rounded p-2 bg-card/25">
                      {employees.map((emp) => (
                        <label key={emp.id} className="flex items-center gap-1.5 text-xs text-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={meetingAttendees.includes(emp.id)}
                            onChange={() => handleAttendeeCheckbox(emp.id)}
                            className="rounded border-border"
                          />
                          <span className="truncate">{emp.full_name}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <Button type="submit" className="w-full bg-primary hover:bg-primary/90 text-white">
                    Programar Reunión
                  </Button>
                </form>
              </div>

              {/* Scheduled Meetings List */}
              <div className="space-y-4">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <CalendarIcon className="h-4 w-4 text-blue-500" />
                  Próximas Reuniones
                </h3>
                <div className="max-h-[350px] overflow-y-auto space-y-2.5 border border-border/40 rounded-lg p-3 bg-card/20">
                  {events.filter(e => e.type === "meeting").length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-8">No hay reuniones programadas.</p>
                  ) : (
                    events
                      .filter(e => e.type === "meeting")
                      .map((m) => (
                        <div key={m.id} className="p-2.5 rounded border border-border/20 bg-card/30 text-xs flex justify-between gap-3">
                          <div className="min-w-0">
                            <h4 className="font-semibold text-foreground truncate">{m.title}</h4>
                            <p className="text-[10px] text-muted-foreground">
                              {new Date(m.start).toLocaleDateString()} a las {new Date(m.start).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
                            </p>
                            {m.extra?.location && (
                              <p className="text-[10px] text-indigo-400 mt-0.5 truncate">
                                📍 {m.extra.location}
                              </p>
                            )}
                          </div>
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10 self-start" onClick={() => handleDeleteMeeting(m.id)}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tasks Tab */}
          {activeTab === "tasks" && (
            <div className="grid gap-6 md:grid-cols-2">
              {/* Form */}
              <div className="space-y-4">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <Plus className="h-4 w-4 text-purple-500" />
                  Nueva Tarea
                </h3>
                <form onSubmit={handleCreateTask} className="space-y-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="tTitle">Nombre de la tarea</Label>
                    <Input id="tTitle" type="text" placeholder="Crear informe de costes, revisar CVs..." value={taskTitle} onChange={e => setTaskTitle(e.target.value)} required />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="tDesc">Detalles / Instrucciones</Label>
                    <Input id="tDesc" type="text" placeholder="Detalles de la entrega..." value={taskDesc} onChange={e => setTaskDesc(e.target.value)} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="tAssignee">Responsable</Label>
                      <select
                        id="tAssignee"
                        value={taskAssignee}
                        onChange={e => setTaskAssignee(e.target.value)}
                        required
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground"
                      >
                        <option value="" disabled className="text-muted-foreground">Seleccionar...</option>
                        {employees.map((emp) => (
                          <option key={emp.id} value={emp.id} className="text-foreground bg-background">{emp.full_name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="tDueDate">Fecha Límite</Label>
                      <Input id="tDueDate" type="date" value={taskDueDate} onChange={e => setTaskDueDate(e.target.value)} />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="tPriority">Prioridad</Label>
                    <select
                      id="tPriority"
                      value={taskPriority}
                      onChange={e => setTaskPriority(e.target.value as any)}
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground"
                    >
                      <option value="low" className="text-foreground bg-background">Baja</option>
                      <option value="medium" className="text-foreground bg-background">Media</option>
                      <option value="high" className="text-foreground bg-background">Alta</option>
                      <option value="urgent" className="text-foreground bg-background">Urgente</option>
                    </select>
                  </div>
                  <Button type="submit" className="w-full bg-primary hover:bg-primary/90 text-white">
                    Asignar Tarea
                  </Button>
                </form>
              </div>

              {/* Tasks List */}
              <div className="space-y-4">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <ListTodo className="h-4 w-4 text-purple-500" />
                  Lista de Tareas
                </h3>
                <div className="max-h-[350px] overflow-y-auto space-y-2 border border-border/40 rounded-lg p-3 bg-card/20">
                  {events.filter(e => e.type === "task").length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-8">No hay tareas pendientes.</p>
                  ) : (
                    events
                      .filter(e => e.type === "task")
                      .map((t) => (
                        <div key={t.id} className="p-2.5 rounded border border-border/20 bg-card/30 text-xs flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2 min-w-0">
                            <button className="text-muted-foreground hover:text-primary shrink-0" onClick={() => handleToggleTaskStatus(t)}>
                              {t.status === "done" ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                              ) : (
                                <Circle className="h-4 w-4" />
                              )}
                            </button>
                            <div className="min-w-0">
                              <h4 className={`font-semibold text-foreground truncate ${t.status === "done" ? "line-through opacity-50" : ""}`}>{t.title}</h4>
                              <p className="text-[9px] text-muted-foreground">
                                Asignado a: {employees.find(emp => emp.id === t.extra?.assigned_to)?.full_name || "Desconocido"}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Badge variant="outline" className={`text-[9px] py-0 px-1.5 font-bold uppercase
                              ${t.priority === "urgent" ? "bg-rose-500/10 text-rose-500 border-rose-500/20" :
                                t.priority === "high" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                                t.priority === "medium" ? "bg-blue-500/10 text-blue-500 border-blue-500/20" :
                                "bg-muted text-muted-foreground"
                              }
                            `}>
                              {t.priority}
                            </Badge>
                            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10" onClick={() => handleDeleteTask(t.id)}>
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
