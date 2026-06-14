"use client";

import { useEffect, useState } from "react";
import { ReportAPI, DashboardSummary } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Building2, UserCheck, UserX, Clock } from "lucide-react";
import { useUser } from "@/hooks/use-user";
import { ManagerCommandCenter } from "@/components/manager/ManagerCommandCenter";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const CHART_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
  "var(--color-chart-6)",
  "var(--color-chart-7)",
  "var(--color-chart-8)",
];

function formatRelativeTime(isoDate: string | null): string {
  if (!isoDate) return "—";
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `hace ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

export default function DashboardPage() {
  const { user } = useUser();
  const isManager = user?.role === "manager" || user?.role === "hr_admin" || user?.role === "super_admin" || user?.role === "it_manager" || user?.role === "finance_manager";
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    ReportAPI.getDashboard()
      .then(setData)
      .catch(() => setError("No se pudieron cargar las métricas del dashboard."))
      .finally(() => setLoading(false));
  }, []);

  const kpis = data
    ? [
      {
        title: "Total Empleados",
        value: data.total_employees.toLocaleString(),
        icon: Users,
        desc: `${data.active_employees} activos`,
        trend: "up" as const,
      },
      {
        title: "Activos",
        value: data.active_employees.toLocaleString(),
        icon: UserCheck,
        desc: `${data.total_employees > 0 ? Math.round((data.active_employees / data.total_employees) * 100) : 0}% del total`,
        trend: "up" as const,
      },
      {
        title: "Archivados",
        value: data.inactive_employees.toLocaleString(),
        icon: UserX,
        desc: "Fuera de servicio",
        trend: data.inactive_employees > 0 ? ("down" as const) : ("neutral" as const),
      },
      {
        title: "Departamentos",
        value: data.unique_departments.toLocaleString(),
        icon: Building2,
        desc: "Unidades activas",
        trend: "neutral" as const,
      },
    ]
    : Array(4).fill(null);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex flex-col gap-1 items-start">
        <h2 className="text-2xl font-bold tracking-tight">Vista Empresarial</h2>
        <p className="text-muted-foreground text-sm">
          Métricas en tiempo real de tu organización.
        </p>
      </div>

      {isManager && <ManagerCommandCenter />}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {loading
          ? Array(4)
            .fill(0)
            .map((_, i) => (
              <Card key={i} className="glass animate-pulse">
                <CardHeader className="pb-2">
                  <div className="h-4 bg-muted/60 rounded w-24" />
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-muted/60 rounded w-16 mb-2" />
                  <div className="h-3 bg-muted/40 rounded w-28" />
                </CardContent>
              </Card>
            ))
          : kpis.map((metric) =>
            metric ? (
              <Card key={metric.title} className="glass shadow-sm hover:shadow-md transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {metric.title}
                  </CardTitle>
                  <metric.icon
                    className={`h-4 w-4 ${metric.trend === "up"
                        ? "text-primary"
                        : metric.trend === "down"
                          ? "text-destructive"
                          : "text-muted-foreground"
                      }`}
                  />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metric.value}</div>
                  <p className="text-xs text-muted-foreground mt-1">{metric.desc}</p>
                </CardContent>
              </Card>
            ) : null
          )}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7 pt-2">
        {/* Bar Chart — headcount por departamento */}
        <Card className="col-span-4 glass">
          <CardHeader>
            <CardTitle>Headcount por Departamento</CardTitle>
            <CardDescription>Distribución de empleados activos por área.</CardDescription>
          </CardHeader>
          <CardContent className="h-[280px]">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <div className="animate-spin h-6 w-6 rounded-full border-2 border-primary border-t-transparent" />
              </div>
            ) : data && data.departments.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                <BarChart
                  data={data.departments}
                  margin={{ top: 4, right: 16, left: -16, bottom: 40 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    angle={-30}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(v: any) => [v, "Empleados"]}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {data.departments.map((_: any, i: number) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                Sin datos de departamentos. Importa empleados para ver el gráfico.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Employees */}
        <Card className="col-span-3 glass">
          <CardHeader>
            <CardTitle>Altas Recientes</CardTitle>
            <CardDescription>Últimos empleados incorporados al sistema.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-4 pt-4 border-t border-border/50">
                {Array(4)
                  .fill(0)
                  .map((_, i) => (
                    <div key={i} className="flex items-center gap-3 animate-pulse">
                      <div className="w-8 h-8 rounded-full bg-muted/60 shrink-0" />
                      <div className="flex-1 space-y-1">
                        <div className="h-3 bg-muted/60 rounded w-32" />
                        <div className="h-2 bg-muted/40 rounded w-20" />
                      </div>
                      <div className="h-2 bg-muted/40 rounded w-10" />
                    </div>
                  ))}
              </div>
            ) : data && data.recent_employees.length > 0 ? (
              <div className="space-y-3 pt-4 border-t border-border/50">
                {data.recent_employees.map((emp: any) => (
                  <div key={emp.id} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <span className="text-xs font-semibold text-primary">
                        {emp.full_name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium leading-none truncate">{emp.full_name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {emp.department} · {emp.role}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                      <Clock className="w-3 h-3" />
                      {formatRelativeTime(emp.created_at)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="pt-4 border-t border-border/50 text-sm text-muted-foreground text-center py-8">
                Aún no hay empleados registrados.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
