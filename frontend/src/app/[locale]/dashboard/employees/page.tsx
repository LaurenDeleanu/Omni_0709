"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserAPI, Employee } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  MoreHorizontal, Plus, Loader2, Trash2, Archive,
  Search, Users, UserCheck, UserX, ExternalLink, EyeOff, KeyRound,
  LayoutGrid, List, Phone, MapPin, CreditCard, Shield, Calendar, DollarSign,
  Briefcase, Building2, Mail, CheckCircle2, AlertCircle, ArrowUpRight
} from "lucide-react";
import { useState, useMemo } from "react";
import { useRouter } from "@/i18n/routing";
import { InlineCopilot } from "@/components/ai/InlineCopilot";
import { PageHeader } from "@/components/layout/PageHeader";
import { toast } from "sonner";
import { API_BASE } from "@/lib/api/client";
import { useUser } from "@/hooks/use-user";

const EMPTY_FORM = {
  email: "",
  full_name: "",
  department: "",
  role: "employee",
  is_active: true,
  password: "",
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
          {/* Backdrop to close on click outside */}
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          
          <div className="absolute left-0 right-0 mt-1 max-h-60 overflow-y-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md z-40 backdrop-blur-md bg-card/95">
            {/* Search Input */}
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
              {/* Option "Sin supervisor" */}
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
              
              {/* Supervisor list */}
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
  return name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "?";
}

function getDeptGradient(dept: string = "") {
  const normalized = dept.toLowerCase().trim();
  if (normalized.includes("tech") || normalized.includes("it") || normalized.includes("sistemas") || normalized.includes("desarrollo")) {
    return "from-cyan-500/20 to-blue-500/20 border-cyan-500/30 text-cyan-400 dark:text-cyan-300";
  }
  if (normalized.includes("hr") || normalized.includes("recursos") || normalized.includes("personal") || normalized.includes("talento")) {
    return "from-purple-500/20 to-pink-500/20 border-purple-500/30 text-purple-400 dark:text-purple-300";
  }
  if (normalized.includes("ventas") || normalized.includes("sales") || normalized.includes("comercial") || normalized.includes("marketing")) {
    return "from-amber-500/20 to-orange-500/20 border-amber-500/30 text-amber-400 dark:text-amber-300";
  }
  if (normalized.includes("finanzas") || normalized.includes("contabilidad") || normalized.includes("legal") || normalized.includes("admin")) {
    return "from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-400 dark:text-emerald-300";
  }
  return "from-slate-500/20 to-zinc-500/20 border-slate-500/30 text-slate-400 dark:text-slate-300";
}

export default function EmployeesPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { user } = useUser();
  const isAdmin = user?.role === "hr_admin" || user?.role === "super_admin";
  const [viewMode, setViewMode] = useState<"table" | "grid">("grid");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "archived">("all");

  const { data: employees, isLoading, isError } = useQuery<Employee[]>({
    queryKey: ["employees"],
    queryFn: UserAPI.getEmployees,
  });

  const createMutation = useMutation({
    mutationFn: UserAPI.createEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setSheetOpen(false);
      setForm(EMPTY_FORM);
      toast.success("Empleado creado correctamente");
    },
    onError: () => {
      toast.error("Error al crear el empleado. El correo ya existe.");
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Employee> }) =>
      UserAPI.updateEmployee(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setSheetOpen(false);
      setForm(EMPTY_FORM);
      setEditingEmployee(null);
      toast.success("Empleado actualizado correctamente");
    },
    onError: () => {
      toast.error("Error al actualizar el empleado.");
    }
  });

  const archiveMutation = useMutation({
    mutationFn: UserAPI.archiveEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      toast.success("Empleado archivado correctamente");
    },
    onError: () => {
      toast.error("Error al archivar el empleado.");
    }
  });

  const deleteMutation = useMutation({
    mutationFn: UserAPI.deleteEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      toast.success("Empleado eliminado permanentemente");
    },
    onError: () => {
      toast.error("Error al eliminar el empleado.");
    }
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async ({ userId, password }: { userId: string; password: string }) => {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/users/${userId}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) throw new Error("Error al resetear la contraseña");
      return res.json();
    },
    onSuccess: (data) => toast.success(data.message || "Contraseña actualizada"),
    onError: () => toast.error("No se pudo actualizar la contraseña"),
  });

  const openCreate = () => {
    setEditingEmployee(null);
    setForm(EMPTY_FORM);
    setSheetOpen(true);
  };

  const openEdit = (emp: Employee) => {
    setEditingEmployee(emp);
    setForm({
      email: emp.email,
      full_name: emp.full_name || "",
      department: emp.department || "",
      role: emp.role,
      is_active: emp.is_active,
      password: "",
      phone_number: emp.phone_number || "",
      address: emp.address || "",
      iban: emp.iban || "",
      social_security_number: emp.social_security_number || "",
      emergency_contact: emp.emergency_contact || "",
      contract_type: emp.contract_type || "Indefinido",
      hire_date: emp.hire_date ? new Date(emp.hire_date).toISOString().split("T")[0] : "",
      base_salary: emp.base_salary ?? 50000,
      country: emp.country || "ES",
      manager_id: emp.manager_id || "none",
    });
    setSheetOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validar IBAN
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

    if (editingEmployee) {
      updateMutation.mutate({ id: editingEmployee.id, data: payload });
    } else {
      createMutation.mutate(payload as any);
    }
  };

  // Filtered employees
  const filteredEmployees = useMemo(() => {
    if (!employees) return [];
    return employees.filter((emp) => {
      const matchesSearch =
        search === "" ||
        emp.email.toLowerCase().includes(search.toLowerCase()) ||
        (emp.full_name || "").toLowerCase().includes(search.toLowerCase()) ||
        (emp.department || "").toLowerCase().includes(search.toLowerCase());
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && emp.is_active) ||
        (statusFilter === "archived" && !emp.is_active);
      return matchesSearch && matchesStatus;
    });
  }, [employees, search, statusFilter]);

  const totalActive = employees?.filter((e) => e.is_active).length ?? 0;
  const totalArchived = employees?.filter((e) => !e.is_active).length ?? 0;
  const totalCount = employees?.length ?? 0;
  const isMutating = createMutation.isPending || updateMutation.isPending;

  // Analíticas del Centro Analítico Superior
  const activeEmployeesList = useMemo(() => {
    return employees?.filter((e) => e.is_active) ?? [];
  }, [employees]);

  const deptCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    activeEmployeesList.forEach((emp) => {
      const dept = emp.department || "Sin Departamento";
      counts[dept] = (counts[dept] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([name, count]) => ({
        name,
        count,
        percentage: activeEmployeesList.length > 0 ? Math.round((count / activeEmployeesList.length) * 100) : 0,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 3);
  }, [activeEmployeesList]);

  const activityRate = totalCount > 0 ? Math.round((totalActive / totalCount) * 100) : 0;

  const avgSalary = useMemo(() => {
    if (activeEmployeesList.length === 0) return 0;
    const sum = activeEmployeesList.reduce((acc, emp) => acc + (emp.base_salary || 0), 0);
    return Math.round(sum / activeEmployeesList.length);
  }, [activeEmployeesList]);

  // IBAN validator check for real-time feedback
  const isIbanValid = useMemo(() => {
    if (!form.iban) return true;
    const cleanIban = form.iban.replace(/\s+/g, "").toUpperCase();
    return /^ES\d{22}$/.test(cleanIban);
  }, [form.iban]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Centro de Personal"
        description="Gestión integral de la plantilla, cumplimiento laboral español y organigrama."
        action={
          <div className="flex items-center gap-3">
            {/* View switcher */}
            <div className="flex items-center bg-muted/60 border border-border/50 rounded-lg p-1 backdrop-blur-sm">
              <Button
                variant={viewMode === "table" ? "secondary" : "ghost"}
                size="sm"
                className="px-2.5 h-8 gap-1"
                onClick={() => setViewMode("table")}
              >
                <List className="w-4 h-4" />
                <span className="hidden md:inline text-xs">Tabla</span>
              </Button>
              <Button
                variant={viewMode === "grid" ? "secondary" : "ghost"}
                size="sm"
                className="px-2.5 h-8 gap-1"
                onClick={() => setViewMode("grid")}
              >
                <LayoutGrid className="w-4 h-4" />
                <span className="hidden md:inline text-xs">Malla</span>
              </Button>
            </div>

            {isAdmin && (
              <Button id="add-employee-btn" onClick={openCreate} className="gap-2 shadow-lg bg-primary hover:bg-primary/95 transition-all">
                <Plus className="w-4 h-4" /> Añadir Empleado
              </Button>
            )}
          </div>
        }
      />

      <InlineCopilot
        moduleContext="employees"
        placeholder="Pregunta sobre empleados, departamentos o salarios..."
        quickActions={[
          { label: "Mostrar lista de empleados", message: "Mostrar lista de empleados" },
          { label: "Analizar distribución salarial", message: "Analizar distribución salarial" },
          { label: "Generar organigrama", message: "Generar organigrama" },
        ]}
      />

      {/* Centro Analítico Superior */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Widget 1: Headcount por Dept */}
        <Card className="backdrop-blur-md bg-card/40 border-border/50 shadow-md flex flex-col justify-between overflow-hidden relative group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-2xl -mr-6 -mt-6 transition-all group-hover:scale-150 duration-500" />
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
              Distribución de Personal
              <Building2 className="w-4 h-4 text-primary" />
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-3 flex-1 flex flex-col justify-center">
            {deptCounts.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">Sin información de departamentos</p>
            ) : (
              deptCounts.map((dept) => (
                <div key={dept.name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-medium">
                    <span className="truncate max-w-[150px]">{dept.name}</span>
                    <span className="text-muted-foreground">{dept.count} ({dept.percentage}%)</span>
                  </div>
                  <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-500"
                      style={{ width: `${dept.percentage}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Widget 2: Actividad del Personal */}
        <Card className="backdrop-blur-md bg-card/40 border-border/50 shadow-md flex flex-col justify-between overflow-hidden relative group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl -mr-6 -mt-6 transition-all group-hover:scale-150 duration-500" />
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
              Ratio de Actividad
              <UserCheck className="w-4 h-4 text-emerald-500" />
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-1 flex items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="text-3xl font-extrabold tracking-tight">{activityRate}%</div>
              <p className="text-xs text-muted-foreground">
                {totalActive} de {totalCount} en activo
              </p>
            </div>
            {/* SVG Mini Ring */}
            <div className="relative w-16 h-16 shrink-0">
              <svg className="w-full h-full" viewBox="0 0 36 36">
                <path
                  className="text-muted"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className="text-emerald-500 transition-all duration-1000"
                  strokeDasharray={`${activityRate}, 100`}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
            </div>
          </CardContent>
        </Card>

        {/* Widget 3: Coste Salarial Medio */}
        <Card className="backdrop-blur-md bg-card/40 border-border/50 shadow-md flex flex-col justify-between overflow-hidden relative group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-2xl -mr-6 -mt-6 transition-all group-hover:scale-150 duration-500" />
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
              Masa Salarial Activa
              <DollarSign className="w-4 h-4 text-amber-500" />
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-1 flex flex-col justify-center space-y-1">
            <div className="flex items-baseline gap-2">
              <div className="text-3xl font-extrabold tracking-tight">
                {avgSalary.toLocaleString("es-ES")} €
              </div>
              <span className="text-xs font-medium text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded flex items-center gap-0.5">
                PROM <ArrowUpRight className="w-3 h-3" />
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Coste salarial base anual medio por empleado en activo.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Search + Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            id="employee-search"
            placeholder="Buscar por nombre, email, departamento..."
            className="pl-9 bg-card/50 backdrop-blur-xs"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as typeof statusFilter)}>
            <SelectTrigger id="status-filter" className="w-[160px] bg-card/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los Estados</SelectItem>
              <SelectItem value="active">Activos</SelectItem>
              <SelectItem value="archived">Archivados</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Grid View (Malla de Tarjetas Premium) */}
      {viewMode === "grid" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading && (
            <div className="col-span-full py-20 text-center">
              <div className="flex flex-col items-center justify-center gap-3 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="text-sm font-medium">Cargando la plantilla de personal...</span>
              </div>
            </div>
          )}

          {isError && (
            <div className="col-span-full py-16 text-center text-destructive border border-destructive/20 bg-destructive/5 rounded-2xl">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-destructive" />
              <p className="font-semibold">Error al conectar con la base de datos.</p>
              <p className="text-xs text-destructive/70 mt-1">Por favor, asegúrate de que el backend de FastAPI esté en ejecución.</p>
            </div>
          )}

          {!isLoading && !isError && filteredEmployees.length === 0 && (
            <div className="col-span-full py-20 text-center border border-dashed rounded-2xl bg-muted/20">
              <Users className="w-10 h-10 mx-auto text-muted-foreground/60 mb-2" />
              <p className="text-muted-foreground font-medium">
                {search ? `No hay resultados para "${search}".` : "No se han registrado empleados todavía."}
              </p>
            </div>
          )}

          {filteredEmployees.map((emp) => {
            const gradClass = getDeptGradient(emp.department);
            return (
              <div
                key={emp.id}
                onClick={() => router.push(`/dashboard/employees/${emp.id}`)}
                className="group cursor-pointer backdrop-blur-md bg-card/60 border border-border/50 shadow-md hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative rounded-2xl p-5 overflow-hidden flex flex-col justify-between"
              >
                {/* Visual Glow Gradient Accent */}
                <div className="absolute -top-10 -right-10 w-24 h-24 bg-primary/5 rounded-full blur-xl group-hover:scale-150 transition-all duration-500" />
                
                <div>
                  {/* Top line with Avatar & Badges */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      {/* Premium Dynamic Avatar */}
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br border flex items-center justify-center shrink-0 text-sm font-bold shadow-xs transition-transform group-hover:scale-105 ${gradClass}`}>
                        {getInitials(emp.full_name || emp.email)}
                      </div>
                      <div className="min-w-0">
                        <h4 className="font-bold text-base tracking-tight truncate group-hover:text-primary transition-colors">
                          {emp.full_name || "Sin Nombre"}
                        </h4>
                        <span className="text-xs text-muted-foreground truncate block max-w-[150px]">
                          {emp.department || "Sin Departamento"}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                      {emp.is_active ? (
                        <span className="relative flex h-2 w-2 mr-1">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                      ) : (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0.5">○ Archivado</Badge>
                      )}
                      
                      {/* Action Dropdown inside Grid Card */}
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          id={`actions-grid-${emp.id}`}
                          className="h-7 w-7 p-0 flex items-center justify-center rounded-md border hover:bg-muted/80 text-muted-foreground transition-colors"
                        >
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                          <DropdownMenuItem onClick={() => router.push(`/dashboard/employees/${emp.id}`)}>
                            <ExternalLink className="w-4 h-4 mr-2 text-primary" /> Ver Ficha Completa
                          </DropdownMenuItem>
                          {isAdmin && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={() => openEdit(emp)}>
                                <Plus className="w-4 h-4 mr-2" /> Editar Empleado
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => {
                                  const newPwd = prompt(`Nueva contraseña para ${emp.full_name || emp.email}:`);
                                  if (newPwd && newPwd.length >= 6) {
                                    resetPasswordMutation.mutate({ userId: emp.id, password: newPwd });
                                  } else if (newPwd) {
                                    toast.error("La contraseña debe tener al menos 6 caracteres");
                                  }
                                }}
                              >
                                <KeyRound className="w-4 h-4 mr-2 text-muted-foreground" /> Resetear Contraseña
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-amber-600 dark:text-amber-400 focus:bg-amber-50 dark:focus:bg-amber-950/20"
                                onClick={() => {
                                  if (confirm(`¿Archivar a ${emp.full_name || emp.email}?`)) {
                                    archiveMutation.mutate(emp.id);
                                  }
                                }}
                              >
                                <Archive className="w-4 h-4 mr-2" /> Archivar
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => {
                                  if (confirm(emp.is_active ? `¿Inactivar a ${emp.full_name || emp.email}?` : `¿Reactivar a ${emp.full_name || emp.email}?`)) {
                                    updateMutation.mutate({ id: emp.id, data: { is_active: !emp.is_active } });
                                  }
                                }}
                              >
                                <EyeOff className="w-4 h-4 mr-2" /> {emp.is_active ? "Inactivar" : "Reactivar"}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive focus:bg-destructive/10"
                                onClick={() => {
                                  if (confirm(`¿Eliminar PERMANENTEMENTE a ${emp.full_name || emp.email}? Esta acción no se puede deshacer.`)) {
                                    deleteMutation.mutate(emp.id);
                                  }
                                }}
                              >
                                <Trash2 className="w-4 h-4 mr-2" /> Eliminar
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="mt-5 space-y-2 border-t pt-4 text-xs">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Mail className="w-3.5 h-3.5" />
                      <span className="truncate">{emp.email}</span>
                    </div>
                    {emp.phone_number && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Phone className="w-3.5 h-3.5" />
                        <span>{emp.phone_number}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>
                        Alta: {emp.hire_date ? new Date(emp.hire_date).toLocaleDateString("es-ES") : new Date(emp.created_at).toLocaleDateString("es-ES")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between pt-1">
                      <div className="flex items-center gap-1.5 text-muted-foreground font-semibold">
                        <DollarSign className="w-3.5 h-3.5 text-amber-500" />
                        <span className="text-foreground">
                          {emp.base_salary ? `${emp.base_salary.toLocaleString("es-ES")} €` : "50.000 €"}
                        </span>
                      </div>
                      <Badge variant="outline" className="capitalize text-[10px] tracking-wide font-semibold px-2 py-0.5 border-border/80">
                        {emp.role.replace(/_/g, " ")}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Bottom line detailing contract type if available */}
                <div className="mt-4 flex items-center justify-between text-[10px] text-muted-foreground/80 bg-muted/30 px-3 py-1.5 rounded-lg border">
                  <span className="font-medium truncate max-w-[130px]">Contrato: {emp.contract_type || "Indefinido"}</span>
                  <span className="shrink-0">ID: {emp.id.slice(0, 8)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Table View (Vista de Tabla Tradicional) */}
      {viewMode === "table" && (
        <div className="rounded-xl border bg-card/50 backdrop-blur-sm overflow-hidden shadow-xs">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead>Nombre / Email</TableHead>
                <TableHead>Departamento</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead>Contrato</TableHead>
                <TableHead>Salario Base Anual</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="w-[60px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading && (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center">
                    <div className="flex items-center justify-center gap-2 text-muted-foreground">
                      <Loader2 className="h-5 w-5 animate-spin text-primary" /> Cargando la plantilla de personal...
                    </div>
                  </TableCell>
                </TableRow>
              )}
              {isError && (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-destructive font-medium">
                    Error al cargar empleados. Verifica que el servidor FastAPI esté encendido.
                  </TableCell>
                </TableRow>
              )}
              {!isLoading && filteredEmployees.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    {search ? `Sin resultados para "${search}".` : "No hay empleados registrados."}
                  </TableCell>
                </TableRow>
              )}
              {filteredEmployees.map((emp) => (
                <TableRow
                  key={emp.id}
                  className="group cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => router.push(`/dashboard/employees/${emp.id}`)}
                >
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 text-xs font-semibold text-primary">
                        {getInitials(emp.full_name || emp.email)}
                      </div>
                      <div>
                        <div className="font-semibold text-sm group-hover:text-primary transition-colors">
                          {emp.full_name || "Sin Nombre"}
                        </div>
                        <div className="text-xs text-muted-foreground">{emp.email}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm">
                    {emp.department || "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="capitalize text-[10px] font-semibold px-2 py-0.5">
                      {emp.role.replace(/_/g, " ")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs font-medium text-muted-foreground">
                    {emp.contract_type || "Indefinido"}
                  </TableCell>
                  <TableCell className="text-sm font-semibold">
                    {emp.base_salary ? `${emp.base_salary.toLocaleString("es-ES")} €` : "50.000 €"}
                  </TableCell>
                  <TableCell>
                    {emp.is_active ? (
                      <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 text-[10px] font-bold">
                        ● Activo
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="text-[10px]">○ Archivado</Badge>
                    )}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        id={`actions-${emp.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity inline-flex items-center justify-center rounded-md text-sm hover:bg-accent hover:text-accent-foreground"
                      >
                        <span className="sr-only">Abrir menú</span>
                        <MoreHorizontal className="h-4 w-4" />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuGroup>
                          <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/dashboard/employees/${emp.id}`);
                            }}
                          >
                            <ExternalLink className="w-4 h-4 mr-2" /> Ver detalles
                          </DropdownMenuItem>
                          {isAdmin && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openEdit(emp);
                                }}
                              >
                                <Plus className="w-4 h-4 mr-2" /> Editar empleado
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const newPwd = prompt(`Nueva contraseña para ${emp.full_name || emp.email}:`);
                                  if (newPwd && newPwd.length >= 6) {
                                    resetPasswordMutation.mutate({ userId: emp.id, password: newPwd });
                                  } else if (newPwd) {
                                    toast.error("La contraseña debe tener al menos 6 caracteres");
                                  }
                                }}
                              >
                                <KeyRound className="w-4 h-4 mr-2" /> Resetear Contraseña
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-amber-600 focus:bg-amber-50 dark:focus:bg-amber-950/30"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (confirm(`¿Archivar a ${emp.full_name || emp.email}?`)) {
                                    archiveMutation.mutate(emp.id);
                                  }
                                }}
                              >
                                <Archive className="w-4 h-4 mr-2" /> Archivar
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const msg = emp.is_active
                                    ? `¿Inactivar a ${emp.full_name || emp.email}?`
                                    : `¿Reactivar a ${emp.full_name || emp.email}?`;
                                  if (confirm(msg)) {
                                    updateMutation.mutate({ id: emp.id, data: { is_active: !emp.is_active } });
                                  }
                                }}
                              >
                                <EyeOff className="w-4 h-4 mr-2" /> {emp.is_active ? "Inactivar" : "Reactivar"}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive focus:bg-destructive/10"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (confirm(`¿Eliminar PERMANENTEMENTE a ${emp.full_name || emp.email}? No se puede deshacer.`)) {
                                    deleteMutation.mutate(emp.id);
                                  }
                                }}
                              >
                                <Trash2 className="w-4 h-4 mr-2" /> Borrar
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuGroup>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Employees count footer */}
      {!isLoading && filteredEmployees.length > 0 && (
        <p className="text-xs text-muted-foreground text-right mt-2">
          Mostrando {filteredEmployees.length} de {employees?.length ?? 0} empleados
        </p>
      )}

      <InlineCopilot
        moduleContext="HR"
        placeholder="Ask about employees, onboarding, or compliance..."
        quickActions={[
          { label: "Show department breakdown", message: "Show department breakdown" },
          { label: "Find top performers", message: "Find top performers" },
          { label: "Check onboarding status", message: "Check onboarding status" },
        ]}
      />

      {/* Create / Edit Sheet (Formulario de Cumplimiento Completo) */}
      <Sheet open={sheetOpen} onOpenChange={(open) => { setSheetOpen(open); if (!open) setEditingEmployee(null); }}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto max-h-screen">
          <SheetHeader className="pb-4 border-b">
            <SheetTitle className="text-xl font-bold flex items-center gap-2">
              {editingEmployee ? "Editar Ficha de Empleado" : "Registrar Nuevo Empleado"}
            </SheetTitle>
            <SheetDescription>
              {editingEmployee
                ? `Actualiza los datos y cumplimiento laboral de ${editingEmployee.full_name || editingEmployee.email}.`
                : "Añade un nuevo empleado con cobertura de nóminas, IBAN y SSN según la normativa española."}
            </SheetDescription>
          </SheetHeader>

          <form id="employee-form" onSubmit={handleSubmit} className="space-y-6 py-6 pb-20">
            {/* Sección 1: Datos de Acceso e Identidad */}
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">
                1. Identidad y Acceso al Sistema
              </h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-email">Email Corporativo *</Label>
                  <Input
                    id="emp-email"
                    type="email"
                    required
                    placeholder="empleado@empresa.com"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    disabled={!!editingEmployee}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="emp-name">Nombre Completo *</Label>
                  <Input
                    id="emp-name"
                    required
                    placeholder="María García Pérez"
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-dept">Departamento</Label>
                  <Input
                    id="emp-dept"
                    placeholder="Recursos Humanos"
                    value={form.department}
                    onChange={(e) => setForm({ ...form, department: e.target.value })}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="emp-role">Rol y Permisos</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v || "" })}>
                    <SelectTrigger id="emp-role">
                      <SelectValue />
                    </SelectTrigger>
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
                <SearchableSupervisorSelect
                  value={form.manager_id}
                  onChange={(val) => setForm({ ...form, manager_id: val })}
                  employees={employees || []}
                  excludeId={editingEmployee?.id}
                />
              </div>

              {!editingEmployee && (
                <div className="space-y-2">
                  <Label htmlFor="emp-password">Contraseña Inicial</Label>
                  <Input
                    id="emp-password"
                    type="password"
                    placeholder="Mínimo 6 caracteres"
                    value={form.password || ""}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    autoComplete="new-password"
                  />
                  <p className="text-[10px] text-muted-foreground">Podrá actualizarla al iniciar sesión en el portal.</p>
                </div>
              )}
            </div>

            {/* Sección 2: Información Personal de Contacto */}
            <div className="space-y-4 pt-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">
                2. Datos de Contacto y Emergencia
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-phone">Teléfono de Contacto</Label>
                  <Input
                    id="emp-phone"
                    placeholder="+34 600 000 000"
                    value={form.phone_number}
                    onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="emp-emergency">Contacto de Emergencia</Label>
                  <Input
                    id="emp-emergency"
                    placeholder="Juan García (Padre) - 611 222 333"
                    value={form.emergency_contact}
                    onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="emp-address">Dirección de Residencia</Label>
                <Input
                  id="emp-address"
                  placeholder="Calle Gran Vía 45, 3º B, 28013 Madrid"
                  value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                />
              </div>
            </div>

            {/* Sección 3: Datos Laborales y Cumplimiento de Nóminas (España) */}
            <div className="space-y-4 pt-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-primary border-l-2 border-primary pl-2">
                3. Cumplimiento Laboral y Bancario (España)
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-contract">Tipo de Contrato</Label>
                  <Select value={form.contract_type} onValueChange={(v) => setForm({ ...form, contract_type: v || "Indefinido" })}>
                    <SelectTrigger id="emp-contract">
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

                <div className="space-y-2">
                  <Label htmlFor="emp-hire">Fecha de Contratación</Label>
                  <Input
                    id="emp-hire"
                    type="date"
                    value={form.hire_date}
                    onChange={(e) => setForm({ ...form, hire_date: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-salary">Salario Base Anual (€)</Label>
                  <Input
                    id="emp-salary"
                    type="number"
                    min="0"
                    placeholder="45000"
                    value={form.base_salary}
                    onChange={(e) => setForm({ ...form, base_salary: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="emp-ssn">Nº de Seguridad Social (NUSS)</Label>
                  <Input
                    id="emp-ssn"
                    placeholder="281234567890"
                    value={form.social_security_number}
                    onChange={(e) => setForm({ ...form, social_security_number: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="emp-iban">IBAN Español de Pago</Label>
                  {form.iban && (
                    isIbanValid ? (
                      <span className="text-[10px] text-emerald-500 flex items-center gap-1 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" /> IBAN Español Válido
                      </span>
                    ) : (
                      <span className="text-[10px] text-destructive flex items-center gap-1 font-semibold">
                        <AlertCircle className="w-3.5 h-3.5" /> Formato Incorrecto (ES + 22 dígitos)
                      </span>
                    )
                  )}
                </div>
                <Input
                  id="emp-iban"
                  placeholder="ES91 2100 0418 4502 0005 6789"
                  value={form.iban}
                  onChange={(e) => setForm({ ...form, iban: e.target.value })}
                  className={form.iban && !isIbanValid ? "border-destructive/80 focus-visible:ring-destructive" : ""}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emp-country">País Fiscal</Label>
                  <Input
                    id="emp-country"
                    placeholder="ES"
                    value={form.country}
                    onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase().slice(0, 2) })}
                  />
                </div>
              </div>
            </div>
          </form>

          <SheetFooter className="absolute bottom-0 left-0 right-0 p-6 bg-card border-t z-10">
            <Button
              id="submit-employee"
              type="submit"
              form="employee-form"
              disabled={isMutating || (!!form.iban && !isIbanValid)}
              className="w-full shadow-lg"
            >
              {isMutating && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {editingEmployee ? "Guardar Cambios en la Ficha" : "Registrar Empleado en Plantilla"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
