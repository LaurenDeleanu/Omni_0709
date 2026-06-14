"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Clock, CalendarRange, Users, AlertCircle, Play, Square, Coffee, CheckCircle2,
  MapPin, RefreshCw, AlertTriangle, ShieldCheck, Calendar, ListFilter,
  UserCheck, UserX, UserMinus, Plus, Trash2, Edit3, Settings, Info, Save
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { API_BASE } from "@/lib/api/client";
import { useUser } from "@/hooks/use-user";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

type BreakLog = {
  id: string;
  time_log_id: string;
  break_type: "coffee" | "lunch" | "medical" | "personal";
  start_time: string;
  end_time: string | null;
  notes: string | null;
};

type TimeLog = {
  id: string;
  user_id: string;
  clock_in: string;
  clock_out: string | null;
  geolocation_in: string | null;
  geolocation_out: string | null;
  ip_address: string | null;
  device_info: string | null;
  notes: string | null;
  breaks: BreakLog[];
};

type WorkSchedule = {
  id: string;
  user_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  flexible: boolean;
};

type ComplianceAlert = {
  type: string;
  date: string;
  severity: "critical" | "warning" | "info";
  detail: string;
};

type ComplianceData = {
  user_id: string;
  checks: {
    rest_between_shifts: { status: "ok" | "warning"; message: string };
    continuous_work_break: { status: "ok" | "warning"; message: string };
    max_daily_hours: { status: "ok" | "warning"; message: string };
  };
  alerts: ComplianceAlert[];
};

type EmployeeStatus = {
  id: string;
  full_name: string;
  email: string;
  department: string | null;
  status: "offline" | "working" | "break";
  active_log: TimeLog | null;
  active_break: BreakLog | null;
};

export default function ShiftsPage() {
  const t = useTranslations("Navigation");
  const { user } = useUser();
  const queryClient = useQueryClient();

  const isHrAdmin = user?.role === "hr_admin" || user?.role === "super_admin";

  // Tab State
  const [activeMainTab, setActiveMainTab] = useState<"employee" | "admin">("employee");

  // --- Real-time clock ---
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  useEffect(() => {
    setCurrentTime(new Date());
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // --- Geolocation ---
  const [location, setLocation] = useState<string | null>(null);
  const [fetchingLocation, setFetchingLocation] = useState(false);

  const requestLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocalización no soportada por su navegador");
      return;
    }
    setFetchingLocation(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation(`${pos.coords.latitude.toFixed(6)},${pos.coords.longitude.toFixed(6)}`);
        setFetchingLocation(false);
        toast.success("Ubicación de fichaje capturada");
      },
      (err) => {
        toast.error("Error al obtener ubicación: " + err.message);
        setFetchingLocation(false);
      }
    );
  };

  useEffect(() => {
    requestLocation();
  }, []);

  // --- API DATA FETCHING ---
  const token = typeof window !== "undefined" ? localStorage.getItem("local_access_token") : null;
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  // 1. Get active time-log
  const { data: activeLog, isLoading: activeLoading } = useQuery<TimeLog | null>({
    queryKey: ["time-log-active"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/finance/time-logs/active`, { headers });
      if (!res.ok) return null;
      return res.json();
    },
    refetchInterval: 10000, // Cada 10s
  });

  // 2. Get past time-logs list
  const { data: timeLogs, isLoading: logsLoading } = useQuery<TimeLog[]>({
    queryKey: ["time-logs-list"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/finance/time-logs`, { headers });
      if (!res.ok) return [];
      return res.json();
    },
  });

  // 3. Get my work schedule
  const { data: mySchedule, isLoading: myScheduleLoading } = useQuery<WorkSchedule[]>({
    queryKey: ["work-schedules-mine"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/finance/work-schedules/mine`, { headers });
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : (data.schedules || []);
    },
  });

  // 4. Get my compliance status
  const { data: myCompliance } = useQuery<ComplianceData>({
    queryKey: ["my-compliance-audit"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/finance/time-logs/compliance`, { headers });
      if (!res.ok) throw new Error();
      return res.json();
    },
    refetchInterval: 30000,
  });

  // --- HR ADMIN DATA FETCHING ---
  // 5. Get all work schedules
  const { data: allSchedules } = useQuery<WorkSchedule[]>({
    queryKey: ["work-schedules-all"],
    queryFn: async () => {
      if (!isHrAdmin) return [];
      const res = await fetch(`${API_BASE}/finance/work-schedules`, { headers });
      if (!res.ok) return [];
      return res.json();
    },
    enabled: isHrAdmin,
  });

  // 6. Get all employees (to assign schedules & show team status)
  const { data: employees } = useQuery<any[]>({
    queryKey: ["employees-list"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/users`, { headers });
      if (!res.ok) return [];
      return res.json();
    },
    enabled: isHrAdmin,
  });

  // 7. Get team status (consolidated logs of everyone today)
  const { data: teamLogs } = useQuery<TimeLog[]>({
    queryKey: ["team-time-logs-today"],
    queryFn: async () => {
      if (!isHrAdmin) return [];
      const res = await fetch(`${API_BASE}/finance/time-logs`, { headers });
      if (!res.ok) return [];
      return res.json();
    },
    enabled: isHrAdmin,
    refetchInterval: 15000,
  });

  // --- STOPWATCH / ELAPSED TIMER LOGGER ---
  const [elapsedWorkingSeconds, setElapsedWorkingSeconds] = useState(0);
  const [elapsedBreakSeconds, setElapsedBreakSeconds] = useState(0);

  const activeBreak = activeLog?.breaks?.find((b) => b.end_time === null);

  useEffect(() => {
    let interval: any;
    if (activeLog && !activeLog.clock_out) {
      interval = setInterval(() => {
        // Calcular tiempo de trabajo transcurrido
        const startTime = new Date(activeLog.clock_in).getTime();
        const now = new Date().getTime();
        let totalElapsed = Math.floor((now - startTime) / 1000);

        // Si el empleado está actualmente en descanso, calculamos el descanso acumulado
        if (activeBreak) {
          const breakStart = new Date(activeBreak.start_time).getTime();
          const breakElapsed = Math.floor((now - breakStart) / 1000);
          setElapsedBreakSeconds(breakElapsed);
        } else {
          setElapsedBreakSeconds(0);
        }

        // Restar la duración de los descansos finalizados
        let completedBreaksDuration = 0;
        activeLog.breaks.forEach((b) => {
          if (b.end_time) {
            completedBreaksDuration += Math.floor((new Date(b.end_time).getTime() - new Date(b.start_time).getTime()) / 1000);
          }
        });

        // El tiempo de trabajo efectivo es total transcurrido menos descansos completados y descanso activo
        let activeBreakDuration = activeBreak ? Math.floor((now - new Date(activeBreak.start_time).getTime()) / 1000) : 0;
        let effectiveWorking = totalElapsed - completedBreaksDuration - activeBreakDuration;
        
        setElapsedWorkingSeconds(effectiveWorking > 0 ? effectiveWorking : 0);
      }, 1000);
    } else {
      setElapsedWorkingSeconds(0);
      setElapsedBreakSeconds(0);
    }
    return () => clearInterval(interval);
  }, [activeLog, activeBreak]);

  // --- MUTATIONS ---
  // A. Clock In
  const clockInMutation = useMutation({
    mutationFn: async (notes: string) => {
      const res = await fetch(`${API_BASE}/finance/time-logs/clock-in`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          user_id: user?.id || user?.user_id || (user?.sub?.includes('|') ? user?.sub?.split('|')[1] : user?.sub) || "default",
          geolocation_in: location,
          ip_address: "192.168.1.1",
          device_info: navigator.userAgent,
          notes: notes || "Entrada desde panel de control web",
        }),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al fichar la entrada");
      }
      return res.json();
    },
    onSuccess: () => {
      toast.success("✅ ¡Fichaje de Entrada Registrado!");
      queryClient.invalidateQueries({ queryKey: ["time-log-active"] });
      queryClient.invalidateQueries({ queryKey: ["time-logs-list"] });
      queryClient.invalidateQueries({ queryKey: ["my-compliance-audit"] });
    },
    onError: (err: any) => {
      toast.error(err.message);
    },
  });

  // B. Clock Out
  const clockOutMutation = useMutation({
    mutationFn: async ({ logId, notes }: { logId: string; notes: string }) => {
      const res = await fetch(`${API_BASE}/finance/time-logs/clock-out/${logId}`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          geolocation_out: location,
          notes: notes || "Salida normal",
        }),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al fichar la salida");
      }
      return res.json();
    },
    onSuccess: () => {
      toast.success("🚪 ¡Fichaje de Salida Registrado! Que tengas un buen descanso.");
      queryClient.invalidateQueries({ queryKey: ["time-log-active"] });
      queryClient.invalidateQueries({ queryKey: ["time-logs-list"] });
      queryClient.invalidateQueries({ queryKey: ["my-compliance-audit"] });
    },
    onError: (err: any) => {
      toast.error(err.message);
    },
  });

  // C. Start Break
  const startBreakMutation = useMutation({
    mutationFn: async ({ breakType, notes }: { breakType: string; notes: string }) => {
      const res = await fetch(`${API_BASE}/finance/time-logs/active/break/start`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          break_type: breakType,
          notes: notes || `Descanso tipo: ${breakType}`,
        }),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al iniciar descanso");
      }
      return res.json();
    },
    onSuccess: (data) => {
      toast.success(`☕ Pausa registrada: ${data.break_type.toUpperCase()}`);
      queryClient.invalidateQueries({ queryKey: ["time-log-active"] });
      queryClient.invalidateQueries({ queryKey: ["my-compliance-audit"] });
    },
    onError: (err: any) => {
      toast.error(err.message);
    },
  });

  // D. End Break
  const endBreakMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/finance/time-logs/active/break/end`, {
        method: "POST",
        headers,
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al finalizar descanso");
      }
      return res.json();
    },
    onSuccess: () => {
      toast.success("💼 Descanso finalizado. ¡De vuelta al trabajo!");
      queryClient.invalidateQueries({ queryKey: ["time-log-active"] });
      queryClient.invalidateQueries({ queryKey: ["my-compliance-audit"] });
    },
    onError: (err: any) => {
      toast.error(err.message);
    },
  });

  // E. HR Assign Work Schedule
  const assignScheduleMutation = useMutation({
    mutationFn: async ({ employeeId, schedules }: { employeeId: string; schedules: any[] }) => {
      const res = await fetch(`${API_BASE}/finance/work-schedules/${employeeId}`, {
        method: "POST",
        headers,
        body: JSON.stringify(schedules),
      });
      if (!res.ok) throw new Error("Error al guardar el horario");
      return res.json();
    },
    onSuccess: () => {
      toast.success("💾 Horario de trabajo asignado correctamente");
      queryClient.invalidateQueries({ queryKey: ["work-schedules-all"] });
    },
    onError: () => {
      toast.error("Ocurrió un error al guardar el horario.");
    },
  });

  // F. General Shifts Queries & Mutations
  const { data: generalShifts, isLoading: generalShiftsLoading } = useQuery<any[]>({
    queryKey: ["general-shifts-list"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/finance/general-shifts`, { headers });
      if (!res.ok) return [];
      return res.json();
    },
    enabled: isHrAdmin,
  });

  const createGeneralShiftMutation = useMutation({
    mutationFn: async (newShift: { name: string; start_time: string; end_time: string }) => {
      const res = await fetch(`${API_BASE}/finance/general-shifts`, {
        method: "POST",
        headers,
        body: JSON.stringify(newShift),
      });
      if (!res.ok) throw new Error("Error al crear la plantilla de turno");
      return res.json();
    },
    onSuccess: () => {
      toast.success("✅ Plantilla de turno creada con éxito");
      queryClient.invalidateQueries({ queryKey: ["general-shifts-list"] });
      setNewShiftName("");
      setNewShiftStart("09:00");
      setNewShiftEnd("18:00");
    },
    onError: (err: any) => {
      toast.error(err.message);
    }
  });

  const deleteGeneralShiftMutation = useMutation({
    mutationFn: async (shiftId: string) => {
      const res = await fetch(`${API_BASE}/finance/general-shifts/${shiftId}`, {
        method: "DELETE",
        headers,
      });
      if (!res.ok) throw new Error("Error al eliminar la plantilla");
      return true;
    },
    onSuccess: () => {
      toast.success("🗑️ Plantilla de turno eliminada");
      queryClient.invalidateQueries({ queryKey: ["general-shifts-list"] });
      queryClient.invalidateQueries({ queryKey: ["work-schedules-all"] });
    },
    onError: (err: any) => {
      toast.error(err.message);
    }
  });

  const bulkAssignMutation = useMutation({
    mutationFn: async (payload: { employee_ids: string[]; general_shift_id: string; days: number[] }) => {
      const res = await fetch(`${API_BASE}/finance/general-shifts/assign`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Error al realizar la asignación colectiva");
      return res.json();
    },
    onSuccess: () => {
      toast.success("👥 Turno asignado en bloque con éxito");
      queryClient.invalidateQueries({ queryKey: ["work-schedules-all"] });
      queryClient.invalidateQueries({ queryKey: ["work-schedules-mine"] });
      setBulkSelectedEmployees([]);
      setBulkSelectedShift("");
    },
    onError: (err: any) => {
      toast.error(err.message);
    }
  });

  // State variables for Bulk Assignment and General Shifts
  const [adminBottomTab, setAdminBottomTab] = useState<"individual" | "bulk" | "templates">("individual");
  const [bulkSelectedEmployees, setBulkSelectedEmployees] = useState<string[]>([]);
  const [bulkSelectedShift, setBulkSelectedShift] = useState<string>("");
  const [bulkSelectedDays, setBulkSelectedDays] = useState<number[]>([0, 1, 2, 3, 4]); // default Mon-Fri
  const [newShiftName, setNewShiftName] = useState("");
  const [newShiftStart, setNewShiftStart] = useState("09:00");
  const [newShiftEnd, setNewShiftEnd] = useState("18:00");

  // --- Clock In/Out notes and selections ---
  const [clockInNotes, setClockInNotes] = useState("");
  const [clockOutNotes, setClockOutNotes] = useState("");
  const [selectedBreakType, setSelectedBreakType] = useState<"coffee" | "lunch" | "medical" | "personal">("coffee");
  const [breakNotes, setBreakNotes] = useState("");

  // --- FORMAT HELPER ---
  const formatSeconds = (totalSecs: number) => {
    const hrs = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;
    return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const getDayName = (dayIdx: number) => {
    const days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
    return days[dayIdx] || "Desconocido";
  };

  const getBreakBadgeColor = (type: string) => {
    switch (type) {
      case "coffee": return "bg-amber-500/10 text-amber-500 border-amber-500/20";
      case "lunch": return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "medical": return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      default: return "bg-gray-500/10 text-gray-500 border-gray-500/20";
    }
  };

  const getBreakLabel = (type: string) => {
    switch (type) {
      case "coffee": return "☕ Café / Desayuno";
      case "lunch": return "🍴 Comida / Almuerzo";
      case "medical": return "🩺 Visita Médica";
      case "personal": return "🍃 Asuntos Propios";
      default: return "Pausa";
    }
  };

  // --- HR MONITORING CALCULATIONS ---
  const activeEmployeesList = () => {
    if (!employees || !teamLogs) return [];
    
    return employees.map((emp) => {
      // Encontrar el fichaje de hoy (el último)
      const empLogs = teamLogs.filter((log) => log.user_id === emp.id);
      const activeLog = empLogs.find((log) => log.clock_out === null) || null;
      
      let status: "offline" | "working" | "break" = "offline";
      let activeBreak = null;
      
      if (activeLog) {
        activeBreak = activeLog.breaks?.find((b) => b.end_time === null) || null;
        status = activeBreak ? "break" : "working";
      }
      
      return {
        ...emp,
        status,
        active_log: activeLog,
        active_break: activeBreak
      } as EmployeeStatus;
    });
  };

  // --- HR WORK SCHEDULES MANAGEMENT ---
  const [selectedEmployeeForSchedule, setSelectedEmployeeForSchedule] = useState<string>("");
  const [editScheduleDays, setEditScheduleDays] = useState<{ [day: number]: { active: boolean; start: string; end: string } }>({
    0: { active: true, start: "09:00", end: "18:00" },
    1: { active: true, start: "09:00", end: "18:00" },
    2: { active: true, start: "09:00", end: "18:00" },
    3: { active: true, start: "09:00", end: "18:00" },
    4: { active: true, start: "09:00", end: "18:00" },
    5: { active: false, start: "09:00", end: "18:00" },
    6: { active: false, start: "09:00", end: "18:00" },
  });

  const loadEmployeeScheduleForEditing = (empId: string) => {
    setSelectedEmployeeForSchedule(empId);
    if (!allSchedules) return;
    
    const empScheds = allSchedules.filter((s) => s.user_id === empId);
    const newEditState = { ...editScheduleDays };
    
    // Resetear todo a inactivo
    for (let d = 0; d < 7; d++) {
      newEditState[d] = { active: false, start: "09:00", end: "18:00" };
    }
    
    // Cargar lo que existe en DB
    empScheds.forEach((s) => {
      newEditState[s.day_of_week] = {
        active: true,
        start: s.start_time,
        end: s.end_time
      };
    });
    
    setEditScheduleDays(newEditState);
  };

  const handleSaveSchedule = () => {
    if (!selectedEmployeeForSchedule) {
      toast.error("Seleccione un empleado primero");
      return;
    }
    
    const schedulesList: any[] = [];
    Object.keys(editScheduleDays).forEach((dayStr) => {
      const day = parseInt(dayStr);
      const conf = editScheduleDays[day];
      if (conf.active) {
        schedulesList.push({
          day_of_week: day,
          start_time: conf.start,
          end_time: conf.end,
          flexible: false
        });
      }
    });
    
    assignScheduleMutation.mutate({
      employeeId: selectedEmployeeForSchedule,
      schedules: schedulesList
    });
  };

  // --- SYSTEM WIDE COMPLIANCE AUDITING CONSOLE ---
  // Simulador de alertas globales para prevenir multas en tiempo real
  const [globalComplianceLogs, setGlobalComplianceLogs] = useState<any[]>([]);

  useEffect(() => {
    if (!employees || !teamLogs) return;
    
    // Generar alertas de cumplimiento del equipo de forma simulada/agregada para HR
    const list: any[] = [];
    
    employees.slice(0, 8).forEach((emp) => {
      const empLogs = teamLogs.filter((l) => l.user_id === emp.id);
      
      // Chequeo de 12 horas entre jornadas simuladas para demostrar la potencia del sistema
      if (empLogs.length >= 2) {
        const lastOut = empLogs[1].clock_out ? new Date(empLogs[1].clock_out!).getTime() : null;
        const currentIn = new Date(empLogs[0].clock_in).getTime();
        
        if (lastOut) {
          const hours = (currentIn - lastOut) / (3600 * 1000);
          if (hours < 12.0) {
            list.push({
              employee: emp.full_name,
              type: "rest_between_shifts",
              detail: `Descanso de solo ${hours.toFixed(1)}h entre jornadas (mínimo 12h obligatorio por Art. 34.1 ET).`,
              severity: "critical",
              date: new Date(empLogs[0].clock_in).toLocaleDateString()
            });
          }
        }
      }
      
      // Chequeo de jornada de >6h continuas sin descansos de 15m
      empLogs.forEach((log) => {
        const checkIn = new Date(log.clock_in).getTime();
        const checkOut = log.clock_out ? new Date(log.clock_out).getTime() : new Date().getTime();
        const duration = (checkOut - checkIn) / (3600 * 1000);
        
        if (duration > 6.0) {
          // Sumar pausas
          let pauseMin = 0;
          log.breaks?.forEach((b) => {
            const end = b.end_time ? new Date(b.end_time).getTime() : new Date().getTime();
            pauseMin += (end - new Date(b.start_time).getTime()) / (60 * 1000);
          });
          
          if (pauseMin < 15) {
            list.push({
              employee: emp.full_name,
              type: "continuous_work_break",
              detail: `Jornada continua de ${duration.toFixed(1)}h con pausa acumulada de solo ${pauseMin.toFixed(0)} min (mínimo 15 min obligatorio).`,
              severity: "warning",
              date: new Date(log.clock_in).toLocaleDateString()
            });
          }
        }
      });
    });
    
    setGlobalComplianceLogs(list);
  }, [employees, teamLogs]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 pb-12">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-950 via-slate-800 to-indigo-950 dark:from-white dark:to-indigo-300 bg-clip-text text-transparent">
            Control Horario y Descansos
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Gestión de turnos de trabajo, pausas reglamentarias y cumplimiento con el Estatuto de los Trabajadores (Art. 34).
          </p>
        </div>
        
        {/* Real-time Madrid Clock */}
        <div className="flex items-center gap-3 px-4 py-2 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 rounded-xl shadow-inner backdrop-blur-md">
          <Clock className="w-5 h-5 animate-pulse" />
          <div className="text-right">
            <p className="text-xs font-semibold uppercase tracking-wider opacity-80">Madrid (Europa)</p>
            <p className="text-lg font-mono font-bold">
              {currentTime ? currentTime.toLocaleTimeString("es-ES") : "--:--:--"}
            </p>
          </div>
        </div>
      </div>

      <InlineCopilot
        moduleContext="schedules"
        placeholder="Pregunta sobre turnos, horarios o descansos..."
        quickActions={[
          { label: "Ver mis turnos de esta semana", message: "Ver mis turnos de esta semana" },
          { label: "Analizar cumplimiento de jornada", message: "Analizar cumplimiento de jornada" },
          { label: "Optimizar horarios del equipo", message: "Optimizar horarios del equipo" },
          { label: "Verificar descansos legales", message: "Verificar descansos legales" },
        ]}
      />

      {/* TABS - NAVIGATION FOR WORKSPACE */}
      <Tabs defaultValue="employee" className="w-full space-y-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-100/80 dark:bg-slate-900/60 p-2 rounded-xl border border-border/60">
          <TabsList className="grid grid-cols-2 w-full sm:w-[350px] bg-background/50 backdrop-blur">
            <TabsTrigger value="employee" className="gap-2" onClick={() => setActiveMainTab("employee")}>
              <Calendar className="w-4 h-4" /> Mi Jornada
            </TabsTrigger>
            {isHrAdmin && (
              <TabsTrigger value="admin" className="gap-2 text-indigo-500 dark:text-indigo-300 font-semibold" onClick={() => setActiveMainTab("admin")}>
                <ShieldCheck className="w-4 h-4" /> Panel de HR
              </TabsTrigger>
            )}
          </TabsList>
          
          <div className="text-xs text-muted-foreground flex items-center gap-2">
            <MapPin className="w-3.5 h-3.5 text-indigo-500" />
            <span className="font-mono">
              IP: 192.168.1.1 | Coord: {location || (fetchingLocation ? "Capturando..." : "Ubicación pendiente")}
            </span>
            <Button size="icon" variant="ghost" className="w-6 h-6 rounded-full" onClick={requestLocation} disabled={fetchingLocation}>
              <RefreshCw className={`w-3 h-3 ${fetchingLocation ? "animate-spin text-indigo-500" : ""}`} />
            </Button>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* ======================= TAB: EMPLOYEE PERSONAL WORKSPACE ================ */}
        {/* ========================================================================= */}
        <TabsContent value="employee" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-3">
            
            {/* COLUMN 1: LIVE TIME-CLOCK CONTROLLER */}
            <Card className="glass relative overflow-hidden md:col-span-2 border-border/50 shadow-xl bg-gradient-to-b from-card to-card/70 backdrop-blur-xl">
              <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl -z-10" />
              <CardHeader>
                <CardTitle className="text-xl flex items-center gap-2">
                  <Play className="w-5 h-5 text-indigo-500" /> Registrar Jornada Laboral
                </CardTitle>
                <CardDescription>
                  Ficha tus entradas, salidas y descansos reglamentarios. Los tiempos se auditan según la legislación vigente.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                
                {/* 1. STATE INDICATOR DISPLAY */}
                <div className="p-6 rounded-2xl border text-center space-y-4 backdrop-blur-md shadow-inner bg-slate-50/50 dark:bg-slate-900/20">
                  <div className="flex justify-center">
                    {!activeLog ? (
                      <Badge className="px-3 py-1 bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20 text-sm font-semibold gap-1.5">
                        <UserMinus className="w-4 h-4" /> Fuera de Jornada
                      </Badge>
                    ) : activeBreak ? (
                      <Badge className="px-3 py-1 bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 text-sm font-semibold gap-1.5 animate-pulse">
                        <Coffee className="w-4 h-4" /> En Descanso ({getBreakLabel(activeBreak.break_type)})
                      </Badge>
                    ) : (
                      <Badge className="px-3 py-1 bg-success/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-sm font-semibold gap-1.5 animate-pulse">
                        <Clock className="w-4 h-4" /> Trabajando Activamente
                      </Badge>
                    )}
                  </div>

                  {/* Dynamic Stopwatch Counters */}
                  <div className="grid grid-cols-2 gap-4 divide-x divide-border">
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Tiempo Efectivo Hoy</p>
                      <p className={`text-3xl font-extrabold font-mono transition-colors ${elapsedWorkingSeconds > 0 ? "text-emerald-500" : "text-muted-foreground"}`}>
                        {formatSeconds(elapsedWorkingSeconds)}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Pausa Activa / Total</p>
                      <p className={`text-3xl font-extrabold font-mono transition-colors ${elapsedBreakSeconds > 0 ? "text-amber-500 animate-pulse" : "text-muted-foreground"}`}>
                        {formatSeconds(elapsedBreakSeconds)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 2. DYNAMIC CONTROL BUTTONS */}
                {!activeLog ? (
                  /* --- CLOCK IN VIEW --- */
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Notas de entrada (Opcional)</label>
                      <Input 
                        placeholder="Ej. Teletrabajo, Visita a cliente..." 
                        value={clockInNotes} 
                        onChange={(e) => setClockInNotes(e.target.value)}
                        className="bg-background/50"
                      />
                    </div>
                    <Button 
                      className="w-full h-14 text-lg font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-indigo-600/20 gap-2 rounded-xl transition-all duration-300 hover:-translate-y-0.5" 
                      onClick={() => clockInMutation.mutate(clockInNotes)}
                      disabled={clockInMutation.isPending}
                    >
                      {clockInMutation.isPending ? "Fichando..." : (
                        <>
                          <Play className="w-5 h-5" /> Fichar Entrada Laboral
                        </>
                      )}
                    </Button>
                  </div>
                ) : activeBreak ? (
                  /* --- END ACTIVE BREAK VIEW --- */
                  <div className="space-y-4">
                    <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 text-sm flex items-start gap-3">
                      <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-amber-800 dark:text-amber-300">Estás en un descanso reglamentario</p>
                        <p className="text-muted-foreground mt-0.5">El tiempo se pausará y se sumará a tus descansos del día. Haz clic en el botón verde para volver a tu jornada efectiva.</p>
                      </div>
                    </div>
                    <Button 
                      className="w-full h-14 text-lg font-bold bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 shadow-lg shadow-emerald-500/20 gap-2 rounded-xl transition-all duration-300 hover:-translate-y-0.5" 
                      onClick={() => endBreakMutation.mutate()}
                      disabled={endBreakMutation.isPending}
                    >
                      {endBreakMutation.isPending ? "Procesando..." : (
                        <>
                          <CheckCircle2 className="w-5 h-5" /> Finalizar Descanso y Reanudar Trabajo
                        </>
                      )}
                    </Button>
                  </div>
                ) : (
                  /* --- ACTIVE WORK DAY: BREAK & CLOCK OUT VIEW --- */
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Sub-Panel: Start a break */}
                      <Card className="border border-border/50 shadow-inner bg-slate-50/20 dark:bg-slate-900/10 p-4 rounded-xl">
                        <p className="text-sm font-semibold flex items-center gap-1.5 mb-3">
                          <Coffee className="w-4 h-4 text-amber-500" /> Iniciar Pausa / Descanso
                        </p>
                        <div className="space-y-3">
                          <select 
                            value={selectedBreakType}
                            onChange={(e: any) => setSelectedBreakType(e.target.value)}
                            className="w-full rounded-md border border-input bg-background/50 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                          >
                            <option value="coffee">☕ Café / Desayuno (Pagado)</option>
                            <option value="lunch">🍴 Comida / Almuerzo (No pagado)</option>
                            <option value="medical">🩺 Visita Médica</option>
                            <option value="personal">🍃 Asuntos Propios</option>
                          </select>
                          <Input 
                            placeholder="Comentario sobre la pausa..." 
                            value={breakNotes} 
                            onChange={(e) => setBreakNotes(e.target.value)}
                            className="bg-background/50 text-xs h-8"
                          />
                          <Button 
                            variant="outline" 
                            className="w-full h-10 border-amber-500/20 text-amber-600 hover:bg-amber-500/10 dark:text-amber-400 dark:hover:bg-amber-500/20 gap-1.5"
                            onClick={() => startBreakMutation.mutate({ breakType: selectedBreakType, notes: breakNotes })}
                            disabled={startBreakMutation.isPending}
                          >
                            Iniciar Pausa
                          </Button>
                        </div>
                      </Card>

                      {/* Sub-Panel: Clock Out */}
                      <Card className="border border-border/50 shadow-inner bg-slate-50/20 dark:bg-slate-900/10 p-4 rounded-xl flex flex-col justify-between">
                        <div>
                          <p className="text-sm font-semibold flex items-center gap-1.5 mb-3 text-rose-500">
                            <Square className="w-4 h-4" /> Finalizar Jornada (Salida)
                          </p>
                          <Input 
                            placeholder="Notas de salida..." 
                            value={clockOutNotes} 
                            onChange={(e) => setClockOutNotes(e.target.value)}
                            className="bg-background/50 text-xs"
                          />
                        </div>
                        <Button 
                          className="w-full h-10 bg-rose-600 hover:bg-rose-700 shadow-md shadow-rose-600/15 gap-1.5 mt-3"
                          onClick={() => clockOutMutation.mutate({ logId: activeLog.id, notes: clockOutNotes })}
                          disabled={clockOutMutation.isPending}
                        >
                          Fichar Salida
                        </Button>
                      </Card>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* COLUMN 2: SPANISH LABOR COMPLIANCE CHECKLIST */}
            <Card className="glass border-border/50 shadow-xl bg-gradient-to-b from-card to-card/70 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="text-xl flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-indigo-500" /> Auditoría de Ley (España)
                </CardTitle>
                <CardDescription>
                  Verificaciones automáticas según el Estatuto de los Trabajadores.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                
                {/* Check 1: 12 Hours rest between shifts */}
                <div className="p-3 rounded-xl border flex items-start gap-3 bg-slate-50/30 dark:bg-slate-950/20">
                  {myCompliance?.checks?.rest_between_shifts?.status === "ok" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5 animate-bounce" />
                  )}
                  <div>
                    <p className="text-sm font-bold">12h Mínimas de Descanso</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {myCompliance?.checks?.rest_between_shifts?.message || "Validando última jornada..."}
                    </p>
                  </div>
                </div>

                {/* Check 2: Break for continuous workday > 6h */}
                <div className="p-3 rounded-xl border flex items-start gap-3 bg-slate-50/30 dark:bg-slate-950/20">
                  {myCompliance?.checks?.continuous_work_break?.status === "ok" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5 animate-pulse" />
                  )}
                  <div>
                    <p className="text-sm font-bold">Descanso de Jornada ({">"}6h)</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {myCompliance?.checks?.continuous_work_break?.message || "La ley exige al menos 15 minutos de descanso si la jornada continuada supera las 6h."}
                    </p>
                  </div>
                </div>

                {/* Check 3: Max 9 hours daily */}
                <div className="p-3 rounded-xl border flex items-start gap-3 bg-slate-50/30 dark:bg-slate-950/20">
                  {myCompliance?.checks?.max_daily_hours?.status === "ok" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="text-sm font-bold">Límite Diario Estándar (9h)</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {myCompliance?.checks?.max_daily_hours?.message || "Las horas ordinarias no pueden superar las 9h diarias."}
                    </p>
                  </div>
                </div>

                {/* Alerts Console */}
                {myCompliance?.alerts && myCompliance.alerts.length > 0 && (
                  <div className="space-y-2 mt-4">
                    <p className="text-xs font-bold text-rose-500 uppercase tracking-wider flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" /> Alertas de Cumplimiento Registradas
                    </p>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {myCompliance.alerts.map((al, idx) => (
                        <div key={idx} className="p-2.5 rounded-lg text-xs bg-rose-500/5 border border-rose-500/10 text-rose-600 dark:text-rose-400 space-y-1">
                          <div className="flex justify-between font-semibold">
                            <span>{al.type === "rest_between_shifts" ? "Violación 12h descanso" : "Falta Pausa 15m"}</span>
                            <span>{al.date}</span>
                          </div>
                          <p className="text-muted-foreground text-[10px] leading-relaxed">{al.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* LOWER SECTION: PLAN LABORAL & HISTORY LOGS */}
          <div className="grid gap-6 md:grid-cols-3">
            
            {/* MY WORK WEEKLY PLAN (Seeded) */}
            <Card className="glass border-border/50 shadow-md">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CalendarRange className="w-5 h-5 text-indigo-500" /> Mi Horario Planificado
                </CardTitle>
                <CardDescription>Horas de trabajo establecidas por contrato.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2.5">
                  {[0, 1, 2, 3, 4, 5, 6].map((dayIdx) => {
                    const sched = mySchedule?.find((s) => s.day_of_week === dayIdx);
                    return (
                      <div key={dayIdx} className="flex justify-between items-center p-2 rounded-lg border text-sm bg-slate-50/10 dark:bg-slate-900/10">
                        <span className="font-semibold text-muted-foreground">{getDayName(dayIdx)}</span>
                        {sched ? (
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="font-mono text-xs">{sched.start_time} - {sched.end_time}</Badge>
                            <span className="text-xs text-muted-foreground font-semibold">8h</span>
                          </div>
                        ) : (
                          <Badge variant="ghost" className="text-xs text-muted-foreground opacity-60">Descanso semanal</Badge>
                        )}
                      </div>
                    );
                  })}
                  <div className="mt-4 pt-3 border-t text-center text-xs font-semibold text-muted-foreground">
                    Total horas planificadas: <span className="text-indigo-500 font-mono">40 horas / semana</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* MY TIME LOGS HISTORY (TABLE) */}
            <Card className="glass border-border/50 shadow-md md:col-span-2 overflow-hidden">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ListFilter className="w-5 h-5 text-indigo-500" /> Historial Reciente de Fichajes
                </CardTitle>
                <CardDescription>Registro del control diario del corriente mes.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto max-h-[380px]">
                  <table className="w-full text-sm text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-900 text-xs font-bold uppercase tracking-wider text-muted-foreground border-b">
                        <th className="p-4">Día / Fecha</th>
                        <th className="p-4">Entrada</th>
                        <th className="p-4">Salida</th>
                        <th className="p-4">Pausas</th>
                        <th className="p-4 text-right">Efectivas</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {timeLogs && timeLogs.length > 0 ? (
                        timeLogs.slice(0, 10).map((log) => {
                          const dateStr = new Date(log.clock_in).toLocaleDateString("es-ES", { weekday: "short", day: "numeric", month: "short" });
                          const clockInTime = new Date(log.clock_in).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
                          const clockOutTime = log.clock_out 
                            ? new Date(log.clock_out).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }) 
                            : "--:--";

                          // Calcular pausas
                          let totalBreakMin = 0;
                          log.breaks?.forEach((b) => {
                            const end = b.end_time ? new Date(b.end_time).getTime() : new Date().getTime();
                            totalBreakMin += (end - new Date(b.start_time).getTime()) / (60 * 1000);
                          });

                          // Calcular neto
                          const diffMs = (log.clock_out ? new Date(log.clock_out).getTime() : new Date().getTime()) - new Date(log.clock_in).getTime();
                          const totalHours = diffMs / (3600 * 1000);
                          const netHours = totalHours - (totalBreakMin / 60.0);

                          return (
                            <tr key={log.id} className="hover:bg-slate-50/20 transition-colors">
                              <td className="p-4 font-semibold">{dateStr}</td>
                              <td className="p-4 font-mono text-xs">{clockInTime}</td>
                              <td className="p-4 font-mono text-xs">{clockOutTime}</td>
                              <td className="p-4">
                                {log.breaks && log.breaks.length > 0 ? (
                                  <div className="flex flex-wrap gap-1">
                                    {log.breaks.map((b) => (
                                      <Badge key={b.id} variant="outline" className={`text-[9px] font-semibold font-mono ${getBreakBadgeColor(b.break_type)}`}>
                                        {b.break_type.toUpperCase()}
                                      </Badge>
                                    ))}
                                    <span className="text-[10px] text-muted-foreground font-mono font-semibold self-center ml-1">
                                      ({totalBreakMin.toFixed(0)}m)
                                    </span>
                                  </div>
                                ) : (
                                  <span className="text-xs text-muted-foreground opacity-60">Sin descansos</span>
                                )}
                              </td>
                              <td className="p-4 text-right font-mono font-bold text-indigo-500">
                                {netHours > 0 ? `${netHours.toFixed(2)}h` : "0.00h"}
                              </td>
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={5} className="p-8 text-center text-muted-foreground">
                            No se han registrado fichajes este mes.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

          </div>
        </TabsContent>

        {/* ========================================================================= */}
        {/* ========================== TAB: HR ADMIN DASHBOARD ====================== */}
        {/* ========================================================================= */}
        <TabsContent value="admin" className="space-y-6">
          
          {/* STATS ROW OVERVIEW */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="glass bg-gradient-to-b from-blue-500/10 to-indigo-500/10 border-indigo-500/20 shadow-md">
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-indigo-500 text-white rounded-xl"><Users className="w-6 h-6" /></div>
                <div>
                  <p className="text-sm font-semibold text-muted-foreground">Total Plantilla</p>
                  <h3 className="text-2xl font-bold">{employees?.length || 0} empleados</h3>
                </div>
              </CardContent>
            </Card>
            <Card className="glass bg-gradient-to-b from-emerald-500/10 to-green-500/10 border-emerald-500/20 shadow-md">
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-success text-white rounded-xl"><UserCheck className="w-6 h-6 animate-pulse" /></div>
                <div>
                  <p className="text-sm font-semibold text-muted-foreground">Trabajando Hoy</p>
                  <h3 className="text-2xl font-bold">
                    {activeEmployeesList().filter((e) => e.status === "working").length} activos
                  </h3>
                </div>
              </CardContent>
            </Card>
            <Card className="glass bg-gradient-to-b from-amber-500/10 to-gold-500/10 border-amber-500/20 shadow-md">
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-amber-500 text-white rounded-xl"><Coffee className="w-6 h-6 animate-bounce" /></div>
                <div>
                  <p className="text-sm font-semibold text-muted-foreground">En Pausa / Descanso</p>
                  <h3 className="text-2xl font-bold">
                    {activeEmployeesList().filter((e) => e.status === "break").length} empleados
                  </h3>
                </div>
              </CardContent>
            </Card>
            <Card className="glass bg-gradient-to-b from-rose-500/10 to-red-500/10 border-rose-500/20 shadow-md">
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-rose-500 text-white rounded-xl"><UserX className="w-6 h-6" /></div>
                <div>
                  <p className="text-sm font-semibold text-muted-foreground">Alertas Inspección</p>
                  <h3 className="text-2xl font-bold text-rose-500">
                    {globalComplianceLogs.length} críticas
                  </h3>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            
            {/* ADMIN COLUMN 1: LIVE ACTIVE STATUS MONITORING & GEOLOCATIONS */}
            <Card className="glass border-border/50 shadow-lg md:col-span-2 overflow-hidden">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <UserCheck className="w-5 h-5 text-indigo-500" /> Monitoreo de Jornada en Vivo
                </CardTitle>
                <CardDescription>Vigila las geolocalizaciones y los estados del equipo de trabajo en tiempo real.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto max-h-[450px]">
                  <table className="w-full text-sm text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-900 text-xs font-bold uppercase tracking-wider border-b">
                        <th className="p-4">Colaborador</th>
                        <th className="p-4">Departamento</th>
                        <th className="p-4">Estado</th>
                        <th className="p-4">Inicio Jornada</th>
                        <th className="p-4 text-right">Ubicación</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {activeEmployeesList().map((emp) => {
                        return (
                          <tr key={emp.id} className="hover:bg-slate-50/20 transition-colors">
                            <td className="p-4 font-semibold">{emp.full_name}</td>
                            <td className="p-4 text-xs text-muted-foreground">{emp.department || "Sin asignación"}</td>
                            <td className="p-4">
                              {emp.status === "working" ? (
                                <Badge className="bg-success text-white border-none text-[10px] animate-pulse">TRABAJANDO</Badge>
                              ) : emp.status === "break" ? (
                                <Badge className="bg-amber-500 text-white border-none text-[10px]">EN DESCANSO</Badge>
                              ) : (
                                <Badge variant="outline" className="text-muted-foreground border-slate-300 text-[10px]">DESCONECTADO</Badge>
                              )}
                            </td>
                            <td className="p-4 font-mono text-xs">
                              {emp.active_log 
                                ? new Date(emp.active_log.clock_in).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }) 
                                : "--:--"
                              }
                            </td>
                            <td className="p-4 text-right">
                              {emp.active_log?.geolocation_in ? (
                                <a 
                                  href={`https://www.google.com/maps/search/?api=1&query=${emp.active_log.geolocation_in}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-indigo-500 hover:underline flex items-center gap-1 justify-end font-mono"
                                >
                                  <MapPin className="w-3.5 h-3.5 text-indigo-500" />
                                  GPS Map
                                </a>
                              ) : (
                                <span className="text-xs text-muted-foreground opacity-60">Sin GPS</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            {/* ADMIN COLUMN 2: REGULATORY AUDITING PANEL (Inspección de Trabajo) */}
            <Card className="glass border-border/50 shadow-lg bg-gradient-to-b from-card to-rose-500/[0.02]">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-rose-500">
                  <AlertTriangle className="w-5 h-5" /> Auditoría de Inspección Laboral
                </CardTitle>
                <CardDescription>Consola de advertencias para evitar multas de inspección en España (Art. 34 ET).</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                
                <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-700 dark:text-indigo-300 rounded-xl text-xs flex gap-2">
                  <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
                  <p>Cumplimiento automático de **Registro de Jornada Diario obligatorio (Real Decreto-ley 8/2019)** garantizado.</p>
                </div>

                <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
                  {globalComplianceLogs.length > 0 ? (
                    globalComplianceLogs.map((log, idx) => (
                      <div key={idx} className="p-3 rounded-lg border text-xs bg-rose-500/5 border-rose-500/15 text-rose-600 dark:text-rose-400 space-y-1.5 shadow-sm">
                        <div className="flex justify-between items-center font-bold">
                          <span>👤 {log.employee}</span>
                          <Badge variant="outline" className="text-[9px] uppercase border-rose-500/30 text-rose-600 dark:text-rose-400 font-mono">
                            {log.type === "rest_between_shifts" ? "Rest < 12h" : "No Break > 6h"}
                          </Badge>
                        </div>
                        <p className="text-muted-foreground text-[11px] leading-relaxed">{log.detail}</p>
                        <p className="text-[9px] text-muted-foreground font-semibold text-right">Fecha de incidencia: {log.date}</p>
                      </div>
                    ))
                  ) : (
                    <div className="p-6 text-center text-muted-foreground text-xs space-y-2 border border-dashed rounded-xl bg-slate-50/10 dark:bg-slate-900/10">
                      <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto opacity-70" />
                      <p className="font-semibold text-emerald-600 dark:text-emerald-400">¡Plantilla 100% en regla!</p>
                      <p className="text-[10px]">No se registran violaciones a la normativa de descansos de España.</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

          </div>

          {/* DYNAMIC SHIFT PLAN MATRIX (Cuadrante Semanal) */}
          <Card className="glass border-border/50 shadow-lg overflow-hidden">
            <CardHeader className="bg-slate-50/50 dark:bg-slate-900/30">
              <CardTitle className="text-lg flex items-center gap-2">
                <CalendarRange className="w-5 h-5 text-indigo-500" /> Cuadrante Semanal del Equipo (Planificador)
              </CardTitle>
              <CardDescription>
                Matriz de turnos contratados para la plantilla. Selecciona un empleado en el panel inferior para redefinir sus horarios.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-100/50 dark:bg-slate-900 text-xs font-bold uppercase tracking-wider text-muted-foreground border-b">
                      <th className="p-4 w-[200px]">Colaborador</th>
                      {[0, 1, 2, 3, 4, 5, 6].map((d) => (
                        <th key={d} className="p-4 text-center">{getDayName(d)}</th>
                      ))}
                      <th className="p-4 text-right">Horas/Semana</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {employees && employees.map((emp) => {
                      const empScheds = allSchedules?.filter((s) => s.user_id === emp.id) || [];
                      let totalHours = 0;
                      return (
                        <tr key={emp.id} className="hover:bg-slate-50/10 transition-colors">
                          <td className="p-4 font-semibold">
                            <div>
                              <p className="text-sm font-bold text-slate-800 dark:text-slate-200">{emp.full_name}</p>
                              <p className="text-[10px] text-muted-foreground">{emp.email}</p>
                            </div>
                          </td>
                          {[0, 1, 2, 3, 4, 5, 6].map((day) => {
                            const sched = empScheds.find((s) => s.day_of_week === day);
                            if (sched) {
                              totalHours += 8;
                              return (
                                <td key={day} className="p-4 text-center">
                                  <Badge className="px-2.5 py-1 bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 border-indigo-500/20 font-mono text-[10px] rounded-lg">
                                    {sched.start_time}-{sched.end_time}
                                  </Badge>
                                </td>
                              );
                            }
                            return (
                              <td key={day} className="p-4 text-center">
                                <Badge variant="ghost" className="px-2 py-0.5 text-muted-foreground/60 opacity-60 text-[10px]">
                                  Libre
                                </Badge>
                              </td>
                            );
                          })}
                          <td className="p-4 text-right font-mono font-bold text-indigo-500 text-sm">
                            {totalHours}h
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* LOWER ROW: HR WORK SCHEDULE SETTINGS EDITOR */}
          <Card className="glass border-border/50 shadow-lg">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/40 pb-4">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CalendarRange className="w-5 h-5 text-indigo-500" /> Planificador y Asignador de Turnos
                </CardTitle>
                <CardDescription>Crea horarios contractuales individuales, gestiona turnos generales o realiza asignaciones en bloque.</CardDescription>
              </div>
              <div className="flex gap-1.5 bg-slate-100/80 dark:bg-slate-900/60 p-1 rounded-lg border text-xs">
                <Button
                  size="sm"
                  variant={adminBottomTab === "individual" ? "default" : "ghost"}
                  className="text-xs h-7 rounded px-3 py-1 font-semibold"
                  onClick={() => setAdminBottomTab("individual")}
                >
                  <Users className="w-3.5 h-3.5 mr-1" /> Individual
                </Button>
                <Button
                  size="sm"
                  variant={adminBottomTab === "bulk" ? "default" : "ghost"}
                  className="text-xs h-7 rounded px-3 py-1 font-semibold text-indigo-500 dark:text-indigo-300"
                  onClick={() => setAdminBottomTab("bulk")}
                >
                  <Plus className="w-3.5 h-3.5 mr-1" /> En Bloque
                </Button>
                <Button
                  size="sm"
                  variant={adminBottomTab === "templates" ? "default" : "ghost"}
                  className="text-xs h-7 rounded px-3 py-1 font-semibold text-amber-500"
                  onClick={() => setAdminBottomTab("templates")}
                >
                  <Settings className="w-3.5 h-3.5 mr-1" /> Turnos Generales
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
              
              {/* TAB 1: INDIVIDUAL WORK SCHEDULE ASSIGNMENT */}
              {adminBottomTab === "individual" && (
                <div className="grid gap-6 md:grid-cols-4">
                  
                  {/* Employee Selector List */}
                  <div className="border border-border/50 rounded-xl bg-slate-50/10 dark:bg-slate-900/10 p-3 max-h-[350px] overflow-y-auto">
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2.5 px-1">Seleccionar Colaborador</p>
                    <div className="space-y-1.5">
                      {employees?.map((emp) => (
                        <button
                          key={emp.id}
                          onClick={() => loadEmployeeScheduleForEditing(emp.id)}
                          className={`w-full text-left p-2.5 rounded-lg text-xs font-semibold transition-all border ${
                            selectedEmployeeForSchedule === emp.id 
                              ? "bg-primary text-white border-indigo-700 shadow-md shadow-indigo-600/15" 
                              : "bg-background/50 hover:bg-slate-100 dark:hover:bg-slate-950 border-transparent"
                          }`}
                        >
                          {emp.full_name}
                          <p className={`text-[10px] ${selectedEmployeeForSchedule === emp.id ? "text-white/80" : "text-muted-foreground"}`}>
                            {emp.email}
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Day Editor Form (3 cols) */}
                  <div className="md:col-span-3 space-y-4">
                    {selectedEmployeeForSchedule ? (
                      <div className="space-y-6">
                        <div className="flex justify-between items-center">
                          <h4 className="font-bold text-sm text-indigo-500">
                            Configurando horario de: <span className="underline text-slate-800 dark:text-slate-200">{employees?.find((e) => e.id === selectedEmployeeForSchedule)?.full_name}</span>
                          </h4>
                          <Button 
                            onClick={handleSaveSchedule} 
                            disabled={assignScheduleMutation.isPending}
                            className="bg-primary hover:bg-indigo-700 font-bold gap-2 text-xs h-9 px-4 shadow-md shadow-indigo-600/15"
                          >
                            <Save className="w-4 h-4" /> Guardar Horario
                          </Button>
                        </div>

                        <div className="grid gap-3">
                          {[0, 1, 2, 3, 4, 5, 6].map((day) => {
                            const conf = editScheduleDays[day] || { active: false, start: "09:00", end: "18:00" };
                            return (
                              <div key={day} className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-3 rounded-lg border text-sm bg-slate-50/10 dark:bg-slate-900/10">
                                
                                <div className="flex items-center gap-3">
                                  <input
                                    type="checkbox"
                                    id={`day-chk-${day}`}
                                    checked={conf.active}
                                    onChange={(e) => {
                                      const copy = { ...editScheduleDays };
                                      copy[day] = { ...copy[day], active: e.target.checked };
                                      setEditScheduleDays(copy);
                                    }}
                                    className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                  />
                                  <label htmlFor={`day-chk-${day}`} className="font-semibold w-24">
                                    {getDayName(day)}
                                  </label>
                                </div>

                                {conf.active ? (
                                  <div className="flex items-center gap-4 w-full sm:w-auto">
                                    <div className="flex items-center gap-2 text-xs">
                                      <span>Hora Entrada:</span>
                                      <Input
                                        type="text"
                                        value={conf.start}
                                        onChange={(e) => {
                                          const copy = { ...editScheduleDays };
                                          copy[day] = { ...copy[day], start: e.target.value };
                                          setEditScheduleDays(copy);
                                        }}
                                        className="w-18 h-8 px-2 text-xs text-center font-mono font-bold bg-background"
                                        placeholder="09:00"
                                      />
                                    </div>
                                    <div className="flex items-center gap-2 text-xs">
                                      <span>Hora Salida:</span>
                                      <Input
                                        type="text"
                                        value={conf.end}
                                        onChange={(e) => {
                                          const copy = { ...editScheduleDays };
                                          copy[day] = { ...copy[day], end: e.target.value };
                                          setEditScheduleDays(copy);
                                        }}
                                        className="w-18 h-8 px-2 text-xs text-center font-mono font-bold bg-background"
                                        placeholder="18:00"
                                      />
                                    </div>
                                    <span className="text-xs text-muted-foreground font-semibold shrink-0">8 horas</span>
                                  </div>
                                ) : (
                                  <span className="text-xs text-muted-foreground italic font-medium opacity-65">Descanso semanal contractual</span>
                                )}

                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <div className="p-12 text-center border border-dashed rounded-xl flex flex-col items-center justify-center h-full min-h-[250px] bg-slate-50/10 dark:bg-slate-900/10 text-muted-foreground">
                        <CalendarRange className="w-10 h-10 text-indigo-500 mb-2 opacity-50" />
                        <p className="font-semibold text-sm">No se ha seleccionado colaborador</p>
                        <p className="text-xs max-w-sm mt-1">Selecciona un empleado de la lista de la izquierda para planificar o modificar sus horarios de trabajo semanales.</p>
                      </div>
                    )}
                  </div>

                </div>
              )}

              {/* TAB 2: BULK SHIFT ASSIGNMENT */}
              {adminBottomTab === "bulk" && (
                <div className="grid gap-6 md:grid-cols-4">
                  {/* Left Side: Employees Checkbox Multi-Selector */}
                  <div className="border border-border/50 rounded-xl bg-slate-50/10 dark:bg-slate-900/10 p-3 max-h-[350px] overflow-y-auto">
                    <div className="flex flex-col gap-1 mb-3 px-1 border-b border-border/40 pb-2">
                      <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Seleccionar Colaboradores</p>
                      <button
                        type="button"
                        className="text-[10px] text-indigo-500 hover:text-indigo-600 font-semibold hover:underline text-left self-start mt-1"
                        onClick={() => {
                          if (bulkSelectedEmployees.length === employees?.length) {
                            setBulkSelectedEmployees([]);
                          } else {
                            setBulkSelectedEmployees(employees?.map((e) => e.id) || []);
                          }
                        }}
                      >
                        {bulkSelectedEmployees.length === employees?.length ? "Deseleccionar todos" : "Seleccionar todos"}
                      </button>
                    </div>
                    <div className="space-y-1.5">
                      {employees?.map((emp) => {
                        const isChecked = bulkSelectedEmployees.includes(emp.id);
                        return (
                          <div
                            key={emp.id}
                            className={`flex items-center gap-2 p-2 rounded-lg border text-xs font-semibold transition-all ${
                              isChecked
                                ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-700 dark:text-indigo-300"
                                : "bg-background/50 hover:bg-slate-100 dark:hover:bg-slate-950 border-transparent"
                            }`}
                          >
                            <input
                              type="checkbox"
                              id={`bulk-emp-${emp.id}`}
                              checked={isChecked}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setBulkSelectedEmployees([...bulkSelectedEmployees, emp.id]);
                                } else {
                                  setBulkSelectedEmployees(bulkSelectedEmployees.filter((id) => id !== emp.id));
                                }
                              }}
                              className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <label htmlFor={`bulk-emp-${emp.id}`} className="cursor-pointer flex-1 select-none">
                              {emp.full_name}
                              <p className="text-[10px] text-muted-foreground font-normal">{emp.email}</p>
                            </label>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Right Side: Shift & Day settings Form */}
                  <div className="md:col-span-3 space-y-6">
                    <div className="flex justify-between items-center">
                      <h4 className="font-bold text-sm text-indigo-500">
                        Configurando asignación masiva de turnos
                      </h4>
                      <Button
                        onClick={() => {
                          if (bulkSelectedEmployees.length === 0) {
                            toast.error("Selecciona al menos un empleado");
                            return;
                          }
                          if (!bulkSelectedShift) {
                            toast.error("Selecciona una plantilla de turno");
                            return;
                          }
                          if (bulkSelectedDays.length === 0) {
                            toast.error("Selecciona al menos un día");
                            return;
                          }
                          bulkAssignMutation.mutate({
                            employee_ids: bulkSelectedEmployees,
                            general_shift_id: bulkSelectedShift,
                            days: bulkSelectedDays
                          });
                        }}
                        disabled={bulkAssignMutation.isPending}
                        className="bg-primary hover:bg-indigo-700 font-bold gap-2 text-xs h-9 px-4 shadow-md shadow-indigo-600/15"
                      >
                        <Plus className="w-4 h-4" /> Asignar Turno en Bloque
                      </Button>
                    </div>

                    <div className="grid gap-6 sm:grid-cols-2">
                      {/* Select Shift Template */}
                      <div className="space-y-3">
                        <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider block">1. Seleccionar Turno General</label>
                        <select
                          value={bulkSelectedShift}
                          onChange={(e) => setBulkSelectedShift(e.target.value)}
                          className="w-full rounded-lg border border-input bg-background/50 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                        >
                          <option value="">-- Elige una plantilla de turno --</option>
                          {generalShifts?.map((shift) => (
                            <option key={shift.id} value={shift.id}>
                              {shift.name} ({shift.start_time} - {shift.end_time})
                            </option>
                          ))}
                        </select>
                        <p className="text-[10px] text-muted-foreground leading-relaxed">
                          Los turnos generales estandarizados aplican automáticamente los horarios de entrada y salida vigentes por Convenio Colectivo.
                        </p>
                      </div>

                      {/* Select Days */}
                      <div className="space-y-3">
                        <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider block">2. Días de la semana para aplicar</label>
                        <div className="grid grid-cols-2 gap-2">
                          {[0, 1, 2, 3, 4, 5, 6].map((day) => {
                            const isSelected = bulkSelectedDays.includes(day);
                            return (
                              <button
                                key={day}
                                type="button"
                                onClick={() => {
                                  if (isSelected) {
                                    setBulkSelectedDays(bulkSelectedDays.filter((d) => d !== day));
                                  } else {
                                    setBulkSelectedDays([...bulkSelectedDays, day]);
                                  }
                                }}
                                className={`flex items-center gap-2 px-3 py-2 border rounded-lg text-xs font-semibold transition-all justify-start ${
                                  isSelected
                                    ? "bg-primary text-white border-indigo-700 shadow-sm"
                                    : "bg-background hover:bg-slate-100 dark:hover:bg-slate-900 border-border"
                                }`}
                              >
                                <span className={`w-2 h-2 rounded-full ${isSelected ? "bg-white animate-pulse" : "bg-slate-400"}`} />
                                {getDayName(day)}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: SHIFT TEMPLATES */}
              {adminBottomTab === "templates" && (
                <div className="grid gap-6 md:grid-cols-4">
                  {/* Left Side: Shift Templates List (2 cols) */}
                  <div className="md:col-span-2 space-y-4">
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider px-1">Plantillas Activas</p>
                    <div className="grid gap-3">
                      {generalShiftsLoading ? (
                        <p className="text-xs text-muted-foreground">Cargando plantillas...</p>
                      ) : generalShifts && generalShifts.length > 0 ? (
                        generalShifts.map((shift) => {
                          const isCustom = !["gs_m", "gs_t", "gs_n", "gs_o"].includes(shift.id);
                          return (
                            <div key={shift.id} className="flex justify-between items-center p-3 rounded-lg border text-sm bg-slate-50/10 dark:bg-slate-900/10 hover:bg-slate-50/20 transition-all">
                              <div className="space-y-0.5">
                                <p className="font-bold">{shift.name}</p>
                                <div className="flex gap-2">
                                  <Badge variant="outline" className="font-mono text-xs px-2 py-0.5 bg-indigo-500/5 border-indigo-500/10 text-indigo-600 dark:text-indigo-300">
                                    {shift.start_time} - {shift.end_time}
                                  </Badge>
                                  {isCustom ? (
                                    <Badge className="text-[9px] bg-indigo-500/15 text-indigo-600 border-none font-semibold uppercase tracking-wider">Empresa</Badge>
                                  ) : (
                                    <Badge className="text-[9px] bg-slate-500/15 text-slate-600 border-none font-semibold uppercase tracking-wider">Efecto Ley</Badge>
                                  )}
                                </div>
                              </div>
                              {isCustom ? (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-rose-500 hover:text-rose-700 hover:bg-rose-500/10 rounded-full"
                                  onClick={() => deleteGeneralShiftMutation.mutate(shift.id)}
                                  disabled={deleteGeneralShiftMutation.isPending}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              ) : (
                                <span className="text-[10px] text-muted-foreground italic font-semibold px-2">Sist. Ley</span>
                              )}
                            </div>
                          );
                        })
                      ) : (
                        <p className="text-xs text-muted-foreground">No hay turnos generales configurados.</p>
                      )}
                    </div>
                  </div>

                  {/* Right Side: Create New Shift Form (2 cols) */}
                  <div className="md:col-span-2 space-y-4 border-t md:border-t-0 md:border-l border-border/50 pt-4 md:pt-0 md:pl-6">
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Crear Nueva Plantilla de Turno</p>
                    <div className="space-y-4 max-w-sm">
                      <div className="space-y-2">
                        <label className="text-xs font-semibold">Nombre del Turno</label>
                        <Input
                          placeholder="Ej. Turno de Mañana Express, Turno Corto..."
                          value={newShiftName}
                          onChange={(e) => setNewShiftName(e.target.value)}
                          className="bg-background/50 h-9 text-xs"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <label className="text-xs font-semibold">Hora Inicio</label>
                          <Input
                            placeholder="09:00"
                            value={newShiftStart}
                            onChange={(e) => setNewShiftStart(e.target.value)}
                            className="bg-background/50 h-9 text-xs font-mono font-bold text-center"
                          />
                        </div>
                        <div className="space-y-2">
                          <label className="text-xs font-semibold">Hora Fin</label>
                          <Input
                            placeholder="18:00"
                            value={newShiftEnd}
                            onChange={(e) => setNewShiftEnd(e.target.value)}
                            className="bg-background/50 h-9 text-xs font-mono font-bold text-center"
                          />
                        </div>
                      </div>
                      <Button
                        onClick={() => {
                          if (!newShiftName) {
                            toast.error("El nombre del turno es obligatorio");
                            return;
                          }
                          createGeneralShiftMutation.mutate({
                            name: newShiftName,
                            start_time: newShiftStart,
                            end_time: newShiftEnd
                          });
                        }}
                        disabled={createGeneralShiftMutation.isPending}
                        className="w-full bg-primary hover:bg-indigo-700 font-bold gap-2 text-xs h-9 px-4 shadow-md shadow-indigo-600/15"
                      >
                        <Plus className="w-4 h-4" /> Guardar Nueva Plantilla
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

        </TabsContent>
      </Tabs>
    </div>
  );
}
