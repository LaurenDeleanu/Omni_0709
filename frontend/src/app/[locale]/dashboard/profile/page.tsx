"use client";

import { useEffect, useState } from "react";
import { 
  User, Calendar, DollarSign, ClipboardList, CheckCircle2, Download, Plus, 
  MapPin, Building, Briefcase, Mail, ShieldCheck, Phone, HeartHandshake, 
  Check, X, RefreshCw, AlertTriangle, FileText, Upload, HelpCircle, 
  Settings, UserCheck, CheckSquare, Sparkles, Building2, CalendarDays
} from "lucide-react";
import { useUser } from "@/hooks/use-user";
import { CalendarAPI, PayAPI, WorkflowAPI, UserWorkflow, type VacationRequest, type Payslip, UserAPI } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { EmployeeHub } from "@/components/employee/EmployeeHub";
import { EmployeeChecklists } from "@/components/employee/EmployeeChecklists";

const SPANISH_HOLIDAYS_2026: Record<string, string> = {
  "01-01": "Año Nuevo (Nacional)",
  "01-06": "Epifanía del Señor / Reyes (Nacional)",
  "03-19": "San José (Regional)",
  "04-02": "Jueves Santo (Nacional)",
  "04-03": "Viernes Santo (Nacional)",
  "05-01": "Fiesta del Trabajo (Nacional)",
  "05-02": "Fiesta de la Comunidad de Madrid (Regional)",
  "05-15": "San Isidro (Local Madrid)",
  "07-25": "Santiago Apóstol (Regional)",
  "08-15": "Asunción de la Virgen (Nacional)",
  "10-12": "Fiesta Nacional de España (Nacional)",
  "11-01": "Todos los Santos (Nacional)",
  "11-09": "Nuestra Señora de la Almudena (Local Madrid)",
  "12-06": "Día de la Constitución Española (Nacional)",
  "12-08": "Inmaculada Concepción (Nacional)",
  "12-25": "Natividad del Señor / Navidad (Nacional)"
};

const calculateAccruedVacationDays = (hireDateStr?: string) => {
  const totalAllowance = 30; // 30 días naturales según Estatuto de los Trabajadores
  if (!hireDateStr) return totalAllowance;
  try {
    const hireDate = new Date(hireDateStr);
    const currentYear = new Date().getFullYear();
    if (isNaN(hireDate.getTime()) || hireDate.getFullYear() > currentYear) return 0;
    
    // Si fue contratado antes del año actual, tiene el año completo
    if (hireDate.getFullYear() < currentYear) {
      return totalAllowance;
    }
    
    // Hired this year, calculate months worked/to be worked this year
    const hireMonth = hireDate.getMonth(); // 0-indexed
    const monthsWorked = 12 - hireMonth;
    const accrued = Math.round((totalAllowance / 12) * monthsWorked);
    return accrued;
  } catch (e) {
    return totalAllowance;
  }
};

export default function ESSProfilePage() {
  const { user, invalidate } = useUser();
  const [activeTab, setActiveTab] = useState<"profile" | "vacations" | "payslips" | "workflows" | "approvals" | "checklists">("profile");

  const isHrAdmin = user?.role === "hr_admin" || user?.role === "super_admin";

  // --- TAB 1: PROFILE EDITING & STATES ---
  const [phoneInput, setPhoneInput] = useState("");
  const [emergencyInput, setEmergencyInput] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  
  // Custom Gradient Avatar
  const gradients = [
    "from-blue-600 to-indigo-600 shadow-indigo-500/20",
    "from-violet-600 to-purple-600 shadow-purple-500/20",
    "from-emerald-500 to-teal-500 shadow-emerald-500/20",
    "from-rose-500 to-pink-500 shadow-rose-500/20",
    "from-amber-500 to-orange-600 shadow-orange-500/20"
  ];
  const [avatarIndex, setAvatarIndex] = useState(0);

  // Sensitive details approval modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalField, setModalField] = useState<"address" | "iban" | null>(null);
  const [modalValue, setModalValue] = useState("");

  // Sync inputs on user load
  useEffect(() => {
    if (user) {
      setPhoneInput(user.phone_number || "");
      setEmergencyInput(user.emergency_contact || "");
      // Generar índice determinista según su ID
      if (user.id) {
        const charCodeSum = user.id.split("").reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0);
        setAvatarIndex(charCodeSum % gradients.length);
      }
    }
  }, [user]);

  // --- TAB 2: VACATIONS STATE ---
  const [vacations, setVacations] = useState<VacationRequest[]>([]);
  const [vacationAllowance, setVacationAllowance] = useState(30);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [absenceType, setAbsenceType] = useState<"vacation" | "medical" | "personal" | "marriage">("vacation");
  const [documentPath, setDocumentPath] = useState<string | null>(null);
  const [isSubmittingVacation, setIsSubmittingVacation] = useState(false);
  const [loadingVacations, setLoadingVacations] = useState(false);

  // Interactive Mini Calendar Calendar Days Grid
  const [calMonth, setCalMonth] = useState(new Date().getMonth());
  const [calYear, setCalYear] = useState(new Date().getFullYear());

  // --- TAB 3: PAYSLIPS STATE & Breakdown ---
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [loadingPayslips, setLoadingPayslips] = useState(false);
  const [selectedPayslipForVisual, setSelectedPayslipForVisual] = useState<Payslip | null>(null);
  const [isDownloading, setIsDownloading] = useState<Record<string, boolean>>({});
  const [payrollQueryText, setPayrollQueryText] = useState("");
  const [isSubmittingQuery, setIsSubmittingQuery] = useState(false);

  // --- TAB 4: WORKFLOWS STATE ---
  const [workflows, setWorkflows] = useState<UserWorkflow[]>([]);
  const [loadingWorkflows, setLoadingWorkflows] = useState(false);
  const [isTogglingStep, setIsTogglingStep] = useState<Record<string, boolean>>({});
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, string>>({}); // Mock uploaded onboarding files

  // --- TAB 5: ADMIN CHANGES APPROVAL STATE ---
  const [changeRequests, setChangeRequests] = useState<any[]>([]);
  const [pendingVacationRequests, setPendingVacationRequests] = useState<VacationRequest[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);
  const [loadingVacationRequests, setLoadingVacationRequests] = useState(false);

  // Fetch standard user profile dependencies
  useEffect(() => {
    if (!user) return;
    
    // Fetch vacations
    setLoadingVacations(true);
    CalendarAPI.getVacations()
      .then((data: any) => setVacations(data))
      .catch((err) => console.error("Error loading vacations:", err))
      .finally(() => setLoadingVacations(false));

    if (user.vacation_allowance) {
      setVacationAllowance(user.vacation_allowance);
    } else if (user.hire_date) {
      setVacationAllowance(calculateAccruedVacationDays(user.hire_date));
    } else {
      setVacationAllowance(30);
    }

    // Fetch payslips
    setLoadingPayslips(true);
    PayAPI.getMyPayslips()
      .then((data: any) => {
        setPayslips(data);
        if (data.length > 0) {
          setSelectedPayslipForVisual(data[0]);
        }
      })
      .catch((err) => console.error("Error loading payslips:", err))
      .finally(() => setLoadingPayslips(false));

    // Fetch onboarding workflows
    setLoadingWorkflows(true);
    WorkflowAPI.getUserWorkflows(user.id)
      .then((data) => setWorkflows(data))
      .catch((err) => console.error("Error loading workflows:", err))
      .finally(() => setLoadingWorkflows(false));
  }, [user]);

  // Load Change Requests for admin approvals tab
  const fetchChangeRequests = async () => {
    setLoadingRequests(true);
    try {
      const data = await UserAPI.getProfileRequests();
      setChangeRequests(data);
    } catch (err) {
      console.error("Error loading change requests:", err);
    } finally {
      setLoadingRequests(false);
    }
  };

  const fetchPendingVacationRequests = async () => {
    if (!isHrAdmin) return;
    setLoadingVacationRequests(true);
    try {
      const data: any = await CalendarAPI.getVacations();
      const pending = data.filter((v: any) => v.status === "pending");
      setPendingVacationRequests(pending);
    } catch (err) {
      console.error("Error loading pending vacations:", err);
    } finally {
      setLoadingVacationRequests(false);
    }
  };

  useEffect(() => {
    if (isHrAdmin && activeTab === "approvals") {
      fetchChangeRequests();
      fetchPendingVacationRequests();
    }
  }, [activeTab, isHrAdmin]);

  // --- HANDLERS & ACTIONS ---
  
  // Save non-sensitive profile info
  const handleSaveContactProfile = async () => {
    setIsSavingProfile(true);
    try {
      await UserAPI.updateProfile({
        phone_number: phoneInput,
        emergency_contact: emergencyInput
      });
      toast.success("✅ Datos de contacto actualizados correctamente.");
      invalidate();
    } catch (err: any) {
      toast.error(err?.message || "Ocurrió un error al actualizar el perfil.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Open Sensitive Field Popup Dialog
  const openSensitiveEdit = (field: "address" | "iban") => {
    setModalField(field);
    setModalValue(field === "address" ? user?.address || "" : user?.iban || "");
    setIsModalOpen(true);
  };

  // Request sensitive info change
  const handleSubmitSensitiveRequest = async () => {
    if (!modalField || !modalValue.trim()) return;
    setIsSavingProfile(true);
    try {
      await UserAPI.updateProfile({
        [modalField]: modalValue
      });
      toast.success(`📝 Solicitud de cambio de ${modalField === "address" ? "Dirección" : "IBAN"} enviada a Recursos Humanos.`);
      setIsModalOpen(false);
    } catch (err: any) {
      toast.error(err?.message || "Error al solicitar el cambio.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Submit Vacation Absence Request
  const handleVacationRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate) return;
    setIsSubmittingVacation(true);

    try {
      await CalendarAPI.createVacation({
        start_date: startDate,
        end_date: endDate,
        reason: reason || `Solicitud de: ${absenceType.toUpperCase()}`,
        absence_type: absenceType,
        document_path: documentPath
      });
      toast.success("✈️ Solicitud de ausencia enviada con éxito.");
      setStartDate("");
      setEndDate("");
      setReason("");
      setAbsenceType("vacation");
      setDocumentPath(null);
      
      // Refresh list
      const data: any = await CalendarAPI.getVacations();
      setVacations(data);
    } catch (err: any) {
      toast.error(err?.message || "Error al enviar la solicitud.");
    } finally {
      setIsSubmittingVacation(false);
    }
  };

  // Upload Sickness Medical Part (Mock)
  const handleMockUploadMedicalPart = () => {
    setDocumentPath("uploads/medical_parts/justificante_medico_ss.pdf");
    toast.success("📄 Justificante Médico adjuntado correctamente.");
  };

  // Onboarding Checklist Upload File (Mock)
  const handleMockOnboardingUpload = (stepId: string, filename: string) => {
    setUploadedFiles(prev => ({ ...prev, [stepId]: filename }));
    toast.success(`📎 Archivo '${filename}' subido y adjuntado al checklist.`);
  };

  // Submit payroll query to HR
  const handlePayrollQuerySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!payrollQueryText.trim()) return;
    setIsSubmittingQuery(true);
    setTimeout(() => {
      toast.success("✉️ Consulta sobre nómina enviada a contabilidad. Recibirás respuesta pronto.");
      setPayrollQueryText("");
      setIsSubmittingQuery(false);
    }, 1000);
  };

  // Download Payslip PDF
  const handleDownloadPayslip = async (payslipId: string, cycleId: string) => {
    setIsDownloading((prev) => ({ ...prev, [payslipId]: true }));
    try {
      await PayAPI.downloadPayslipPDF(payslipId, `Periodo_${cycleId}`);
      toast.success("📥 Descarga de nómina iniciada.");
    } catch (err) {
      console.error("Error downloading payslip:", err);
      toast.error("Ocurrió un error al descargar el PDF.");
    } finally {
      setIsDownloading((prev) => ({ ...prev, [payslipId]: false }));
    }
  };

  // Toggle step complete
  const handleToggleStep = async (workflowId: string, stepId: string) => {
    if (!user) return;
    setIsTogglingStep((prev) => ({ ...prev, [stepId]: true }));
    try {
      const updatedWorkflow = await WorkflowAPI.toggleStep(user.id, stepId);
      setWorkflows((prev) => prev.map((w) => (w.id === workflowId ? updatedWorkflow : w)));
      toast.success("📋 Tarea de onboarding actualizada.");
    } catch (err: any) {
      console.error("Error toggling step:", err);
      toast.error(err?.message || "No se pudo cambiar el estado del paso");
    } finally {
      setIsTogglingStep((prev) => ({ ...prev, [stepId]: false }));
    }
  };

  // HR Admin review profile change requests
  const handleReviewRequest = async (requestId: string, approved: boolean) => {
    try {
      await UserAPI.reviewProfileRequest(requestId, approved);
      toast.success(approved ? "✅ Solicitud de cambio aprobada correctamente." : "❌ Solicitud de cambio denegada.");
      fetchChangeRequests();
      invalidate();
    } catch (err: any) {
      toast.error("Error al procesar la solicitud.");
    }
  };

  // HR Admin review vacation / absence requests
  const handleReviewVacation = async (vacationId: string, approved: boolean) => {
    try {
      await CalendarAPI.reviewVacation(vacationId, approved ? "approved" : "rejected");
      toast.success(approved ? "✈️ Solicitud de ausencia aprobada." : "❌ Solicitud de ausencia rechazada.");
      fetchPendingVacationRequests();
      // Refrescar ausencias para el calendario del admin
      const data: any = await CalendarAPI.getVacations();
      setVacations(data);
    } catch (err: any) {
      toast.error("Error al procesar la solicitud de ausencia.");
    }
  };

  // --- STATS & HELPERS ---
  const approvedVacationDays = vacations
    .filter((v) => v.status === "approved" && v.absence_type === "vacation")
    .reduce((acc, curr) => {
      const start = new Date(curr.start_date);
      const end = new Date(curr.end_date);
      const diffTime = Math.abs(end.getTime() - start.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
      return acc + diffDays;
    }, 0);

  const vacationRemaining = vacationAllowance - approvedVacationDays;

  const getAbsenceBadge = (type: string) => {
    switch (type) {
      case "medical":
        return <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20">🩺 Médica</Badge>;
      case "personal":
        return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20">🍃 Personal</Badge>;
      case "marriage":
        return <Badge className="bg-purple-500/10 text-purple-500 border-purple-500/20">💍 Licencia</Badge>;
      default:
        return <Badge className="bg-indigo-500/10 text-indigo-500 border-indigo-500/20">✈️ Vacaciones</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400">Aprobado</span>;
      case "rejected":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400">Rechazado</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400">Pendiente</span>;
    }
  };

  const getDayName = (dayIdx: number) => {
    const days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
    return days[dayIdx] || "";
  };

  const getMonthName = (monthIdx: number) => {
    const months = [
      "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];
    return months[monthIdx] || "";
  };

  // --- RENDER DYNAMIC VACATIONS GRID ---
  const renderCalendarDays = () => {
    const totalDays = new Date(calYear, calMonth + 1, 0).getDate();
    // 0 = Lunes, 6 = Domingo
    let firstDayIdx = new Date(calYear, calMonth, 1).getDay();
    firstDayIdx = firstDayIdx === 0 ? 6 : firstDayIdx - 1;

    const daysList = [];
    // Espacios en blanco para el inicio del mes
    for (let i = 0; i < firstDayIdx; i++) {
      daysList.push(<div key={`empty-${i}`} className="h-8 w-8" />);
    }

    // Días del mes
    for (let d = 1; d <= totalDays; d++) {
      const monthStr = (calMonth + 1).toString().padStart(2, '0');
      const dayStr = d.toString().padStart(2, '0');
      const holidayKey = `${monthStr}-${dayStr}`;
      const holidayName = SPANISH_HOLIDAYS_2026[holidayKey];

      // Comprobar si el día pertenece a alguna ausencia aprobada o pendiente
      const matchingAbsence = vacations.find((v) => {
        if (!v.start_date || !v.end_date) return false;
        const [sYear, sMonth, sDay] = v.start_date.split("-").map(Number);
        const [eYear, eMonth, eDay] = v.end_date.split("-").map(Number);
        const start = new Date(sYear, sMonth - 1, sDay);
        const end = new Date(eYear, eMonth - 1, eDay);
        const current = new Date(calYear, calMonth, d);
        return current >= start && current <= end;
      });

      let bgColor = "hover:bg-slate-100 dark:hover:bg-slate-800 text-foreground";
      let borderStyle = "border-transparent";
      let titleStr = undefined;

      if (matchingAbsence) {
        titleStr = `Estado: ${matchingAbsence.status.toUpperCase()} (${matchingAbsence.reason || "Sin motivo"})`;
        if (matchingAbsence.status === "approved") {
          borderStyle = "border-emerald-500/50";
          bgColor = matchingAbsence.absence_type === "medical" 
            ? "bg-blue-500/20 text-blue-600 dark:text-blue-400 font-bold" 
            : "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold";
        } else if (matchingAbsence.status === "pending") {
          borderStyle = "border-amber-500/50";
          bgColor = "bg-amber-500/10 text-amber-600 dark:text-amber-400 font-medium";
        } else {
          bgColor = "bg-rose-500/10 text-rose-600 dark:text-rose-400 font-medium";
        }
      } else if (holidayName) {
        borderStyle = "border-rose-500/40 border-dashed";
        bgColor = "bg-rose-500/10 text-rose-600 dark:text-rose-400 font-bold";
        titleStr = `Festivo: ${holidayName}`;
      }

      daysList.push(
        <div 
          key={`day-${d}`} 
          className={`h-8 w-8 rounded-lg flex items-center justify-center text-xs font-semibold border ${borderStyle} ${bgColor} transition-all cursor-pointer`}
          title={titleStr}
        >
          {d}
        </div>
      );
    }

    return daysList;
  };

  const nextMonth = () => {
    if (calMonth === 11) {
      setCalMonth(0);
      setCalYear(prev => prev + 1);
    } else {
      setCalMonth(prev => prev + 1);
    }
  };

  const prevMonth = () => {
    if (calMonth === 0) {
      setCalMonth(11);
      setCalYear(prev => prev - 1);
    } else {
      setCalMonth(prev => prev - 1);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-2">
          <div className="h-8 w-8 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin mx-auto" />
          <p className="text-muted-foreground text-sm font-medium">Cargando tu portal de empleado...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto px-4 pb-12">
      
      {/* 1. HEADER BANNER */}
      <div className="relative overflow-hidden rounded-3xl border border-border/40 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950 p-8 md:p-10 shadow-xl text-white">
        <div className="absolute right-0 top-0 translate-x-12 -translate-y-12 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute left-1/3 bottom-0 translate-y-12 w-64 h-64 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center gap-6 relative z-10">
          
          {/* Cycle Avatar onClick */}
          <div 
            onClick={() => setAvatarIndex(prev => (prev + 1) % gradients.length)}
            className={`h-24 w-24 rounded-3xl bg-gradient-to-tr ${gradients[avatarIndex]} flex items-center justify-center text-3xl font-extrabold shadow-xl cursor-pointer select-none transition-transform hover:scale-105 active:scale-95 duration-200 shrink-0 border border-white/10`}
            title="Haz clic para cambiar el estilo de tu avatar"
          >
            {user.full_name ? user.full_name.split(" ").map((n: string) => n[0]).slice(0, 2).join("").toUpperCase() : "U"}
          </div>

          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Portal del Empleado
              </Badge>
              {isHrAdmin && (
                <Badge className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  RRHH Admin
                </Badge>
              )}
            </div>
            <h2 className="text-3xl font-extrabold tracking-tight">{user.full_name || user.email}</h2>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-indigo-200/90 font-medium">
              <span className="flex items-center gap-1.5"><Briefcase className="h-4 w-4 text-indigo-400" /> {user.role === "hr_admin" ? "Recursos Humanos (Admin)" : "Empleado"}</span>
              <span className="hidden sm:inline text-indigo-500/50">•</span>
              <span className="flex items-center gap-1.5"><Building className="h-4 w-4 text-indigo-400" /> {user.department || "Sin Departamento"}</span>
              <span className="hidden sm:inline text-indigo-500/50">•</span>
              <span className="flex items-center gap-1.5"><Mail className="h-4 w-4 text-indigo-400" /> {user.email}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Employee Self-Service Hub */}
      <EmployeeHub />

      {/* 2. TAB CONTROL CENTER */}
      <div className="flex flex-wrap gap-2 p-1.5 border border-border/40 bg-slate-100/80 dark:bg-slate-900/60 rounded-2xl max-w-xl">
        {[
          { id: "profile", label: "Mi Perfil", icon: User },
          { id: "vacations", label: "Vacaciones", icon: Calendar },
          { id: "payslips", label: "Nóminas", icon: DollarSign },
          { id: "workflows", label: "Onboarding", icon: ClipboardList },
          { id: "checklists", label: "Checklists", icon: CheckSquare },
          ...(isHrAdmin ? [{ id: "approvals", label: "Aprobaciones", icon: ShieldCheck }] : [])
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center justify-center gap-2 flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all duration-200 active:scale-95 ${
                activeTab === tab.id
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/10 border border-indigo-700"
                  : "text-muted-foreground hover:text-foreground hover:bg-slate-200/50 dark:hover:bg-slate-800/50"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* ======================= TAB 1: MI PERFIL DETAILED ======================= */}
      {/* ========================================================================= */}
      {activeTab === "profile" && (
        <div className="grid gap-6 md:grid-cols-3 animate-fadeIn">
          
          {/* Card: Personal and Editable Info */}
          <Card className="glass md:col-span-2 border-border/50 shadow-md">
            <CardHeader className="flex flex-row justify-between items-center pb-3">
              <div>
                <CardTitle className="text-lg">Información Personal y Contacto</CardTitle>
                <CardDescription>Visualiza y actualiza tus datos. Los campos sensibles requieren revisión de RRHH.</CardDescription>
              </div>
              <Button 
                onClick={handleSaveContactProfile}
                disabled={isSavingProfile}
                className="bg-indigo-600 hover:bg-indigo-700 h-9 font-bold text-xs gap-1.5 shadow-md shadow-indigo-600/15"
              >
                {isSavingProfile ? "Guardando..." : (
                  <>
                    <RefreshCw className={`w-3.5 h-3.5 ${isSavingProfile ? "animate-spin" : ""}`} />
                    Guardar Cambios
                  </>
                )}
              </Button>
            </CardHeader>
            <CardContent className="space-y-5">
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                
                {/* 1. Email (Read-only) */}
                <div className="space-y-1 bg-slate-50/50 dark:bg-slate-900/10 p-2.5 rounded-lg border">
                  <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Correo Electrónico</p>
                  <p className="text-sm font-semibold text-foreground/80">{user.email || "—"}</p>
                </div>

                {/* 2. Phone (Directly Editable) */}
                <div className="space-y-1 bg-slate-50/50 dark:bg-slate-900/10 p-2.5 rounded-lg border flex flex-col justify-center">
                  <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider flex items-center gap-1">
                    <Phone className="w-3 h-3 text-indigo-500" /> Teléfono de Contacto
                  </p>
                  <input
                    type="text"
                    value={phoneInput}
                    onChange={(e) => setPhoneInput(e.target.value)}
                    placeholder="Escribe tu teléfono..."
                    className="w-full bg-transparent border-none text-sm font-semibold p-0 text-foreground focus:ring-0 focus:outline-none placeholder:text-muted-foreground/60 focus:border-b focus:border-indigo-500"
                  />
                </div>

                {/* 3. Address (Requires Approval) */}
                <div className="space-y-1 bg-slate-50/50 dark:bg-slate-900/10 p-2.5 rounded-lg border flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Dirección Postal</p>
                    <p className="text-sm font-semibold text-foreground/80 truncate max-w-[200px]">{user.address || "No configurada"}</p>
                  </div>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="h-7 text-[10px] font-bold border-indigo-500/20 text-indigo-500 hover:bg-indigo-500/10"
                    onClick={() => openSensitiveEdit("address")}
                  >
                    Editar
                  </Button>
                </div>

                {/* 4. IBAN Bancario (Requires Approval) */}
                <div className="space-y-1 bg-slate-50/50 dark:bg-slate-900/10 p-2.5 rounded-lg border flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Cuenta Bancaria (IBAN)</p>
                    <p className="text-sm font-semibold font-mono text-foreground/80 truncate max-w-[200px]">
                      {user.iban ? `${user.iban.slice(0, 4)} **** **** ****` : "No asignada"}
                    </p>
                  </div>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="h-7 text-[10px] font-bold border-indigo-500/20 text-indigo-500 hover:bg-indigo-500/10"
                    onClick={() => openSensitiveEdit("iban")}
                  >
                    Modificar
                  </Button>
                </div>

                {/* 5. Contacto Emergencia (Directly Editable) */}
                <div className="space-y-1 bg-slate-50/50 dark:bg-slate-900/10 p-2.5 rounded-lg border flex flex-col justify-center">
                  <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider flex items-center gap-1">
                    <HeartHandshake className="w-3.5 h-3.5 text-indigo-500" /> Contacto de Emergencia
                  </p>
                  <input
                    type="text"
                    value={emergencyInput}
                    onChange={(e) => setEmergencyInput(e.target.value)}
                    placeholder="Nombre y teléfono de contacto..."
                    className="w-full bg-transparent border-none text-sm font-semibold p-0 text-foreground focus:ring-0 focus:outline-none placeholder:text-muted-foreground/60 focus:border-b focus:border-indigo-500"
                  />
                </div>

                {/* 6. Num Seguridad Social (Read-only) */}
                <div className="space-y-1 bg-slate-50/50 dark:bg-slate-900/10 p-2.5 rounded-lg border">
                  <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Nº Seguridad Social</p>
                  <p className="text-sm font-mono font-semibold text-foreground/80">{user.social_security_number || "32 / 12345678 / 90"}</p>
                </div>

              </div>

              {/* 2. CONTRACT DETAILS BLOCK */}
              <div className="mt-4 pt-4 border-t space-y-3">
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Datos Contractuales de la Ficha</p>
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-3 bg-indigo-500/[0.02] border border-indigo-500/10 rounded-xl space-y-1">
                    <p className="text-[9px] font-bold text-muted-foreground uppercase">Tipo de Contrato</p>
                    <p className="text-xs font-bold">{user.contract_type || "Indefinido 100/100"}</p>
                  </div>
                  <div className="p-3 bg-indigo-500/[0.02] border border-indigo-500/10 rounded-xl space-y-1">
                    <p className="text-[9px] font-bold text-muted-foreground uppercase">Antigüedad</p>
                    <p className="text-xs font-bold">
                      {user.hire_date ? new Date(user.hire_date).toLocaleDateString("es-ES") : "2024-05-15"}
                    </p>
                  </div>
                  <div className="p-3 bg-indigo-500/[0.02] border border-indigo-500/10 rounded-xl space-y-1">
                    <p className="text-[9px] font-bold text-muted-foreground uppercase">Jornada Anual</p>
                    <p className="text-xs font-bold">1760 horas / año</p>
                  </div>
                </div>
              </div>

            </CardContent>
          </Card>

          {/* Org Tree Column */}
          <div className="space-y-6">
            
            {/* Direct hierarchy */}
            <Card className="glass border-border/50 shadow-md">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-1.5"><Building2 className="w-4 h-4 text-indigo-500" /> Jerarquía y Equipo</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5 py-4">
                
                {/* 1. Direct Manager */}
                <div className="flex items-center gap-3 p-2.5 rounded-xl border bg-indigo-500/[0.02] border-indigo-500/10">
                  <div className="h-10 w-10 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow">
                    HR
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground font-bold uppercase">Responsable Directo</p>
                    <p className="text-xs font-bold">Sede Central RRHH</p>
                    <p className="text-[10px] text-muted-foreground font-semibold">hr@successcore.com</p>
                  </div>
                </div>

                {/* 2. Peers list */}
                <div className="space-y-2">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider px-1">Compañeros de Departamento</p>
                  <div className="space-y-2 max-h-[190px] overflow-y-auto pr-1">
                    {[
                      { name: "Lucía Fernández", role: "Diseñadora UI/UX", email: "l.fernandez@successcore.com", status: "working" },
                      { name: "Carlos Mendoza", role: "Frontend Developer", email: "c.mendoza@successcore.com", status: "break" },
                      { name: "Elena Gómez", role: "Backend Developer", email: "e.gomez@successcore.com", status: "offline" }
                    ].map((peer, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 rounded-lg border text-xs bg-slate-50/10 dark:bg-slate-900/10 hover:bg-slate-50/20 transition-all">
                        <div className="min-w-0">
                          <p className="font-bold truncate">{peer.name}</p>
                          <p className="text-[9px] text-muted-foreground font-semibold">{peer.role}</p>
                        </div>
                        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                          peer.status === "working" ? "bg-emerald-500 animate-pulse" : 
                          peer.status === "break" ? "bg-amber-500" : "bg-slate-400"
                        }`} />
                      </div>
                    ))}
                  </div>
                </div>

              </CardContent>
            </Card>

          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* ==================== TAB 2: VACACIONES CON CALENDARIO =================== */}
      {/* ========================================================================= */}
      {activeTab === "vacations" && (
        <div className="grid gap-6 md:grid-cols-3 animate-fadeIn">
          
          {/* Card 1: Balance & Mini Calendar */}
          <div className="space-y-6">
            
            {/* Holiday Progress Meter */}
            <Card className="glass flex flex-col items-center justify-center p-6 text-center border-border/50 shadow-md">
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-foreground leading-none">Balance de Vacaciones</h3>
                <span className="text-[10px] font-bold text-indigo-500 uppercase tracking-wider block mt-1.5 bg-indigo-500/5 px-2 py-0.5 rounded-full border border-indigo-500/10">
                  Normativa Española (2.5d/mes)
                </span>
              </div>
              <div className="relative flex items-center justify-center">
                <svg className="w-36 h-36 transform -rotate-90">
                  <circle cx="72" cy="72" r="58" stroke="currentColor" className="text-slate-200 dark:text-slate-800" strokeWidth="10" fill="transparent" />
                  <circle
                    cx="72"
                    cy="72"
                    r="58"
                    stroke="currentColor"
                    className="text-indigo-600 transition-all duration-500"
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray={2 * Math.PI * 58}
                    strokeDashoffset={2 * Math.PI * 58 * (1 - Math.max(0, vacationRemaining) / vacationAllowance)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-3xl font-extrabold text-foreground">{Math.max(0, vacationRemaining)}</span>
                  <span className="text-[9px] text-muted-foreground font-bold uppercase">Días Restantes</span>
                </div>
              </div>
              <div className="flex gap-4 mt-6 text-xs w-full justify-around border-t border-border/40 pt-4">
                <div className="flex flex-col items-center">
                  <span className="text-muted-foreground font-medium">Asignados</span>
                  <span className="font-bold text-foreground mt-0.5">{vacationAllowance} días</span>
                </div>
                <div className="flex flex-col items-center">
                  <span className="text-muted-foreground font-medium">Consumidos</span>
                  <span className="font-bold text-foreground mt-0.5">{approvedVacationDays} días</span>
                </div>
              </div>
            </Card>

            {/* Interactive Calendar Days Grid */}
            <Card className="glass border-border/50 shadow-md p-4 space-y-3">
              <div className="flex justify-between items-center border-b border-border/40 pb-2">
                <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full" onClick={prevMonth}><RefreshCw className="rotate-180 w-3.5 h-3.5" /> ◀ </Button>
                <p className="text-xs font-bold text-indigo-500 uppercase tracking-wider">{getMonthName(calMonth)} {calYear}</p>
                <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full" onClick={nextMonth}> ▶ </Button>
              </div>
              <div className="grid grid-cols-7 gap-1 text-center font-bold text-[9px] text-muted-foreground mb-1">
                <span>LU</span><span>MA</span><span>MI</span><span>JU</span><span>VI</span><span>SÁ</span><span>DO</span>
              </div>
              <div className="grid grid-cols-7 gap-1 justify-items-center">
                {renderCalendarDays()}
              </div>
              <div className="grid grid-cols-2 gap-y-1.5 gap-x-2 pt-2 text-[9px] font-bold text-muted-foreground border-t border-border/40">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-emerald-500/20 border border-emerald-500/30" /> Aprobado</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-amber-500/10 border border-amber-500/30" /> Pendiente</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-blue-500/20 border border-blue-500/30" /> Médica</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded bg-rose-500/10 border border-dashed border-rose-500/40" /> Festivo (ES)</span>
              </div>
            </Card>

          </div>

          {/* Form and History */}
          <div className="md:col-span-2 space-y-6">
            
            {/* Request Form */}
            <Card className="glass border-border/50 shadow-md">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-1.5"><CalendarDays className="w-5 h-5 text-indigo-500" /> Solicitar Ausencia o Permiso</CardTitle>
                <CardDescription>Cumple con el Estatuto de los Trabajadores registrando vacaciones o bajas.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleVacationRequest} className="space-y-4">
                  
                  <div className="grid grid-cols-2 gap-4">
                    
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-muted-foreground">Tipo de Permiso</label>
                      <select
                        value={absenceType}
                        onChange={(e: any) => setAbsenceType(e.target.value)}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        <option value="vacation">✈️ Vacaciones Anuales (Retribuidas)</option>
                        <option value="medical">🩺 Baja por Enfermedad / Médica</option>
                        <option value="personal">🍃 Asuntos Propios / Días Libres</option>
                        <option value="marriage">💍 Licencia Especial (Matrimonio, Mudanza)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-muted-foreground">Motivo / Descripción</label>
                      <Input
                        type="text"
                        placeholder="Ej. Vacaciones de verano en familia"
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        required
                        className="bg-transparent"
                      />
                    </div>

                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-muted-foreground">Fecha Inicio</label>
                      <input
                        type="date"
                        required
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-muted-foreground">Fecha Fin</label>
                      <input
                        type="date"
                        required
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      />
                    </div>
                  </div>

                  {/* Sickness Justification Attachment */}
                  {absenceType === "medical" && (
                    <div className="p-3 rounded-xl border border-dashed border-indigo-500/20 bg-indigo-500/[0.02] flex items-center justify-between gap-4">
                      <div className="space-y-0.5">
                        <p className="text-xs font-bold flex items-center gap-1"><FileText className="w-4 h-4 text-indigo-500" /> Parte de Baja de la Seg. Social</p>
                        <p className="text-[10px] text-muted-foreground">Es obligatorio adjuntar el justificante oficial para ausencias médicas.</p>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-8 border-indigo-500/30 text-indigo-500 hover:bg-indigo-500/10 font-bold text-xs gap-1"
                        onClick={handleMockUploadMedicalPart}
                      >
                        <Upload className="w-3.5 h-3.5" />
                        {documentPath ? "Cambiar archivo" : "Adjuntar PDF"}
                      </Button>
                    </div>
                  )}

                  <Button type="submit" disabled={isSubmittingVacation} className="w-full bg-indigo-600 hover:bg-indigo-700 font-bold gap-1.5">
                    {isSubmittingVacation ? "Procesando..." : "Enviar Solicitud a RRHH"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Absence History List */}
            <Card className="glass border-border/50 shadow-md">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Historial Completo de Ausencias</CardTitle>
                <CardDescription>Control de bajas, vacaciones y permisos.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {loadingVacations ? (
                  <div className="py-6 text-center text-xs text-muted-foreground">Cargando historial...</div>
                ) : vacations.length === 0 ? (
                  <div className="py-6 text-center text-xs text-muted-foreground">Aún no has registrado ninguna solicitud.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider bg-slate-50 dark:bg-slate-900 border-b border-border/40">
                        <tr>
                          <th className="px-4 py-2">Periodo</th>
                          <th className="px-4 py-2">Días</th>
                          <th className="px-4 py-2">Tipo</th>
                          <th className="px-4 py-2">Motivo</th>
                          <th className="px-4 py-2 text-right">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {vacations.map((v) => {
                          const start = new Date(v.start_date);
                          const end = new Date(v.end_date);
                          const diff = Math.ceil(Math.abs(end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
                          return (
                            <tr key={v.id} className="hover:bg-muted/10">
                              <td className="px-4 py-3 font-semibold text-foreground">
                                {start.toLocaleDateString("es-ES", { month: 'short', day: 'numeric' })} - {end.toLocaleDateString("es-ES", { month: 'short', day: 'numeric', year: 'numeric' })}
                              </td>
                              <td className="px-4 py-3 font-bold text-foreground">{diff}d</td>
                              <td className="px-4 py-3">{getAbsenceBadge(v.absence_type)}</td>
                              <td className="px-4 py-3 text-muted-foreground truncate max-w-[150px]">{v.reason || "Vacaciones"}</td>
                              <td className="px-4 py-3 text-right">{getStatusBadge(v.status)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* ======================= TAB 3: NÓMINAS DETAILED ========================= */}
      {/* ========================================================================= */}
      {activeTab === "payslips" && (
        <div className="grid gap-6 md:grid-cols-3 animate-fadeIn">
          
          {/* Left Column: Payslips Table */}
          <Card className="glass md:col-span-2 border-border/50 shadow-md overflow-hidden">
            <CardHeader>
              <CardTitle className="text-lg">Tus Recibos de Nómina Oficiales</CardTitle>
              <CardDescription>Nóminas mensuales emitidas bajo firma digital de la organización.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {loadingPayslips ? (
                <div className="py-12 text-center text-xs text-muted-foreground">Cargando nóminas...</div>
              ) : payslips.length === 0 ? (
                <div className="py-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center space-y-2">
                  <DollarSign className="h-8 w-8 text-muted-foreground/60" />
                  <p className="font-semibold text-foreground">No hay nóminas disponibles</p>
                  <p className="text-xs max-w-[250px]">RRHH aún no ha cerrado el periodo de nóminas del corriente ciclo.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider bg-slate-50 dark:bg-slate-900 border-b border-border/40">
                      <tr>
                        <th className="px-4 py-3">Código</th>
                        <th className="px-4 py-3">Bruto</th>
                        <th className="px-4 py-3">Deducciones</th>
                        <th className="px-4 py-3">Neto Líquido</th>
                        <th className="px-4 py-3 text-right">Acciones</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {payslips.map((p) => {
                        const isSelected = selectedPayslipForVisual?.id === p.id;
                        return (
                          <tr 
                            key={p.id} 
                            onClick={() => setSelectedPayslipForVisual(p)}
                            className={`cursor-pointer transition-colors ${isSelected ? "bg-indigo-500/5 hover:bg-indigo-500/10 font-medium" : "hover:bg-muted/10"}`}
                          >
                            <td className="px-4 py-4 font-mono font-bold text-xs">#{p.id.slice(0, 6).toUpperCase()}</td>
                            <td className="px-4 py-4 text-muted-foreground">{(p.gross_salary || 0).toLocaleString()} €</td>
                            <td className="px-4 py-4 text-rose-500">-{(p.deductions || 0).toLocaleString()} €</td>
                            <td className="px-4 py-4 font-bold text-indigo-500">{(p.net_salary || 0).toLocaleString()} €</td>
                            <td className="px-4 py-4 text-right">
                              <Button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDownloadPayslip(p.id, p.cycle_id);
                                }}
                                disabled={isDownloading[p.id]}
                                variant="outline"
                                size="sm"
                                className="h-8 flex items-center gap-1 border-indigo-600/30 text-indigo-600 hover:bg-indigo-600 hover:text-white font-bold text-xs"
                              >
                                <Download className="h-3.5 w-3.5" />
                                {isDownloading[p.id] ? "..." : "PDF"}
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right Column: Visualizer Chart & Query form */}
          <div className="space-y-6">
            
            {/* Visualizer Breakdown */}
            {selectedPayslipForVisual ? (
              <Card className="glass border-border/50 shadow-md">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-bold flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-indigo-500 animate-pulse" /> Desglose de Recibo #{selectedPayslipForVisual.id.slice(0, 6).toUpperCase()}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 py-4">
                  
                  {/* Gauge Percentages */}
                  <div className="space-y-3">
                    
                    {/* 1. Neto */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold">
                        <span>Neto Recibido (Líquido)</span>
                        <span className="text-indigo-500 font-bold">
                          {((selectedPayslipForVisual.net_salary / selectedPayslipForVisual.gross_salary) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full" 
                          style={{ width: `${(selectedPayslipForVisual.net_salary / selectedPayslipForVisual.gross_salary) * 100}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-right font-bold font-mono text-indigo-500">{selectedPayslipForVisual.net_salary.toLocaleString()} €</p>
                    </div>

                    {/* 2. Deductions (SS + IRPF) */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold">
                        <span>Deducciones e Impuestos (IRPF/SS)</span>
                        <span className="text-rose-500 font-bold">
                          {((selectedPayslipForVisual.deductions / selectedPayslipForVisual.gross_salary) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-rose-500 rounded-full" 
                          style={{ width: `${(selectedPayslipForVisual.deductions / selectedPayslipForVisual.gross_salary) * 100}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-right font-bold font-mono text-rose-500">-{selectedPayslipForVisual.deductions.toLocaleString()} €</p>
                    </div>

                  </div>

                  <div className="border-t border-border/40 pt-3 text-[10px] text-muted-foreground leading-relaxed flex items-start gap-1.5">
                    <HelpCircle className="w-4 h-4 text-indigo-500 shrink-0" />
                    <span>Las retenciones de IRPF y Seguridad Social se deducen automáticamente en origen conforme a los tramos impositivos oficiales del año en curso.</span>
                  </div>

                </CardContent>
              </Card>
            ) : null}

            {/* Raise query form */}
            <Card className="glass border-border/50 shadow-md">
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-bold flex items-center gap-1.5"><Mail className="w-4 h-4 text-indigo-500" /> Consultar con Contabilidad</CardTitle>
              </CardHeader>
              <CardContent className="py-3">
                <form onSubmit={handlePayrollQuerySubmit} className="space-y-3">
                  <textarea
                    placeholder="Escribe aquí tu duda sobre los importes, tramos de IRPF o variables..."
                    value={payrollQueryText}
                    onChange={(e) => setPayrollQueryText(e.target.value)}
                    required
                    className="w-full text-xs p-2.5 rounded-lg border bg-background/50 focus:outline-none focus:ring-1 focus:ring-ring min-h-[75px]"
                  />
                  <Button 
                    type="submit" 
                    disabled={isSubmittingQuery}
                    className="w-full h-8 text-xs bg-slate-900 hover:bg-slate-800 text-white font-bold"
                  >
                    {isSubmittingQuery ? "Enviando..." : "Enviar Consulta"}
                  </Button>
                </form>
              </CardContent>
            </Card>

          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* ======================= TAB 4: WORKFLOWS ONBOARDING ===================== */}
      {/* ========================================================================= */}
      {activeTab === "workflows" && (
        <Card className="glass border-border/50 shadow-md">
          <CardHeader>
            <CardTitle className="text-lg">Tu Plan de Acogida e Integración (Onboarding)</CardTitle>
            <CardDescription>Completado de tareas e hitos de bienvenida del colaborador.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            
            {loadingWorkflows ? (
              <div className="py-8 text-center text-xs text-muted-foreground">Cargando onboarding...</div>
            ) : workflows.length === 0 ? (
              <div className="py-8 text-center text-xs text-muted-foreground flex flex-col items-center justify-center space-y-2">
                <ClipboardList className="h-8 w-8 text-muted-foreground/60" />
                <p className="font-semibold text-foreground">No tienes planes asignados</p>
                <p className="text-xs max-w-[250px]">Tu incorporación se ha completado satisfactoriamente o no tienes checklists activos.</p>
              </div>
            ) : (
              workflows.map((w) => {
                const totalSteps = w.template?.steps?.length || 0;
                const completedSteps = Object.values(w.steps_status).filter((s) => s.completed).length;
                const progressPct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

                return (
                  <div key={w.id} className="space-y-6">
                    
                    {/* Dynamic Progress Bar */}
                    <div className="space-y-2 p-4 bg-slate-50/50 dark:bg-slate-900/10 border rounded-2xl">
                      <div className="flex items-center justify-between text-xs font-bold">
                        <span className="text-foreground uppercase tracking-wider">{w.template?.name || "Plan de Acogida General"}</span>
                        <span className="text-indigo-500 font-mono">{progressPct}% completado ({completedSteps}/{totalSteps})</span>
                      </div>
                      <div className="h-2 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-600 rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} />
                      </div>
                    </div>

                    {/* Step Cards with attachments */}
                    <div className="grid gap-3 sm:grid-cols-2">
                      {w.template?.steps?.map((step) => {
                        const stepState = w.steps_status[step.id] || { completed: false };
                        const isHR = step.role !== "employee";
                        const canToggle = !isHR || w.status !== "completed";
                        const hasUploadedFile = uploadedFiles[step.id];

                        return (
                          <div
                            key={step.id}
                            className={`p-4 rounded-xl border flex flex-col justify-between gap-3 transition-all duration-200 bg-card border-border/60 hover:shadow-sm ${
                              stepState.completed ? "bg-emerald-500/[0.02] border-emerald-500/25" : ""
                            }`}
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="space-y-1 min-w-0">
                                <p 
                                  onClick={() => canToggle && handleToggleStep(w.id, step.id)}
                                  className={`text-xs font-bold leading-tight cursor-pointer hover:text-indigo-500 ${
                                    stepState.completed ? "text-emerald-700 dark:text-emerald-400 line-through" : "text-foreground"
                                  }`}
                                >
                                  {step.title}
                                </p>
                                <span className={`inline-block px-2 py-0.5 rounded-full text-[8px] font-bold uppercase tracking-wider ${
                                  isHR ? "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400" : "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/30 dark:text-indigo-400"
                                }`}>
                                  {isHR ? "RRHH firma" : "Tu tarea"}
                                </span>
                              </div>

                              <button
                                disabled={isTogglingStep[step.id]}
                                onClick={() => canToggle && handleToggleStep(w.id, step.id)}
                                className={`h-5 w-5 rounded-full flex items-center justify-center border transition-all shrink-0 ${
                                  stepState.completed
                                    ? "bg-emerald-500 border-emerald-500 text-white"
                                    : "border-border/80 hover:border-indigo-600/60"
                                }`}
                              >
                                {stepState.completed && <Check className="h-3 w-3" />}
                              </button>
                            </div>

                            {/* Upload attachments on checklist */}
                            {!stepState.completed && !isHR && (
                              <div className="pt-2 border-t border-border/30 flex items-center justify-between text-[10px] text-muted-foreground gap-2">
                                <span className="truncate">{hasUploadedFile ? `📎 ${hasUploadedFile}` : "Necesita adjuntar documento"}</span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2 text-[9px] font-bold text-indigo-500 hover:bg-indigo-500/10 rounded"
                                  onClick={() => handleMockOnboardingUpload(step.id, "dni_escaneado_firmado.pdf")}
                                >
                                  Subir
                                </Button>
                              </div>
                            )}

                          </div>
                        );
                      })}
                    </div>

                  </div>
                );
              })
            )}

          </CardContent>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* ================= TAB 5: ADMIN CHANGES APPROVAL PANEL =================== */}
      {/* ========================================================================= */}
      {isHrAdmin && activeTab === "approvals" && (
        <div className="space-y-6 animate-fadeIn">
          
          {/* Card 1: Vacation & Absence Requests Approval */}
          <Card className="glass border-border/50 shadow-md">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-1.5"><Calendar className="w-5 h-5 text-indigo-500" /> Aprobaciones de Ausencias y Vacaciones</CardTitle>
              <CardDescription>Autoriza o deniega las peticiones de días de descanso, bajas médicas y permisos oficiales de tu equipo.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {loadingVacationRequests ? (
                <div className="py-12 text-center text-xs text-muted-foreground">Cargando solicitudes de ausencias...</div>
              ) : pendingVacationRequests.length === 0 ? (
                <div className="py-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center space-y-2">
                  <CheckSquare className="h-8 w-8 text-emerald-500/80 animate-bounce" />
                  <p className="font-semibold text-foreground">¡Sin ausencias pendientes!</p>
                  <p className="text-xs">No hay peticiones de vacaciones o permisos esperando resolución.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider bg-slate-50 dark:bg-slate-900 border-b border-border/40">
                      <tr>
                        <th className="px-6 py-3">Empleado (ID)</th>
                        <th className="px-6 py-3">Tipo de Permiso</th>
                        <th className="px-6 py-3">Periodo</th>
                        <th className="px-6 py-3">Días</th>
                        <th className="px-6 py-3">Motivo</th>
                        <th className="px-6 py-3 text-right">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {pendingVacationRequests.map((req) => {
                        const start = new Date(req.start_date);
                        const end = new Date(req.end_date);
                        const diff = Math.ceil(Math.abs(end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
                        return (
                          <tr key={req.id} className="hover:bg-muted/10 text-xs">
                            <td className="px-6 py-4 font-bold text-foreground truncate max-w-[120px]">
                              {req.user_id.slice(0, 8)}...
                            </td>
                            <td className="px-6 py-4">
                              {getAbsenceBadge(req.absence_type)}
                            </td>
                            <td className="px-6 py-4 font-semibold text-foreground">
                              {start.toLocaleDateString("es-ES")} - {end.toLocaleDateString("es-ES")}
                            </td>
                            <td className="px-6 py-4 font-bold text-indigo-500">{diff}d</td>
                            <td className="px-6 py-4 text-muted-foreground max-w-[180px] truncate">{req.reason || "Sin especificar"}</td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex justify-end gap-1.5">
                                <Button
                                  size="sm"
                                  className="h-7 w-7 rounded-full bg-emerald-500 hover:bg-emerald-600 text-white p-0 flex items-center justify-center shadow shadow-emerald-500/20"
                                  onClick={() => handleReviewVacation(req.id, true)}
                                  title="Aprobar ausencia"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                </Button>
                                <Button
                                  size="sm"
                                  className="h-7 w-7 rounded-full bg-rose-500 hover:bg-rose-600 text-white p-0 flex items-center justify-center shadow shadow-rose-500/20"
                                  onClick={() => handleReviewVacation(req.id, false)}
                                  title="Rechazar ausencia"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Card 2: Sensitive Profile Field Change Requests */}
          <Card className="glass border-border/50 shadow-md">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-1.5"><ShieldCheck className="w-5 h-5 text-indigo-500" /> Aprobaciones de Ficha de Empleado</CardTitle>
              <CardDescription>Autoriza o deniega cambios en datos personales sensibles (IBAN y Dirección) solicitados por empleados.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {loadingRequests ? (
                <div className="py-12 text-center text-xs text-muted-foreground">Cargando solicitudes...</div>
              ) : changeRequests.length === 0 ? (
                <div className="py-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center space-y-2">
                  <CheckSquare className="h-8 w-8 text-muted-foreground/60" />
                  <p className="font-semibold text-foreground">¡Todo al día!</p>
                  <p className="text-xs">No existen solicitudes de cambios de perfil pendientes de revisión.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider bg-slate-50 dark:bg-slate-900 border-b border-border/40">
                      <tr>
                        <th className="px-6 py-3">Empleado</th>
                        <th className="px-6 py-3">Campo</th>
                        <th className="px-6 py-3">Valor Anterior</th>
                        <th className="px-6 py-3">Nuevo Valor</th>
                        <th className="px-6 py-3">Estado</th>
                        <th className="px-6 py-3 text-right">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {changeRequests.map((req) => (
                        <tr key={req.id} className="hover:bg-muted/10 text-xs">
                          <td className="px-6 py-4 font-bold text-foreground">ID Colaborador: {req.user_id.slice(0, 8)}...</td>
                          <td className="px-6 py-4">
                            <Badge variant="outline" className="font-mono text-[10px] bg-slate-100 dark:bg-slate-900 font-bold uppercase">
                              {req.field_name}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 text-muted-foreground truncate max-w-[150px] font-mono">{req.old_value || "—"}</td>
                          <td className="px-6 py-4 font-bold text-foreground truncate max-w-[150px] font-mono text-indigo-500">{req.new_value}</td>
                          <td className="px-6 py-4">
                            {req.status === "pending" ? (
                              <Badge className="bg-amber-500 text-white font-bold border-none text-[9px] uppercase">PENDIENTE</Badge>
                            ) : req.status === "approved" ? (
                              <Badge className="bg-emerald-500 text-white font-bold border-none text-[9px] uppercase">APROBADO</Badge>
                            ) : (
                              <Badge className="bg-rose-500 text-white font-bold border-none text-[9px] uppercase">DENEGADO</Badge>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {req.status === "pending" ? (
                              <div className="flex justify-end gap-1.5">
                                <Button
                                  size="sm"
                                  className="h-7 w-7 rounded-full bg-emerald-500 hover:bg-emerald-600 text-white p-0 flex items-center justify-center"
                                  onClick={() => handleReviewRequest(req.id, true)}
                                  title="Aprobar e integrar en ficha"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                </Button>
                                <Button
                                  size="sm"
                                  className="h-7 w-7 rounded-full bg-rose-500 hover:bg-rose-600 text-white p-0 flex items-center justify-center"
                                  onClick={() => handleReviewRequest(req.id, false)}
                                  title="Rechazar y archivar"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </Button>
                              </div>
                            ) : (
                              <span className="text-[10px] text-muted-foreground italic font-semibold">Procesado</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      )}

      {/* ========================================================================= */}
      {/* ================ DIALOG MODAL FOR SENSITIVE EDITS (Custom overlay) ======= */}
      {/* ========================================================================= */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
          <Card className="w-full max-w-md border-border/50 shadow-2xl relative bg-card">
            
            <button 
              onClick={() => setIsModalOpen(false)}
              className="absolute top-3 right-3 text-muted-foreground hover:text-foreground h-6 w-6 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center"
            >
              <X className="w-4 h-4" />
            </button>

            <CardHeader className="pb-2">
              <CardTitle className="text-md flex items-center gap-1.5 text-indigo-500">
                <AlertTriangle className="w-5 h-5 text-amber-500 animate-pulse" /> Solicitud de Cambio de Datos
              </CardTitle>
              <CardDescription>
                Por razones de cumplimiento de ley e integridad de nómina, este campo sensible requiere verificación manual de Recursos Humanos.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 pt-3">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-muted-foreground uppercase">
                  Nuevo valor para: {modalField === "address" ? "Dirección Postal" : "Cuenta Bancaria (IBAN)"}
                </label>
                <Input
                  type="text"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  className="font-mono bg-background text-sm"
                  placeholder={modalField === "address" ? "Ej. Calle Mayor 12, Madrid" : "Ej. ES21 1234 5678 ..."}
                />
              </div>

              <div className="flex gap-2.5 pt-2">
                <Button 
                  variant="outline" 
                  className="flex-1 text-xs h-9 font-semibold"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancelar
                </Button>
                <Button 
                  className="flex-1 text-xs h-9 font-bold bg-indigo-600 hover:bg-indigo-700 shadow-md shadow-indigo-600/15"
                  onClick={handleSubmitSensitiveRequest}
                  disabled={isSavingProfile}
                >
                  {isSavingProfile ? "Enviando..." : "Enviar a RRHH"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB: Checklists */}
      {activeTab === "checklists" && (
        <EmployeeChecklists />
      )}

    </div>
  );
}
