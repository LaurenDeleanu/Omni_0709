"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserAPI, HistoryAPI, Employee, HistoryEntry } from "@/lib/api";
import { useParams } from "next/navigation";
import { useRouter } from "@/i18n/routing";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  ArrowLeft, Loader2, User, Briefcase, Plus, Trash2, Edit2, Pencil,
  Calendar, DollarSign, Archive, RotateCcw, Mail, Building2, Clock,
  ChevronRight, Network, ArrowDown, CreditCard, Shield, Phone, MapPin, AlertCircle,
  TrendingUp, Activity, CheckCircle2, Ticket, FileText, GraduationCap,
  Star, ClipboardList, ShieldCheck, X, Ban, Umbrella
} from "lucide-react";
import { useState, useMemo } from "react";
import { toast } from "sonner";
import { useUser } from "@/hooks/use-user";
import { fetchClient } from "@/lib/api/client";

const EMPTY_HISTORY = {
  position: "", department: "", salary: "", currency: "EUR",
  start_date: "", end_date: "", notes: "",
};

const EMPTY_FORM = {
  email: "",
  full_name: "",
  department: "",
  role: "employee",
  is_active: true,
  phone_number: "",
  address: "",
  iban: "",
  social_security_number: "",
  emergency_contact: "",
  contract_type: "Indefinido",
  hire_date: "",
  base_salary: 50000,
  country: "ES",
  manager_id: "none",
};

const VALID_ROLES = ["employee", "hr_admin", "sys_admin", "super_admin", "manager"];

const TAB_DEFS = [
  { id: "info", label: "Información Personal", icon: User, adminOnly: false },
  { id: "history", label: "Historial Laboral", icon: Clock, adminOnly: false },
  { id: "timeoff", label: "Ausencias", icon: Umbrella, adminOnly: false },
  { id: "tickets", label: "Tickets IT", icon: Ticket, adminOnly: false },
  { id: "reviews", label: "Evaluaciones", icon: Star, adminOnly: false },
  { id: "documents", label: "Documentos", icon: FileText, adminOnly: false },
  { id: "training", label: "Formación", icon: GraduationCap, adminOnly: false },
  { id: "kudos", label: "Kudos", icon: Activity, adminOnly: false },
  { id: "roles", label: "Roles y Permisos", icon: Shield, adminOnly: true },
] as const;

type TabId = typeof TAB_DEFS[number]["id"];

export function SearchableSupervisorSelect({
  value,
  onChange,
  employees,
  excludeId,
}: {
  value: string;
  onChange: (val: string) => void;
  employees: Employee[];
  excludeId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const selectedEmployee = useMemo(() => {
    if (value === "none" || !value) return null;
    return employees.find((e) => e.id === value);
  }, [value, employees]);

  const filteredEmployees = useMemo(() => {
    const list = employees.filter((e) => e.id !== excludeId);
    if (!search) return list;
    return list.filter((e) =>
      (e.full_name || "").toLowerCase().includes(search.toLowerCase()) ||
      e.email.toLowerCase().includes(search.toLowerCase())
    );
  }, [employees, search, excludeId]);

  return (
    <div className="relative">
      <div
        onClick={() => setOpen(!open)}
        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-card/50 backdrop-blur-xs px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-hidden focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
      >
        <span className="truncate">
          {selectedEmployee ? (selectedEmployee.full_name || selectedEmployee.email) : "Sin supervisor (Jerarquía superior)"}
        </span>
        <span className="text-muted-foreground ml-2 text-xs">▼</span>
      </div>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute left-0 right-0 mt-1 max-h-60 overflow-y-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md z-40 backdrop-blur-md bg-card/95">
            <div className="px-2 py-1.5 border-b border-border/50">
              <Input
                type="text"
                placeholder="Buscar supervisor..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-8 text-xs bg-muted/50"
                autoFocus
              />
            </div>
            <div className="py-1">
              <div
                onClick={() => {
                  onChange("none");
                  setOpen(false);
                  setSearch("");
                }}
                className={`relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 px-2 text-xs outline-hidden hover:bg-accent hover:text-accent-foreground ${
                  (value === "none" || !value) ? "bg-accent/40 font-bold" : ""
                }`}
              >
                Sin supervisor (Jerarquía superior)
              </div>
              {filteredEmployees.map((e) => (
                <div
                  key={e.id}
                  onClick={() => {
                    onChange(e.id);
                    setOpen(false);
                    setSearch("");
                  }}
                  className={`relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 px-2 text-xs outline-hidden hover:bg-accent hover:text-accent-foreground ${
                    value === e.id ? "bg-accent/40 font-bold" : ""
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="font-medium">{e.full_name || "Sin Nombre"}</span>
                    <span className="text-[10px] text-muted-foreground">{e.email}</span>
                  </div>
                </div>
              ))}
              {filteredEmployees.length === 0 && (
                <div className="text-[10px] text-muted-foreground p-2 text-center">
                  No se encontraron resultados
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function getInitials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase() || "?";
}

function formatDate(dateStr: string | null | undefined) {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString("es-ES", {
    year: "numeric", month: "short", day: "numeric",
  });
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    approved: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    rejected: "bg-rose-500/10 text-rose-500 border-rose-500/20",
    pending: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    completed: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    in_progress: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    open: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    closed: "bg-slate-500/10 text-slate-500 border-slate-500/20",
    active: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    enrolled: "bg-violet-500/10 text-violet-500 border-violet-500/20",
  };
  return `text-[10px] font-bold px-2 py-0.5 rounded-full border ${map[status] || "bg-muted text-muted-foreground border-border"}`;
}

function ListCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="backdrop-blur-md bg-card/50 border-border/50 shadow-md">
      <CardHeader className="pb-3 border-b">
        <CardTitle className="text-sm font-bold flex items-center gap-2 text-primary">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        {children}
      </CardContent>
    </Card>
  );
}

export default function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useUser();
  const isAdmin = user?.role === "hr_admin" || user?.role === "super_admin";
  const [tab, setTab] = useState<TabId>("info");
  const [historySheetOpen, setHistorySheetOpen] = useState(false);
  const [editingHistoryEntry, setEditingHistoryEntry] = useState<HistoryEntry | null>(null);
  const [historyForm, setHistoryForm] = useState(EMPTY_HISTORY);

  const [editSheetOpen, setEditSheetOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const [newRole, setNewRole] = useState("employee");

  const { data: employee, isLoading: loadingEmp } = useQuery<Employee>({
    queryKey: ["employee", id],
    queryFn: () => UserAPI.getEmployee(id),
  });

  const { data: history, isLoading: loadingHistory } = useQuery<HistoryEntry[]>({
    queryKey: ["employee-history", id],
    queryFn: () => HistoryAPI.getHistory(id),
    enabled: tab === "history",
  });

  const { data: allEmployees } = useQuery<Employee[]>({
    queryKey: ["employees"],
    queryFn: UserAPI.getEmployees,
  });

  const { data: profile } = useQuery<any>({
    queryKey: ["employee-profile", id],
    queryFn: () => UserAPI.getEmployeeProfile(id),
    enabled: tab === "info",
  });

  const { data: employeeRoles, refetch: refetchRoles } = useQuery<{ roles: string[] }>({
    queryKey: ["employee-roles", id],
    queryFn: () => UserAPI.getEmployeeRoles(id),
    enabled: tab === "roles" && isAdmin,
  });

  const { data: timeOffData, isLoading: loadingTimeoff } = useQuery<any>({
    queryKey: ["employee-timeoff", id],
    queryFn: () => UserAPI.getEmployeeTimeOff(id),
    enabled: tab === "timeoff",
  });

  const { data: ticketsData, isLoading: loadingTickets } = useQuery<any>({
    queryKey: ["employee-tickets", id],
    queryFn: () => UserAPI.getEmployeeItTickets(id),
    enabled: tab === "tickets",
  });

  const { data: reviewsData, isLoading: loadingReviews } = useQuery<any>({
    queryKey: ["employee-reviews", id],
    queryFn: () => UserAPI.getEmployeePerformance(id),
    enabled: tab === "reviews",
  });

  const { data: documentsData, isLoading: loadingDocs } = useQuery<any>({
    queryKey: ["employee-documents", id],
    queryFn: () => UserAPI.getEmployeeDocuments(id),
    enabled: tab === "documents",
  });

  const { data: trainingData, isLoading: loadingTraining } = useQuery<any>({
    queryKey: ["employee-training", id],
    queryFn: () => UserAPI.getEmployeeTraining(id),
    enabled: tab === "training",
  });

  const { data: kudosData, isLoading: loadingKudos } = useQuery<any>({
    queryKey: ["employee-kudos", id],
    queryFn: () => UserAPI.getEmployeeKudos(id),
    enabled: tab === "kudos",
  });

  const archiveMutation = useMutation({
    mutationFn: () =>
      employee?.is_active
        ? UserAPI.archiveEmployee(id)
        : UserAPI.updateEmployee(id, { is_active: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee", id] });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      toast.success(employee?.is_active ? "Empleado archivado correctamente" : "Empleado reactivado correctamente");
    },
    onError: () => toast.error("Error al modificar el estado del empleado"),
  });

  const assignRoleMutation = useMutation({
    mutationFn: (role: string) => UserAPI.assignRole(id, role),
    onSuccess: () => {
      refetchRoles();
      queryClient.invalidateQueries({ queryKey: ["employee", id] });
      toast.success("Rol asignado correctamente");
    },
    onError: (err: any) => toast.error(err.message || "Error al asignar rol"),
  });

  const removeRoleMutation = useMutation({
    mutationFn: (role: string) => UserAPI.removeRole(id, role),
    onSuccess: () => {
      refetchRoles();
      queryClient.invalidateQueries({ queryKey: ["employee", id] });
      toast.success("Rol eliminado correctamente");
    },
    onError: (err: any) => toast.error(err.message || "Error al eliminar rol"),
  });

  const addHistoryMutation = useMutation({
    mutationFn: (data: typeof EMPTY_HISTORY) =>
      HistoryAPI.addEntry(id, {
        ...data,
        salary: data.salary ? parseFloat(data.salary) : undefined,
        end_date: data.end_date || undefined,
        notes: data.notes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee-history", id] });
      setHistorySheetOpen(false);
      setHistoryForm(EMPTY_HISTORY);
      toast.success("Entrada del historial laboral creada correctamente");
    },
    onError: () => toast.error("Error al crear la entrada en el historial"),
  });

  const updateHistoryMutation = useMutation({
    mutationFn: ({ entryId, data }: { entryId: string; data: typeof EMPTY_HISTORY }) =>
      HistoryAPI.updateEntry(id, entryId, {
        ...data,
        salary: data.salary ? parseFloat(data.salary) : undefined,
        end_date: data.end_date || undefined,
        notes: data.notes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee-history", id] });
      setHistorySheetOpen(false);
      setHistoryForm(EMPTY_HISTORY);
      setEditingHistoryEntry(null);
      toast.success("Entrada del historial laboral actualizada correctamente");
    },
    onError: () => toast.error("Error al actualizar la entrada en el historial"),
  });

  const deleteHistoryMutation = useMutation({
    mutationFn: (entryId: string) => HistoryAPI.deleteEntry(id, entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee-history", id] });
      toast.success("Entrada del historial eliminada");
    },
    onError: () => toast.error("Error al eliminar la entrada"),
  });

  const supervisor = useMemo(() => {
    if (!employee || !allEmployees) return null;
    return allEmployees.find((e) => e.id === employee.manager_id) || null;
  }, [employee, allEmployees]);

  const subordinates = useMemo(() => {
    if (!employee || !allEmployees) return [];
    return allEmployees.filter((e) => e.manager_id === employee.id);
  }, [employee, allEmployees]);

  const salaryTrend = useMemo(() => {
    if (!history) return [];
    return history
      .filter((h) => h.salary !== undefined && h.salary !== null)
      .map((h) => ({
        dateStr: h.start_date,
        salary: Number(h.salary),
        position: h.position,
      }))
      .sort((a, b) => new Date(a.dateStr).getTime() - new Date(b.dateStr).getTime());
  }, [history]);

  const salaryChartData = useMemo(() => {
    if (salaryTrend.length === 0) return null;
    const salaries = salaryTrend.map((s) => s.salary);
    const maxVal = Math.max(...salaries, 50000);
    const minVal = Math.min(...salaries, 10000) * 0.9;
    const range = maxVal - minVal || 10000;
    const points = salaryTrend.map((item, idx) => {
      const x = salaryTrend.length > 1 ? (idx / (salaryTrend.length - 1)) * 90 + 5 : 50;
      const y = 80 - ((item.salary - minVal) / range) * 60;
      return { x, y, ...item };
    });
    return { points, maxVal, minVal };
  }, [salaryTrend]);

  const openAddHistory = () => {
    setEditingHistoryEntry(null);
    setHistoryForm(EMPTY_HISTORY);
    setHistorySheetOpen(true);
  };

  const openEditHistory = (entry: HistoryEntry) => {
    setEditingHistoryEntry(entry);
    setHistoryForm({
      position: entry.position || "",
      department: entry.department || "",
      salary: entry.salary ? String(entry.salary) : "",
      currency: entry.currency || "EUR",
      start_date: entry.start_date ? entry.start_date.split("T")[0] : "",
      end_date: entry.end_date ? entry.end_date.split("T")[0] : "",
      notes: entry.notes || "",
    });
    setHistorySheetOpen(true);
  };

  const handleHistorySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingHistoryEntry) {
      updateHistoryMutation.mutate({ entryId: editingHistoryEntry.id, data: historyForm });
    } else {
      addHistoryMutation.mutate(historyForm);
    }
  };

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Employee>) =>
      UserAPI.updateEmployee(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee", id] });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setEditSheetOpen(false);
      toast.success("Empleado actualizado correctamente");
    },
    onError: () => {
      toast.error("Error al actualizar el empleado.");
    }
  });

  const openEdit = () => {
    if (!employee) return;
    setForm({
      email: employee.email,
      full_name: employee.full_name || "",
      department: employee.department || "",
      role: employee.role,
      is_active: employee.is_active,
      phone_number: employee.phone_number || "",
      address: employee.address || "",
      iban: employee.iban || "",
      social_security_number: employee.social_security_number || "",
      emergency_contact: employee.emergency_contact || "",
      contract_type: employee.contract_type || "Indefinido",
      hire_date: employee.hire_date ? new Date(employee.hire_date).toISOString().split("T")[0] : "",
      base_salary: employee.base_salary ?? 50000,
      country: employee.country || "ES",
      manager_id: employee.manager_id || "none",
    });
    setEditSheetOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.iban) {
      const cleanIban = form.iban.replace(/\s+/g, "").toUpperCase();
      if (!/^ES\d{22}$/.test(cleanIban)) {
        toast.error("Por favor, introduce un IBAN español válido (ES seguido de 22 números)");
        return;
      }
    }
    const payload = {
      ...form,
      base_salary: form.base_salary ? parseFloat(form.base_salary as any) : 50000,
      manager_id: form.manager_id === "none" || form.manager_id === "" ? null : form.manager_id,
      hire_date: form.hire_date ? new Date(form.hire_date).toISOString() : null,
    };
    updateMutation.mutate(payload);
  };

  const isIbanValid = useMemo(() => {
    if (!form.iban) return true;
    const cleanIban = form.iban.replace(/\s+/g, "").toUpperCase();
    return /^ES\d{22}$/.test(cleanIban);
  }, [form.iban]);

  const displayRoles = employeeRoles?.roles || (employee?.roles as string[]) || [employee?.role || "employee"];

  if (loadingEmp) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="text-sm font-medium">Cargando la ficha de personal...</span>
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-20 text-muted-foreground space-y-4">
        <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
        <h3 className="text-lg font-bold">Empleado no encontrado</h3>
        <p className="text-sm">El registro solicitado no existe o ha sido eliminado.</p>
        <Button id="back-btn" variant="outline" size="sm" onClick={() => router.push("/dashboard/employees")}>
          Volver al Centro de Personal
        </Button>
      </div>
    );
  }

  const displayName = employee.full_name || employee.email;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <Button id="back-btn" variant="ghost" size="sm" onClick={() => router.push("/dashboard/employees")} className="gap-2 -ml-2 text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" /> Volver a Personal
      </Button>

      {/* Hero Header */}
      <div className="relative rounded-3xl overflow-hidden border border-border/50 bg-gradient-to-br from-primary/10 via-card/50 to-background/90 p-6 sm:p-8 shadow-xl">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -mr-16 -mt-16" />
        <div className="absolute bottom-0 left-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl -ml-8 -mb-8" />
        <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/30 flex items-center justify-center shrink-0 shadow-lg relative group overflow-hidden">
            <div className="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <span className="text-3xl font-extrabold text-primary select-none transform group-hover:scale-105 transition-transform duration-300">
              {getInitials(displayName)}
            </span>
          </div>
          <div className="flex-1 min-w-0 space-y-2">
            <div className="space-y-1">
              <h2 className="text-3xl font-extrabold tracking-tight truncate bg-gradient-to-r from-foreground via-foreground/90 to-foreground/80 bg-clip-text">
                {displayName}
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                {displayRoles.map((r: string) => (
                  <Badge key={r} variant="outline" className="capitalize text-xs font-semibold px-2 py-0.5 border-border/80 flex items-center gap-1">
                    <Briefcase className="w-3.5 h-3.5 text-primary" />
                    {r.replace(/_/g, " ")}
                  </Badge>
                ))}
                {employee.department && (
                  <Badge variant="outline" className="text-xs font-semibold px-2 py-0.5 border-border/80 flex items-center gap-1">
                    <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
                    {employee.department}
                  </Badge>
                )}
                {employee.is_active ? (
                  <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 text-xs font-bold px-2 py-0.5">
                    ● Activo
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs px-2 py-0.5">
                    ○ Archivado
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground pt-1">
              <span className="flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer" onClick={() => { navigator.clipboard.writeText(employee.email); toast.success("Correo copiado"); }}>
                <Mail className="w-3.5 h-3.5" /> {employee.email}
              </span>
              {employee.phone_number && (
                <span className="flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5" /> {employee.phone_number}
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" /> Alta: {employee.hire_date ? formatDate(employee.hire_date) : formatDate(employee.created_at)}
              </span>
            </div>
          </div>
          {isAdmin && (
            <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
              <Button
                id="edit-info-btn"
                variant="outline"
                size="sm"
                className="gap-2 border-border/80 shadow-xs transition-all hover:bg-muted/80"
                onClick={openEdit}
              >
                <Pencil className="w-4 h-4 text-primary" />
                Editar Información
              </Button>
              <Button
                id="archive-btn"
                variant={employee.is_active ? "outline" : "default"}
                size="sm"
                className="gap-2 border-border/80 shadow-xs transition-all hover:bg-muted/80"
                onClick={() => {
                  if (confirm(employee.is_active ? "¿Archivar este empleado?" : "¿Reactivar este empleado?")) {
                    archiveMutation.mutate();
                  }
                }}
                disabled={archiveMutation.isPending}
              >
                {archiveMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : employee.is_active ? (
                  <Archive className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <RotateCcw className="w-4 h-4 text-primary" />
                )}
                {employee.is_active ? "Archivar Ficha" : "Reactivar Ficha"}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex flex-wrap gap-1 border-b border-border/80">
        {TAB_DEFS.filter((t) => !t.adminOnly || isAdmin).map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              id={`tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2.5 text-xs font-semibold transition-all border-b-2 -mb-px flex items-center gap-1.5 whitespace-nowrap ${
                tab === t.id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ===== TAB: info ===== */}
      {tab === "info" && (
        <div className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="backdrop-blur-md bg-card/50 border-border/50 shadow-md">
              <CardHeader className="pb-3 border-b">
                <CardTitle className="text-sm font-bold flex items-center gap-2 text-primary">
                  <User className="h-4.5 w-4.5" /> Datos Personales e Identificación
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                {[
                  { label: "Nombre Completo", value: employee.full_name || "—" },
                  { label: "Email Corporativo", value: employee.email },
                  { label: "Teléfono Móvil", value: profile?.phone || employee.phone_number || "—" },
                  { label: "Dirección Habitual", value: profile?.address || employee.address || "—", icon: MapPin },
                  { label: "Contacto de Emergencia", value: profile?.emergency_contact || employee.emergency_contact || "—" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex flex-col gap-0.5 pb-2 border-b border-border/30 last:border-0 last:pb-0">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">{label}</span>
                    <span className="text-sm font-medium">{value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card className="backdrop-blur-md bg-card/50 border-border/50 shadow-md">
              <CardHeader className="pb-3 border-b">
                <CardTitle className="text-sm font-bold flex items-center gap-2 text-primary">
                  <Briefcase className="h-4.5 w-4.5" /> Cumplimiento y Datos Contractuales
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                {[
                  { label: "Roles Asignados", value: displayRoles.map((r: string) => r.replace(/_/g, " ")).join(", ") },
                  { label: "Departamento", value: profile?.department || employee.department || "—" },
                  { label: "Tipo de Contrato", value: profile?.contract_type || employee.contract_type || "Indefinido (Ordinario)" },
                  { label: "Nº de Seguridad Social (NUSS)", value: profile?.tax_id || employee.social_security_number || "—", icon: Shield },
                  { label: "IBAN de Pago", value: profile?.bank_iban || employee.iban || "—", icon: CreditCard },
                  { label: "Salario Base Anual", value: profile?.base_salary ? `${profile.base_salary.toLocaleString("es-ES")} EUR` : employee.base_salary ? `${employee.base_salary.toLocaleString("es-ES")} EUR` : "50.000 EUR", icon: DollarSign },
                  { label: "País Fiscal", value: profile?.country || employee.country || "ES" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex flex-col gap-0.5 pb-2 border-b border-border/30 last:border-0 last:pb-0">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">{label}</span>
                    <span className="text-sm font-medium capitalize">{value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Organigrama */}
          <Card className="backdrop-blur-md bg-card/50 border-border/50 shadow-md">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-sm font-bold flex items-center gap-2 text-primary">
                <Network className="h-4.5 w-4.5" /> Organigrama Directo y Jerarquía de Reporte
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <div className="flex flex-col items-center">
                <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2">Reporta a (Supervisor)</h4>
                {supervisor ? (
                  <div
                    onClick={() => router.push(`/dashboard/employees/${supervisor.id}`)}
                    className="flex items-center gap-3 bg-muted/40 hover:bg-muted/80 border border-border/60 rounded-xl p-3.5 w-full sm:max-w-md cursor-pointer transition-all shadow-xs"
                  >
                    <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 text-xs font-bold text-primary">
                      {getInitials(supervisor.full_name || supervisor.email)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-bold truncate text-foreground">{supervisor.full_name || "Sin Nombre"}</div>
                      <div className="text-xs text-muted-foreground truncate capitalize">{supervisor.role?.replace(/_/g, " ")} ({supervisor.department || "Sin Dept"})</div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground italic bg-muted/20 border border-dashed rounded-xl py-3 px-6 w-full sm:max-w-md text-center">
                    Sin supervisor directo asignado (Nivel Superior)
                  </div>
                )}
              </div>
              <div className="flex justify-center text-primary/40 -my-2">
                <ArrowDown className="w-5 h-5 animate-pulse" />
              </div>
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-3 bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/40 rounded-xl p-4 w-full sm:max-w-md shadow-md ring-2 ring-primary/15 relative">
                  <div className="absolute top-1/2 -left-1.5 -translate-y-1/2 w-3 h-3 bg-primary rounded-full border border-card" />
                  <div className="w-10 h-10 rounded-lg bg-primary/25 border border-primary/30 flex items-center justify-center shrink-0 text-xs font-extrabold text-primary">
                    {getInitials(displayName)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-extrabold text-foreground truncate">{displayName}</div>
                    <div className="text-xs text-primary/80 font-semibold truncate capitalize">{employee.role?.replace(/_/g, " ")} ({employee.department || "Sin Dept"})</div>
                  </div>
                  <Badge className="bg-primary/20 text-primary border-primary/35 hover:bg-primary/25 text-[9px] font-bold tracking-wider">TÚ</Badge>
                </div>
              </div>
              <div className="flex justify-center text-primary/40 -my-2">
                <ArrowDown className="w-5 h-5 animate-pulse" />
              </div>
              <div className="flex flex-col items-center">
                <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2">Colaboradores Directos ({subordinates.length})</h4>
                {subordinates.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl justify-center">
                    {subordinates.map((sub) => (
                      <div
                        key={sub.id}
                        onClick={() => router.push(`/dashboard/employees/${sub.id}`)}
                        className="flex items-center gap-3 bg-muted/40 hover:bg-muted/85 border border-border/60 rounded-xl p-3 cursor-pointer transition-all shadow-xs"
                      >
                        <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 text-xs font-bold text-primary">
                          {getInitials(sub.full_name || sub.email)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-bold truncate text-foreground">{sub.full_name || "Sin Nombre"}</div>
                          <div className="text-[10px] text-muted-foreground truncate capitalize">{sub.role?.replace(/_/g, " ")}</div>
                        </div>
                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground italic bg-muted/20 border border-dashed rounded-xl py-3 px-6 w-full sm:max-w-md text-center">
                    No cuenta con colaboradores directos a su cargo
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ===== TAB: history ===== */}
      {tab === "history" && (
        <div className="space-y-6">
          {salaryChartData && (
            <Card className="backdrop-blur-md bg-card/50 border-border/50 shadow-md">
              <CardHeader className="pb-2 border-b">
                <CardTitle className="text-sm font-bold flex items-center gap-2 text-primary">
                  <TrendingUp className="h-4.5 w-4.5" /> Evolución Histórica del Salario Base
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 pb-2">
                <div className="relative w-full overflow-hidden rounded-xl bg-muted/10 p-2 border border-border/20">
                  <svg className="w-full h-40" viewBox="0 0 100 100" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="salary-gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
                        <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>
                    {salaryChartData.points.length > 1 && (
                      <path
                        d={`M ${salaryChartData.points[0].x} 95 L ${salaryChartData.points
                          .map((p: any) => `${p.x} ${p.y}`)
                          .join(" L ")} L ${salaryChartData.points[salaryChartData.points.length - 1].x} 95 Z`}
                        fill="url(#salary-gradient)"
                      />
                    )}
                    <line x1="0" y1="20" x2="100" y2="20" stroke="currentColor" strokeOpacity="0.05" strokeDasharray="3" />
                    <line x1="0" y1="50" x2="100" y2="50" stroke="currentColor" strokeOpacity="0.05" strokeDasharray="3" />
                    <line x1="0" y1="80" x2="100" y2="80" stroke="currentColor" strokeOpacity="0.05" strokeDasharray="3" />
                    {salaryChartData.points.length > 1 ? (
                      <path
                        d={`M ${salaryChartData.points.map((p: any) => `${p.x} ${p.y}`).join(" L ")}`}
                        fill="none"
                        stroke="hsl(var(--primary))"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    ) : (
                      <line x1="5" y1="50" x2="95" y2="50" stroke="hsl(var(--primary))" strokeWidth="2.5" strokeDasharray="4" />
                    )}
                    {salaryChartData.points.map((p: any, idx: number) => (
                      <g key={idx} className="cursor-pointer group/node">
                        <circle cx={p.x} cy={p.y} r="4.5" fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth="2" />
                        <circle cx={p.x} cy={p.y} r="2.5" fill="hsl(var(--primary))" />
                        <circle cx={p.x} cy={p.y} r="8" fill="hsl(var(--primary))" fillOpacity="0.0" className="hover:fill-opacity-10 transition-all duration-200" />
                      </g>
                    ))}
                  </svg>
                  <div className="absolute inset-x-0 bottom-2 flex justify-between px-6 text-[9px] text-muted-foreground">
                    <span>{formatDate(salaryTrend[0].dateStr)}</span>
                    <span className="font-semibold text-primary">Sueldo más alto: {salaryChartData.maxVal.toLocaleString("es-ES")} €</span>
                    <span>{formatDate(salaryTrend[salaryTrend.length - 1].dateStr)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          <div className="flex justify-between items-center">
            <div>
              <h4 className="text-sm font-bold text-foreground">Timeline de Cambios Contractuales</h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                Historial de posiciones, traslados de departamentos y salarios ordenados retrospectivamente.
              </p>
            </div>
            <Button id="add-history-btn" size="sm" className="gap-2 shadow-sm" onClick={openAddHistory}>
              <Plus className="h-4 w-4" /> Añadir Entrada al Historial
            </Button>
          </div>
          {loadingHistory && (
            <div className="flex items-center gap-2 text-muted-foreground py-16 justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando el historial laboral...
            </div>
          )}
          {!loadingHistory && (!history || history.length === 0) && (
            <Card className="backdrop-blur-md bg-card/50 border-border/50 border-dashed">
              <CardContent className="py-14 text-center text-muted-foreground text-sm">
                <Clock className="w-10 h-10 mx-auto mb-3 opacity-40 text-primary" />
                <p className="font-semibold">Sin historial laboral registrado</p>
                <p className="text-xs mt-1">Añade la primera posición contractual para registrar su evolución salarial y de cargos.</p>
                <Button variant="outline" size="sm" className="mt-4 gap-1.5" onClick={openAddHistory}>
                  <Plus className="w-3.5 h-3.5" /> Registrar Primer Cargo
                </Button>
              </CardContent>
            </Card>
          )}
          {history && history.length > 0 && (
            <div className="relative pl-6">
              <div className="absolute left-9 top-4 bottom-4 w-0.5 bg-border/80" />
              <div className="space-y-5">
                {history.map((entry, idx) => (
                  <div key={entry.id} className="relative flex gap-4 group">
                    <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center shrink-0 z-10 shadow-xs transition-colors ${
                      !entry.end_date ? "bg-primary border-primary text-primary-foreground" : "bg-card border-border text-muted-foreground"
                    }`}>
                      <Briefcase className="w-3.5 h-3.5" />
                    </div>
                    <Card className="flex-1 backdrop-blur-md bg-card/50 border-border/50 hover:border-primary/40 transition-all duration-300 shadow-xs relative">
                      <CardContent className="py-4 px-5">
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-2 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-bold text-sm text-foreground">{entry.position}</span>
                              {!entry.end_date && (
                                <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 text-[10px] font-bold px-2 py-0.5">
                                  Vigente (Actual)
                                </Badge>
                              )}
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs text-muted-foreground pt-1">
                              {entry.department && (
                                <span className="flex items-center gap-1.5 truncate"><Building2 className="h-3.5 w-3.5 text-primary/70" /> {entry.department}</span>
                              )}
                              {entry.salary && (
                                <span className="flex items-center gap-1.5 font-bold text-foreground"><DollarSign className="h-3.5 w-3.5 text-amber-500" /> {entry.salary.toLocaleString("es-ES")} {entry.currency} / año</span>
                              )}
                              <span className="flex items-center gap-1.5 truncate"><Calendar className="h-3.5 w-3.5 text-primary/70" /> {formatDate(entry.start_date)}{entry.end_date ? ` → ${formatDate(entry.end_date)}` : " → Presente"}</span>
                            </div>
                            {entry.notes && (
                              <p className="text-xs text-muted-foreground/90 italic border-l-2 border-primary/30 pl-3 mt-2 py-0.5 bg-muted/15 rounded-r">{entry.notes}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                            <Button id={`edit-history-${entry.id}`} variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all" onClick={() => openEditHistory(entry)}>
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button id={`delete-history-${entry.id}`} variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive transition-all" onClick={() => {
                              if (confirm("¿Estás seguro de que deseas eliminar esta entrada del historial laboral?")) { deleteHistoryMutation.mutate(entry.id); }
                            }}>
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== TAB: timeoff ===== */}
      {tab === "timeoff" && (
        <ListCard title={<><Umbrella className="h-4.5 w-4.5" /> Historial de Ausencias y Permisos</>}>
          {loadingTimeoff ? (
            <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando...</div>
          ) : timeOffData?.requests?.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {timeOffData.requests.map((r: any) => (
                <div key={r.id} className="flex items-center justify-between p-3 rounded-xl border border-border/30 bg-muted/20">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold">{r.reason || r.type || "Ausencia"}</p>
                    <p className="text-xs text-muted-foreground">{r.start_date ? formatDate(r.start_date) : "—"} → {r.end_date ? formatDate(r.end_date) : "—"}</p>
                  </div>
                  <span className={statusBadge(r.status)}>{r.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-muted-foreground">
              <Umbrella className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Sin solicitudes de ausencia registradas</p>
            </div>
          )}
        </ListCard>
      )}

      {/* ===== TAB: tickets ===== */}
      {tab === "tickets" && (
        <ListCard title={<><Ticket className="h-4.5 w-4.5" /> Tickets de IT Enviados</>}>
          {loadingTickets ? (
            <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando...</div>
          ) : ticketsData?.tickets?.length > 0 || ticketsData?.items?.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {(ticketsData?.tickets || ticketsData?.items || []).map((t: any) => (
                <div key={t.id} className="flex items-center justify-between p-3 rounded-xl border border-border/30 bg-muted/20">
                  <div className="space-y-1 flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{t.title}</p>
                    <p className="text-xs text-muted-foreground">{t.category || ""} — {t.priority || ""}</p>
                    <p className="text-xs text-muted-foreground truncate">{t.description?.slice(0, 80)}</p>
                  </div>
                  <span className={statusBadge(t.status || "open")}>{t.status || "open"}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-muted-foreground">
              <Ticket className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Sin tickets de IT registrados</p>
            </div>
          )}
        </ListCard>
      )}

      {/* ===== TAB: reviews ===== */}
      {tab === "reviews" && (
        <ListCard title={<><Star className="h-4.5 w-4.5" /> Evaluaciones de Desempeño</>}>
          {loadingReviews ? (
            <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando...</div>
          ) : reviewsData?.reviews?.length > 0 || reviewsData?.items?.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {(reviewsData?.reviews || reviewsData?.items || []).map((r: any) => (
                <div key={r.id} className="p-3 rounded-xl border border-border/30 bg-muted/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold">{r.title || r.type || "Evaluación"}</p>
                    <span className={statusBadge(r.status || r.result || "pending")}>{r.status || r.result || "pending"}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{r.feedback || r.notes || r.summary || "Sin comentarios"}</p>
                  {r.score != null && <p className="text-xs font-bold text-primary">Puntuación: {r.score}/5</p>}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-muted-foreground">
              <Star className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Sin evaluaciones de desempeño registradas</p>
            </div>
          )}
        </ListCard>
      )}

      {/* ===== TAB: documents ===== */}
      {tab === "documents" && (
        <ListCard title={<><FileText className="h-4.5 w-4.5" /> Documentos (Contratos, NDAs, Certificaciones)</>}>
          {loadingDocs ? (
            <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando...</div>
          ) : documentsData?.documents?.length > 0 || documentsData?.items?.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {(documentsData?.documents || documentsData?.items || []).map((d: any) => (
                <div key={d.id} className="flex items-center justify-between p-3 rounded-xl border border-border/30 bg-muted/20">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="w-5 h-5 text-primary shrink-0" />
                    <div className="space-y-0.5 min-w-0">
                      <p className="text-sm font-semibold truncate">{d.name || d.title || d.filename || "Documento"}</p>
                      <p className="text-xs text-muted-foreground">{d.type || d.category || ""} — {d.created_at ? formatDate(d.created_at) : ""}</p>
                    </div>
                  </div>
                  <span className={statusBadge(d.status || "active")}>{d.status || "active"}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-muted-foreground">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Sin documentos registrados</p>
            </div>
          )}
        </ListCard>
      )}

      {/* ===== TAB: training ===== */}
      {tab === "training" && (
        <ListCard title={<><GraduationCap className="h-4.5 w-4.5" /> Cursos de Formación</>}>
          {loadingTraining ? (
            <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando...</div>
          ) : trainingData?.enrollments?.length > 0 || trainingData?.items?.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {(trainingData?.enrollments || trainingData?.items || []).map((e: any) => (
                <div key={e.id} className="flex items-center justify-between p-3 rounded-xl border border-border/30 bg-muted/20">
                  <div className="space-y-1 flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{e.course_name || e.course_title || e.title || "Curso"}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{e.progress_percentage != null ? `${e.progress_percentage}%` : ""}</span>
                      {e.score != null && <span>Nota: {e.score}</span>}
                      {e.completed_at && <span>Completado: {formatDate(e.completed_at)}</span>}
                    </div>
                  </div>
                  <span className={statusBadge(e.status || "enrolled")}>{e.status || "enrolled"}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-muted-foreground">
              <GraduationCap className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Sin cursos de formación registrados</p>
            </div>
          )}
        </ListCard>
      )}

      {/* ===== TAB: kudos ===== */}
      {tab === "kudos" && (
        <ListCard title={<><Activity className="h-4.5 w-4.5" /> Kudos Recibidos</>}>
          {loadingKudos ? (
            <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando...</div>
          ) : kudosData?.kudos?.length > 0 || kudosData?.items?.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {(kudosData?.kudos || kudosData?.items || []).map((k: any) => (
                <div key={k.id} className="p-3 rounded-xl border border-border/30 bg-muted/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold">{k.from_name || k.sender_name || "Compañero"}</p>
                    <span className="text-xs text-muted-foreground">{k.created_at ? formatDate(k.created_at) : ""}</span>
                  </div>
                  <p className="text-xs text-muted-foreground italic">&ldquo;{k.message || k.reason || "Sin mensaje"}&rdquo;</p>
                  {k.category && <Badge variant="outline" className="text-[10px]">{k.category}</Badge>}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-muted-foreground">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Sin kudos recibidos</p>
            </div>
          )}
        </ListCard>
      )}

      {/* ===== TAB: roles ===== */}
      {tab === "roles" && isAdmin && (
        <div className="space-y-6">
          <ListCard title={<><ShieldCheck className="h-4.5 w-4.5" /> Gestión de Roles y Permisos</>}>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Roles Actuales</Label>
                <div className="flex flex-wrap gap-2">
                  {displayRoles.map((r: string) => (
                    <Badge key={r} className="capitalize text-sm px-3 py-1.5 gap-2 bg-primary/10 text-primary border-primary/20">
                      {r.replace(/_/g, " ")}
                      {r !== "employee" || displayRoles.length > 1 ? (
                        <button
                          onClick={() => {
                            if (confirm(`¿Eliminar el rol "${r}" de este empleado?`)) {
                              removeRoleMutation.mutate(r);
                            }
                          }}
                          className="hover:text-destructive transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      ) : null}
                    </Badge>
                  ))}
                  {displayRoles.length === 0 && (
                    <span className="text-xs text-muted-foreground italic">Sin roles asignados</span>
                  )}
                </div>
              </div>
              <div className="flex items-end gap-3 pt-2 border-t border-border/30">
                <div className="space-y-2 flex-1">
                  <Label htmlFor="new-role-select" className="text-xs font-semibold text-muted-foreground">Asignar Nuevo Rol</Label>
                  <Select value={newRole} onValueChange={setNewRole}>
                    <SelectTrigger id="new-role-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {VALID_ROLES.filter((r) => !displayRoles.includes(r)).map((r) => (
                        <SelectItem key={r} value={r}>{r.replace(/_/g, " ")}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  size="sm"
                  onClick={() => assignRoleMutation.mutate(newRole)}
                  disabled={assignRoleMutation.isPending || displayRoles.includes(newRole)}
                  className="gap-1.5"
                >
                  {assignRoleMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                  Asignar
                </Button>
              </div>
            </div>
          </ListCard>
        </div>
      )}

      {/* History Sheet */}
      <Sheet open={historySheetOpen} onOpenChange={(open) => { setHistorySheetOpen(open); if (!open) setEditingHistoryEntry(null); }}>
        <SheetContent className="w-full sm:max-w-md">
          <SheetHeader className="pb-3 border-b">
            <SheetTitle className="text-lg font-bold">
              {editingHistoryEntry ? "Editar Entrada de Historial" : "Registrar Entrada Contractual"}
            </SheetTitle>
            <SheetDescription>
              {editingHistoryEntry
                ? `Modifica los datos retrospectivos de cargo y salario de ${displayName}.`
                : `Registra un nuevo cargo, departamento o salario base para ${displayName}.`}
            </SheetDescription>
          </SheetHeader>
          <form id="history-form" className="space-y-4 py-6" onSubmit={handleHistorySubmit}>
            <div className="space-y-2">
              <Label htmlFor="h-position">Cargo o Puesto *</Label>
              <Input id="h-position" required placeholder="Senior Backend Engineer" value={historyForm.position} onChange={(e) => setHistoryForm({ ...historyForm, position: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="h-dept">Departamento</Label>
              <Input id="h-dept" placeholder="Ingeniería / Tecnología" value={historyForm.department} onChange={(e) => setHistoryForm({ ...historyForm, department: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="h-salary">Salario Anual Base (€)</Label>
                <Input id="h-salary" type="number" min="0" placeholder="55000" value={historyForm.salary} onChange={(e) => setHistoryForm({ ...historyForm, salary: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="h-currency">Divisa de Pago</Label>
                <Input id="h-currency" placeholder="EUR" value={historyForm.currency} onChange={(e) => setHistoryForm({ ...historyForm, currency: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="h-start">Fecha de Inicio *</Label>
                <Input id="h-start" type="date" required value={historyForm.start_date} onChange={(e) => setHistoryForm({ ...historyForm, start_date: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="h-end">Fecha de Fin (vacío = Presente)</Label>
                <Input id="h-end" type="date" value={historyForm.end_date} onChange={(e) => setHistoryForm({ ...historyForm, end_date: e.target.value })} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="h-notes">Notas / Motivo de Cambio</Label>
              <Input id="h-notes" placeholder="Promoción interna por méritos, subida salarial de convenio..." value={historyForm.notes} onChange={(e) => setHistoryForm({ ...historyForm, notes: e.target.value })} />
            </div>
          </form>
          <SheetFooter className="pt-4 border-t">
            <Button id="submit-history" type="submit" form="history-form" disabled={addHistoryMutation.isPending || updateHistoryMutation.isPending} className="w-full shadow-sm">
              {addHistoryMutation.isPending || updateHistoryMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              {editingHistoryEntry ? "Guardar Cambios en la Entrada" : "Registrar Entrada Contractual"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Edit Employee Sheet */}
      <Sheet open={editSheetOpen} onOpenChange={setEditSheetOpen}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto max-h-screen">
          <SheetHeader className="pb-4 border-b">
            <SheetTitle className="text-xl font-bold flex items-center gap-2">Editar Ficha de Empleado</SheetTitle>
            <SheetDescription>Actualiza los datos y cumplimiento laboral de {displayName}.</SheetDescription>
          </SheetHeader>
          <form id="employee-edit-form" onSubmit={handleSubmit} className="space-y-6 py-6 pb-20">
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">1. Identidad y Acceso al Sistema</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-email">Email Corporativo *</Label>
                  <Input id="emp-email" type="email" required placeholder="empleado@empresa.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} disabled />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emp-name">Nombre Completo *</Label>
                  <Input id="emp-name" required placeholder="María García Pérez" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-dept">Departamento</Label>
                  <Input id="emp-dept" placeholder="Recursos Humanos" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emp-role">Rol y Permisos</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v || "" })}>
                    <SelectTrigger id="emp-role"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="employee">Empleado</SelectItem>
                      <SelectItem value="hr_admin">HR Admin</SelectItem>
                      <SelectItem value="sys_admin">Sys Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="emp-manager">Supervisor / Reporta a</Label>
                <SearchableSupervisorSelect value={form.manager_id} onChange={(val) => setForm({ ...form, manager_id: val })} employees={allEmployees || []} excludeId={id} />
              </div>
            </div>
            <div className="space-y-4 pt-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">2. Datos de Contacto y Emergencia</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-phone">Teléfono de Contacto</Label>
                  <Input id="emp-phone" placeholder="+34 600 000 000" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emp-emergency">Contacto de Emergencia</Label>
                  <Input id="emp-emergency" placeholder="Juan García (Padre) - 611 222 333" value={form.emergency_contact} onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })} />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="emp-address">Dirección de Residencia</Label>
                <Input id="emp-address" placeholder="Calle Gran Vía 45, 3º B, 28013 Madrid" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
              </div>
            </div>
            <div className="space-y-4 pt-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">3. Cumplimiento Laboral y Bancario (España)</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-contract">Tipo de Contrato</Label>
                  <Select value={form.contract_type} onValueChange={(v) => setForm({ ...form, contract_type: v || "Indefinido" })}>
                    <SelectTrigger id="emp-contract"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Indefinido">Indefinido (Ordinario)</SelectItem>
                      <SelectItem value="Temporal">Temporal</SelectItem>
                      <SelectItem value="Beca">Prácticas / Beca</SelectItem>
                      <SelectItem value="Autónomo">Autónomo / Freelance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emp-hire">Fecha de Contratación</Label>
                  <Input id="emp-hire" type="date" value={form.hire_date} onChange={(e) => setForm({ ...form, hire_date: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-salary">Salario Base Anual (€)</Label>
                  <Input id="emp-salary" type="number" min="0" placeholder="45000" value={form.base_salary} onChange={(e) => setForm({ ...form, base_salary: parseFloat(e.target.value) || 0 })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emp-ssn">Nº de Seguridad Social (NUSS)</Label>
                  <Input id="emp-ssn" placeholder="281234567890" value={form.social_security_number} onChange={(e) => setForm({ ...form, social_security_number: e.target.value })} />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="emp-iban">IBAN Español de Pago</Label>
                  {form.iban && (isIbanValid ? (
                    <span className="text-[10px] text-emerald-500 flex items-center gap-1 font-semibold"><CheckCircle2 className="w-3.5 h-3.5" /> IBAN Español Válido</span>
                  ) : (
                    <span className="text-[10px] text-destructive flex items-center gap-1 font-semibold"><AlertCircle className="w-3.5 h-3.5" /> Formato Incorrecto (ES + 22 dígitos)</span>
                  ))}
                </div>
                <Input id="emp-iban" placeholder="ES91 2100 0418 4502 0005 6789" value={form.iban} onChange={(e) => setForm({ ...form, iban: e.target.value })} className={form.iban && !isIbanValid ? "border-destructive/80 focus-visible:ring-destructive" : ""} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-country">País Fiscal</Label>
                  <Input id="emp-country" placeholder="ES" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase().slice(0, 2) })} />
                </div>
              </div>
            </div>
          </form>
          <SheetFooter className="absolute bottom-0 left-0 right-0 p-6 bg-card border-t z-10">
            <Button id="submit-employee-edit" type="submit" form="employee-edit-form" disabled={updateMutation.isPending || (!!form.iban && !isIbanValid)} className="w-full shadow-lg">
              {updateMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Guardar Cambios en la Ficha
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
