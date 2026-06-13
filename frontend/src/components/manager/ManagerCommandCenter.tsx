"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/routing";
import {
  Users, Trophy, Target, AlertTriangle, Calendar, Clock, TrendingUp,
  CheckCircle2, AlertCircle, Loader2, Sparkles, ChevronRight, Gift, Shield,
  BarChart3, DollarSign, UserCheck, Star
} from "lucide-react";

interface DirectReport {
  id: string;
  full_name: string;
  email: string;
  department: string | null;
  role: string;
  hire_date: string | null;
  base_salary: number | null;
  okr_progress: number;
  last_review_date: string | null;
  last_review_score: number | null;
  vacation_remaining: number;
  is_active: boolean;
}

interface TeamOKR {
  total_okrs: number;
  on_track: number;
  at_risk: number;
  behind: number;
  avg_progress: number;
  employees_with_okrs: number;
}

interface ComplianceItem {
  label: string;
  status: string;
  detail: string;
}

interface TurnoverRisk {
  user_id: string;
  full_name: string;
  risk_level: string;
  indicators: string[];
}

interface ManagerData {
  is_manager: boolean;
  team_headcount: number;
  team_department: string | null;
  avg_salary: number | null;
  span_of_control: number;
  direct_reports: DirectReport[];
  team_okrs: TeamOKR;
  recent_kudos_count: number;
  pending_reviews: number;
  upcoming_anniversaries: { type: string; user_id: string; full_name: string; date: string; days_until: number }[];
  team_compliance: ComplianceItem[];
  open_positions: number;
  turnover_risks: TurnoverRisk[];
}

function formatCurrency(val: number | null) {
  if (!val) return "—";
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(val);
}

function okrStatusBadge(progress: number) {
  if (progress >= 70) return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold"><CheckCircle2 className="w-3 h-3 mr-1" /> On Track</Badge>;
  if (progress >= 40) return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-bold"><AlertTriangle className="w-3 h-3 mr-1" /> At Risk</Badge>;
  return <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] font-bold"><AlertCircle className="w-3 h-3 mr-1" /> Behind</Badge>;
}

export function ManagerCommandCenter() {
  const { data: mgr, isLoading, error } = useQuery<ManagerData>({
    queryKey: ["manager-team-overview"],
    queryFn: async () => {
      const res = await fetchClient("/manager/team-overview");
      const json = await res.json();
      console.log("[Manager] API response:", json);
      return json;
    },
    staleTime: 0,
    retry: 1,
  });

  console.log("[Manager] state:", { isLoading, error: String(error), hasData: !!mgr, isManager: mgr?.is_manager });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="glass">
              <CardHeader className="pb-2"><div className="h-4 bg-muted/60 rounded w-20" /></CardHeader>
              <CardContent><div className="h-8 bg-muted/60 rounded w-16 mb-2" /><div className="h-3 bg-muted/40 rounded w-24" /></CardContent>
            </Card>
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (error || !mgr) {
    return (
      <Card className="glass border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <div>
            <p className="text-sm text-destructive">Unable to load manager dashboard.</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {error ? String(error) : "No response data"}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!mgr.is_manager) return null;

  return (
    <div className="space-y-6">
      {/* Welcome & Context */}
      <Card className="glass overflow-hidden relative">
        <div className="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl -mr-12 -mt-12" />
        <CardContent className="p-6 relative z-10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-primary">Command Center</span>
              </div>
              <h2 className="text-2xl font-bold tracking-tight">
                Tu Equipo
                {mgr.team_department && (
                  <Badge className="ml-2 bg-primary/10 text-primary border-primary/20 text-xs font-bold">{mgr.team_department}</Badge>
                )}
              </h2>
              <p className="text-sm text-muted-foreground">
                {mgr.team_headcount} miembros activos &middot; {mgr.span_of_control} total en reporting &middot; Salario medio: {formatCurrency(mgr.avg_salary)}
              </p>
            </div>
            <div className="flex gap-2">
              <Link href="/dashboard/employees/org-chart">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <Shield className="h-4 w-4" /> Organigrama
                </Button>
              </Link>
              <Link href="/dashboard/employees">
                <Button size="sm" className="gap-1.5">
                  <Users className="h-4 w-4" /> Gestionar Equipo
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Plantilla Activa</CardTitle>
            <Users className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mgr.team_headcount}</div>
            <p className="text-xs text-muted-foreground mt-1">{mgr.span_of_control} total reporting</p>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Progreso OKRs</CardTitle>
            <Target className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mgr.team_okrs.avg_progress}%</div>
            <div className="flex gap-0.5 mt-2">
              <div className="flex-1 h-1.5 rounded-full bg-emerald-500" style={{ width: `${(mgr.team_okrs.on_track / Math.max(mgr.team_okrs.total_okrs, 1)) * 100}%` }} />
              <div className="flex-1 h-1.5 rounded-full bg-amber-500" style={{ width: `${(mgr.team_okrs.at_risk / Math.max(mgr.team_okrs.total_okrs, 1)) * 100}%` }} />
              <div className="flex-1 h-1.5 rounded-full bg-rose-500" style={{ width: `${(mgr.team_okrs.behind / Math.max(mgr.team_okrs.total_okrs, 1)) * 100}%` }} />
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">{mgr.team_okrs.on_track} on track / {mgr.team_okrs.at_risk} risk / {mgr.team_okrs.behind} behind</p>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Pendientes</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mgr.pending_reviews}</div>
            <p className="text-xs text-muted-foreground mt-1">Revisiones sin evaluar</p>
          </CardContent>
        </Card>

        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Reconocimiento</CardTitle>
            <Trophy className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mgr.recent_kudos_count}</div>
            <p className="text-xs text-muted-foreground mt-1">Kudos recibidos</p>
          </CardContent>
        </Card>
      </div>

      {/* Team Grid + Compliance */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Direct Reports */}
        <Card className="glass lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Mis Colaboradores
            </CardTitle>
            <CardDescription>OKR progreso y estado</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {mgr.direct_reports.filter(r => r.is_active).map(report => (
              <Link key={report.id} href={`/dashboard/employees/${report.id}`}>
                <div className="flex items-center gap-4 p-3 rounded-xl hover:bg-muted/30 transition-colors cursor-pointer group border border-border/30">
                  <div className={`h-10 w-10 rounded-xl bg-gradient-to-br ${
                    report.department === "Engineering" ? "from-cyan-500/20 to-blue-500/20 border border-cyan-500/30" :
                    report.department === "HR" ? "from-purple-500/20 to-pink-500/20 border border-purple-500/30" :
                    report.department === "Sales" ? "from-amber-500/20 to-orange-500/20 border border-amber-500/30" :
                    report.department === "Finance" ? "from-emerald-500/20 to-teal-500/20 border border-emerald-500/30" :
                    "from-slate-500/20 to-zinc-500/20 border border-slate-500/30"
                  } flex items-center justify-center text-sm font-bold shrink-0`}>
                    {report.full_name.split(" ").map(n => n[0]).slice(0, 2).join("").toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold truncate">{report.full_name}</p>
                      <Badge variant="outline" className="capitalize text-[10px] shrink-0">{report.role}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{report.email}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="flex items-center gap-1.5">
                      {okrStatusBadge(report.okr_progress)}
                      <span className="text-xs font-bold text-muted-foreground">{Math.round(report.okr_progress)}%</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {report.last_review_date
                        ? `Revisión: ${new Date(report.last_review_date).toLocaleDateString("es-ES")}`
                        : "Sin revisión"}
                    </p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                </div>
              </Link>
            ))}
            {mgr.direct_reports.filter(r => r.is_active).length === 0 && (
              <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                  <Users className="w-6 h-6" />
                </div>
                <p className="text-sm text-muted-foreground">No tienes colaboradores directos asignados.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Side Panel: Compliance + Risk */}
        <div className="space-y-6">
          <Card className="glass">
            <CardHeader>
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                <Shield className="h-5 w-5 text-emerald-500" />
                Cumplimiento
              </CardTitle>
              <CardDescription>Estado de procesos obligatorios</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {mgr.team_compliance.map((item, i) => (
                <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-background/50 border border-border/30">
                  {item.status === "ok" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                  )}
                  <div>
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="text-xs text-muted-foreground">{item.detail}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {mgr.turnover_risks.length > 0 && (
            <Card className="glass border-amber-500/20">
              <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  Riesgo de Rotación
                </CardTitle>
                <CardDescription>{mgr.turnover_risks.length} empleados con indicadores</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {mgr.turnover_risks.map(risk => (
                  <div key={risk.user_id} className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold">{risk.full_name}</span>
                      <Badge className={`text-[10px] font-bold ${risk.risk_level === "high" ? "bg-rose-500/10 text-rose-500 border-rose-500/20" : "bg-amber-500/10 text-amber-500 border-amber-500/20"}`}>
                        {risk.risk_level === "high" ? "Alto" : "Medio"}
                      </Badge>
                    </div>
                    <ul className="text-xs text-muted-foreground space-y-0.5">
                      {risk.indicators.map((ind, i) => <li key={i}>&bull; {ind}</li>)}
                    </ul>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {mgr.upcoming_anniversaries.length > 0 && (
            <Card className="glass">
              <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <Gift className="h-5 w-5 text-pink-500" />
                  Próximos Aniversarios
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {mgr.upcoming_anniversaries.slice(0, 5).map((ann, i) => (
                  <div key={i} className="flex items-center justify-between text-sm py-1.5">
                    <span className="font-medium">{ann.full_name}</span>
                    <Badge variant="outline" className="text-[10px]">{ann.days_until}d</Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
