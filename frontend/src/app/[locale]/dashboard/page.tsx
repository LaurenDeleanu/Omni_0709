"use client";

import { useEffect, useState } from "react";
import { AdminAPI, AdminDashboardSummary } from "@/lib/api/admin";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Building2, UserCheck, Bot, Wallet, GraduationCap, Heart, Activity, LineChart, Cpu, Zap, CreditCard, Sparkles } from "lucide-react";
import { useUser } from "@/hooks/use-user";
import { ManagerCommandCenter } from "@/components/manager/ManagerCommandCenter";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
  LineChart as RechartsLineChart,
  Line,
  AreaChart,
  Area,
} from "recharts";

const CHART_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
];

export default function DashboardPage() {
  const { user } = useUser();
  const isManager = user?.role === "manager" || user?.role === "hr_admin" || user?.role === "super_admin" || user?.role === "it_manager" || user?.role === "finance_manager";
  const [data, setData] = useState<AdminDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    AdminAPI.getDashboardSummary()
      .then(setData)
      .catch(() => setError("No se pudieron cargar las métricas del dashboard avanzado."))
      .finally(() => setLoading(false));
  }, []);

  // Quick helper to format currency
  const formatCurrency = (val: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      <div className="flex flex-col gap-1 items-start">
        <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
          Vista Empresarial Avanzada
        </h2>
        <p className="text-muted-foreground text-sm">
          Métricas consolidadas en tiempo real de RRHH, Finanzas, IA y Capacitación.
        </p>
      </div>

      {isManager && <ManagerCommandCenter />}

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array(8).fill(0).map((_, i) => (
            <Card key={i} className="glass animate-pulse">
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
      ) : data ? (
        <div className="space-y-8">
          
          {/* ── PEOPLE & ORGANIZATION ── */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 border-b pb-2">
              <Users className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold tracking-tight">Personas y Organización</h3>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Empleados</CardTitle>
                  <Users className="h-4 w-4 text-primary" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.people.total_employees.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {data.people.active_employees} activos
                  </p>
                </CardContent>
              </Card>
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Nuevas Altas (7d)</CardTitle>
                  <Sparkles className="h-4 w-4 text-emerald-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.people.new_hires_7d.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">Incorporaciones recientes</p>
                </CardContent>
              </Card>
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Candidatos Activos</CardTitle>
                  <UserCheck className="h-4 w-4 text-amber-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.hiring.active_candidates.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">Procesos de selección abiertos</p>
                </CardContent>
              </Card>
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Kudos (7d)</CardTitle>
                  <Heart className="h-4 w-4 text-rose-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.engagement.kudos_7d.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">Reconocimientos de equipo</p>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
              <Card className="col-span-4 glass">
                <CardHeader>
                  <CardTitle>Headcount por Departamento</CardTitle>
                  <CardDescription>Distribución de empleados activos por área de la empresa.</CardDescription>
                </CardHeader>
                <CardContent className="h-[280px]">
                  {data.people.headcount_by_department.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.people.headcount_by_department} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                        <XAxis dataKey="department" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} allowDecimals={false} />
                        <RechartsTooltip contentStyle={{ background: "hsl(var(--card))", borderRadius: "8px", border: "1px solid hsl(var(--border))" }} />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                          {data.people.headcount_by_department.map((_, i) => (
                            <Cell key={`cell-${i}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">No hay datos de departamentos.</div>
                  )}
                </CardContent>
              </Card>
              
              <Card className="col-span-3 glass">
                <CardHeader>
                  <CardTitle>Funnel de Contratación</CardTitle>
                  <CardDescription>Distribución de candidatos por fase.</CardDescription>
                </CardHeader>
                <CardContent className="h-[280px]">
                  {Object.keys(data.hiring.funnel_by_stage).length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart layout="vertical" data={Object.entries(data.hiring.funnel_by_stage).map(([k, v]) => ({ stage: k, count: v }))} margin={{ top: 10, right: 30, left: 40, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                        <XAxis type="number" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} />
                        <YAxis type="category" dataKey="stage" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} width={80} />
                        <RechartsTooltip contentStyle={{ background: "hsl(var(--card))", borderRadius: "8px", border: "1px solid hsl(var(--border))" }} />
                        <Bar dataKey="count" fill="var(--color-chart-2)" radius={[0, 4, 4, 0]} barSize={20} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">No hay candidatos en el pipeline.</div>
                  )}
                </CardContent>
              </Card>
            </div>
          </section>

          {/* ── FINANCE & PAYROLL ── */}
          <section className="space-y-4 pt-4">
            <div className="flex items-center gap-2 border-b pb-2">
              <Wallet className="w-5 h-5 text-emerald-500" />
              <h3 className="text-lg font-semibold tracking-tight">Finanzas y Nóminas</h3>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Gastos Pendientes</CardTitle>
                  <CreditCard className="h-4 w-4 text-rose-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.finance.pending_expenses}</div>
                  <p className="text-xs text-muted-foreground mt-1">Solicitudes por revisar</p>
                </CardContent>
              </Card>
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Importe Pendiente</CardTitle>
                  <Activity className="h-4 w-4 text-emerald-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{formatCurrency(data.finance.pending_expense_amount)}</div>
                  <p className="text-xs text-muted-foreground mt-1">Impacto financiero a aprobar</p>
                </CardContent>
              </Card>
              <Card className="col-span-2 glass">
                <CardHeader className="pb-2">
                  <CardTitle>Histórico de Nóminas (Gross vs Net)</CardTitle>
                </CardHeader>
                <CardContent className="h-[120px] pt-4">
                  {data.finance.payroll_summary.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={[...data.finance.payroll_summary].reverse()} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorGross" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--color-chart-1)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="var(--color-chart-1)" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="colorNet" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--color-chart-2)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="var(--color-chart-2)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="month" hide />
                        <YAxis hide />
                        <RechartsTooltip contentStyle={{ background: "hsl(var(--card))", borderRadius: "8px", border: "1px solid hsl(var(--border))" }} />
                        <Area type="monotone" dataKey="total_gross" stroke="var(--color-chart-1)" fillOpacity={1} fill="url(#colorGross)" />
                        <Area type="monotone" dataKey="total_net" stroke="var(--color-chart-2)" fillOpacity={1} fill="url(#colorNet)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-muted-foreground">Sin histórico de nóminas.</div>
                  )}
                </CardContent>
              </Card>
            </div>
          </section>

          {/* ── AI AGENTS & TRAINING ── */}
          <section className="space-y-4 pt-4">
            <div className="flex items-center gap-2 border-b pb-2">
              <Bot className="w-5 h-5 text-indigo-500" />
              <h3 className="text-lg font-semibold tracking-tight">Agentes IA & Capacitación</h3>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Runs de IA (Mes)</CardTitle>
                  <Cpu className="h-4 w-4 text-indigo-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.ai_agents.runs_this_month.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Histórico total: {data.ai_agents.total_runs.toLocaleString()}
                  </p>
                </CardContent>
              </Card>
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Éxito IA</CardTitle>
                  <Zap className="h-4 w-4 text-amber-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.ai_agents.success_rate}%</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Coste estimado: ${data.ai_agents.cost_this_month}
                  </p>
                </CardContent>
              </Card>
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Cursos Activos</CardTitle>
                  <GraduationCap className="h-4 w-4 text-blue-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{data.training.active_enrollments.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">Empleados en formación</p>
                </CardContent>
              </Card>
              <Card className="glass shadow-sm hover:shadow-md transition-all">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Tasa Media Completitud</CardTitle>
                  <LineChart className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {data.training.completion_rates.length > 0 
                      ? Math.round(data.training.completion_rates.reduce((acc, c) => acc + c.completion_rate, 0) / data.training.completion_rates.length)
                      : 0}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">En todos los cursos</p>
                </CardContent>
              </Card>
            </div>
          </section>

        </div>
      ) : null}
    </div>
  );
}
