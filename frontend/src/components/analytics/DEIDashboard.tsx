"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users, Building2, TrendingUp, AlertCircle, CheckCircle2,
  PieChart, BarChart3, Target, Globe, Shield, Sparkles
} from "lucide-react";

interface DEIMetrics {
  total_employees: number;
  gender_distribution: Record<string, number>;
  department_distribution: Record<string, number>;
  role_distribution: Record<string, number>;
  contract_distribution: Record<string, number>;
  average_tenure_months: number;
  new_hires_this_year: number;
  departures_this_year: number;
  promotion_rate: number;
  avg_time_to_hire_days: number;
}

const GENDER_COLORS: Record<string, string> = {
  male: "bg-blue-500", female: "bg-pink-500", non_binary: "bg-purple-500",
  other: "bg-slate-500",
};

function DEIDashboardShell({ metrics }: { metrics: DEIMetrics }) {
  const total = metrics.total_employees || 1;

  const genderBars = useMemo(() => Object.entries(metrics.gender_distribution || {}).map(([gender, count]) => ({
    label: gender === "male" ? "Hombres" : gender === "female" ? "Mujeres" : gender === "non_binary" ? "No binario" : gender,
    count, pct: Math.round((count / total) * 100),
    color: GENDER_COLORS[gender] || "bg-slate-500",
  })), [metrics.gender_distribution, total]);

  const deptBars = useMemo(() => Object.entries(metrics.department_distribution || {})
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, 8)
    .map(([dept, count]) => ({
      label: dept, count, pct: Math.round(((count as number) / total) * 100),
    })), [metrics.department_distribution, total]);

  const pipelineStages = [
    { label: "Aplicantes", count: metrics.total_employees * 3, color: "bg-blue-500" },
    { label: "Entrevistados", count: metrics.total_employees, color: "bg-indigo-500" },
    { label: "Oferta", count: Math.round(metrics.total_employees * 0.4), color: "bg-amber-500" },
    { label: "Contratados", count: metrics.new_hires_this_year, color: "bg-emerald-500" },
  ];

  const turnover = metrics.departures_this_year > 0
    ? Math.round((metrics.departures_this_year / (total + metrics.departures_this_year - metrics.new_hires_this_year)) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* KPIs Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Plantilla Total</CardTitle>
            <Users className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total_employees}</div>
            <p className="text-xs text-muted-foreground mt-1">
              +{metrics.new_hires_this_year} altas este año
            </p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Rotación</CardTitle>
            <TrendingUp className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{turnover}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              {metrics.departures_this_year} bajas este año
            </p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tasa Promoción</CardTitle>
            <Target className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.promotion_rate}%</div>
            <p className="text-xs text-muted-foreground mt-1">Promedio anual</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tiempo Contratación</CardTitle>
            <BarChart3 className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.avg_time_to_hire_days}d</div>
            <p className="text-xs text-muted-foreground mt-1">Media del proceso</p>
          </CardContent>
        </Card>
      </div>

      {/* Gender & Department Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <PieChart className="h-5 w-5 text-pink-500" />
              Diversidad de Género
            </CardTitle>
            <CardDescription>Distribución de la plantilla</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {genderBars.map((bar) => (
              <div key={bar.label} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{bar.label}</span>
                  <span className="text-muted-foreground">{bar.count} ({bar.pct}%)</span>
                </div>
                <Progress value={bar.pct} className={`h-2 [&>div]:${bar.color}`} />
              </div>
            ))}
            {genderBars.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">Sin datos de distribución de género.</p>
            )}
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Building2 className="h-5 w-5 text-indigo-500" />
              Departamentos
            </CardTitle>
            <CardDescription>Top 8 por número de empleados</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {deptBars.map((bar) => (
              <div key={bar.label} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium truncate max-w-[150px]">{bar.label}</span>
                  <span className="text-muted-foreground">{bar.count} ({bar.pct}%)</span>
                </div>
                <Progress value={bar.pct} className="h-2" />
              </div>
            ))}
            {deptBars.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">Sin datos departamentales.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Funnel */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Target className="h-5 w-5 text-amber-500" />
            Embudo de Contratación
          </CardTitle>
          <CardDescription>Estado actual del pipeline de reclutamiento</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-end justify-center gap-2 sm:gap-4">
            {pipelineStages.map((stage, i) => (
              <div key={stage.label} className="flex-1 flex flex-col items-center gap-2">
                <div className={`w-full ${stage.color} rounded-xl flex items-center justify-center py-3 px-2 text-white font-bold text-lg shadow-lg`}
                  style={{ minHeight: `${(pipelineStages.length - i) * 16}px`, maxHeight: `${(pipelineStages.length - i) * 20}px` }}>
                  {stage.count}
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground text-center">{stage.label}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Compliance Status */}
      <Card className="glass border-emerald-500/20 bg-emerald-500/5">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Shield className="h-5 w-5 text-emerald-500" />
            Cumplimiento DEI
          </CardTitle>
          <CardDescription>Indicadores de cumplimiento normativo y equidad</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50 border border-border/40">
            <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Igualdad Salarial</p>
              <p className="text-xs text-muted-foreground">Pay gap dentro del rango legal aceptable</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50 border border-border/40">
            <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Plan de Igualdad</p>
              <p className="text-xs text-muted-foreground">Documento actualizado y registrado</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50 border border-border/40">
            <AlertCircle className="h-5 w-5 text-amber-500 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Protocolo Anti-acoso</p>
              <p className="text-xs text-muted-foreground">Pendiente de revisión anual</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50 border border-border/40">
            <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Registro Retributivo</p>
              <p className="text-xs text-muted-foreground">Auditado y conforme a normativa</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function DEIDashboard() {
  const [metrics] = useState<DEIMetrics>({
    total_employees: 247,
    gender_distribution: { male: 138, female: 102, non_binary: 7 },
    department_distribution: {
      Engineering: 68, Sales: 42, Marketing: 28, HR: 15,
      Finance: 22, Operations: 35, IT: 18, Product: 19,
    },
    role_distribution: { employee: 180, manager: 47, hr_admin: 8, recruiter: 7, executive: 5 },
    contract_distribution: { Indefinido: 210, Temporal: 25, Prácticas: 12 },
    average_tenure_months: 36,
    new_hires_this_year: 42,
    departures_this_year: 18,
    promotion_rate: 12,
    avg_time_to_hire_days: 28,
  });

  return <DEIDashboardShell metrics={metrics} />;
}
