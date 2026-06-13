"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  User, Briefcase, Calendar, Clock, DollarSign, Users, CheckSquare,
  FileText, Building2, ChevronRight, AlertCircle, Loader2, Sparkles
} from "lucide-react";
import { Link } from "@/i18n/routing";

interface HubData {
  user_id: string;
  full_name: string;
  email: string;
  department: string | null;
  role: string;
  hire_date: string | null;
  contract_type: string | null;
  base_salary: number | null;
  vacation_allowance: number;
  vacation_used: number;
  vacation_remaining: number;
  manager_name: string | null;
  team_size: number;
  active_checklists: number;
  completed_checklists: number;
  recent_payslips: number;
}

export function EmployeeHub() {
  const { data: hub, isLoading, error } = useQuery<HubData>({
    queryKey: ["employee-hub"],
    queryFn: () => fetchClient("/checklists/employee-hub"),
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 animate-pulse">
        {[...Array(6)].map((_, i) => (
          <Card key={i} className="glass">
            <CardHeader className="pb-2">
              <div className="h-4 bg-muted/60 rounded w-24" />
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted/60 rounded w-16 mb-2" />
              <div className="h-3 bg-muted/40 rounded w-28" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error || !hub) {
    return (
      <Card className="glass border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive">Unable to load your dashboard. Please try again.</p>
        </CardContent>
      </Card>
    );
  }

  const vacationPercent = hub.vacation_allowance > 0
    ? Math.round((hub.vacation_used / hub.vacation_allowance) * 100)
    : 0;

  const formatCurrency = (val: number | null) => {
    if (val === null || val === undefined) return "—";
    return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("es-ES", { year: "numeric", month: "long", day: "numeric" });
  };

  const roleLabel = (role: string) => {
    const map: Record<string, string> = {
      hr_admin: "Administrador HR",
      manager: "Manager",
      employee: "Empleado",
      recruiter: "Reclutador",
      finance_manager: "Finanzas",
      it_manager: "IT Manager",
      legal_manager: "Legal",
    };
    return map[role] || role;
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <Card className="glass overflow-hidden relative">
        <div className="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl -mr-12 -mt-12" />
        <CardContent className="p-6 relative z-10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                  Tu Centro de Empleado
                </span>
              </div>
              <h2 className="text-2xl font-bold tracking-tight">Hola, {hub.full_name}</h2>
              <p className="text-sm text-muted-foreground">
                {hub.department && <span>{hub.department} · </span>}
                {roleLabel(hub.role)}
                {hub.manager_name && <span> · Reporta a {hub.manager_name}</span>}
              </p>
            </div>
            <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-3 py-1.5 text-xs font-semibold">
              {hub.contract_type || "Indefinido"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Salario Base</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(hub.base_salary)}</div>
            <p className="text-xs text-muted-foreground mt-1">Bruto anual</p>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Vacaciones</CardTitle>
            <Calendar className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{hub.vacation_remaining} <span className="text-sm font-normal text-muted-foreground">días</span></div>
            <div className="mt-2">
              <Progress value={vacationPercent} className="h-1.5" />
              <p className="text-[10px] text-muted-foreground mt-1">{hub.vacation_used} de {hub.vacation_allowance} usados</p>
            </div>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Equipo</CardTitle>
            <Users className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{hub.team_size}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {hub.team_size > 0 ? "Miembros del equipo" : "Sin equipo directo"}
            </p>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tareas Pendientes</CardTitle>
            <CheckSquare className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{hub.active_checklists}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {hub.completed_checklists} completados
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions & Details */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Quick Actions */}
        <Card className="glass md:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Acciones Rápidas
            </CardTitle>
            <CardDescription>Atajos a las funciones más usadas</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              { href: "/dashboard/time-tracking", icon: Clock, label: "Fichar entrada/salida", color: "text-emerald-500" },
              { href: "/dashboard/calendar", icon: Calendar, label: "Solicitar vacaciones", color: "text-blue-500" },
              { href: "/dashboard/pay", icon: FileText, label: "Ver mis nóminas", color: "text-violet-500" },
              { href: "/dashboard/grow", icon: Briefcase, label: "Mis objetivos (OKRs)", color: "text-amber-500" },
              { href: "/dashboard/training", icon: Building2, label: "Catálogo de formación", color: "text-indigo-500" },
              { href: "/dashboard/employees/org-chart", icon: Users, label: "Organigrama", color: "text-rose-500" },
            ].map((action) => (
              <Link key={action.label} href={action.href}>
                <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer group">
                  <action.icon className={`h-4 w-4 ${action.color}`} />
                  <span className="text-sm flex-1">{action.label}</span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>

        {/* Profile Details */}
        <Card className="glass md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              Datos Personales
            </CardTitle>
            <CardDescription>Información de tu perfil laboral</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Email</p>
                <p className="text-sm font-medium">{hub.email}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Departamento</p>
                <p className="text-sm font-medium">{hub.department || "—"}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Rol</p>
                <Badge variant="outline" className="capitalize">{roleLabel(hub.role)}</Badge>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tipo de Contrato</p>
                <p className="text-sm font-medium">{hub.contract_type || "—"}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Fecha de Alta</p>
                <p className="text-sm font-medium">{formatDate(hub.hire_date)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Responsable</p>
                <p className="text-sm font-medium">{hub.manager_name || "—"}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
