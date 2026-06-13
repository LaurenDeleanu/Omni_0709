"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Target, Users, Star, TrendingUp, AlertTriangle, Shield,
  Sparkles, Loader2, AlertCircle, ChevronRight
} from "lucide-react";
import { Link } from "@/i18n/routing";

interface EmployeePosition {
  user_id: string;
  full_name: string;
  email: string;
  department: string | null;
  role: string;
  manager_name: string | null;
  hire_date: string | null;
  performance_score: number;
  potential_score: number;
  grid_x: number;
  grid_y: number;
  last_review_date: string | null;
  okr_progress: number;
  base_salary: number | null;
}

interface TalentGridData {
  employees: EmployeePosition[];
  stats: Record<string, number>;
  succession_risks: { user_id: string; full_name: string; role: string; risk: string; potential_successors: EmployeePosition[] }[];
}

const GRID_LABELS = {
  x: ["Necesita Mejorar", "Cumple Expectativas", "Supera Expectativas"],
  y: ["Potencial Limitado", "Potencial de Crecimiento", "Alto Potencial"],
};

const GRID_COLORS: Record<string, string> = {
  "1-1": "bg-rose-500/10 border-rose-500/30 text-rose-500",
  "2-1": "bg-amber-500/10 border-amber-500/30 text-amber-500",
  "3-1": "bg-amber-500/10 border-amber-500/30 text-amber-500",
  "1-2": "bg-amber-500/10 border-amber-500/30 text-amber-500",
  "2-2": "bg-blue-500/10 border-blue-500/30 text-blue-500",
  "3-2": "bg-indigo-500/10 border-indigo-500/30 text-indigo-500",
  "1-3": "bg-slate-500/10 border-slate-500/30 text-slate-500",
  "2-3": "bg-indigo-500/10 border-indigo-500/30 text-indigo-500",
  "3-3": "bg-emerald-500/10 border-emerald-500/30 text-emerald-500",
};

const GRID_CELL_LABELS: Record<string, string> = {
  "1-1": "Acción Urgente",
  "2-1": "Análisis Necesario",
  "3-1": "Enigma",
  "1-2": "Bajo Rendimiento",
  "2-2": "Core Player",
  "3-2": "High Performer",
  "1-3": "Potencial no Aprovechado",
  "2-3": "Rising Star",
  "3-3": "Star / High Flyer",
};

export function TalentGrid() {
  const [selectedCell, setSelectedCell] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"grid" | "succession">("grid");

  const { data, isLoading, error } = useQuery<TalentGridData>({
    queryKey: ["talent-grid"],
    queryFn: () => fetchClient("/talent-grid").then(r => r),
  });

  const cellEmployees = useMemo(() => {
    if (!data) return {};
    const grouped: Record<string, EmployeePosition[]> = {};
    for (const emp of data.employees) {
      const key = `${emp.grid_x}-${emp.grid_y}`;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(emp);
    }
    return grouped;
  }, [data]);

  if (isLoading) {
    return (
      <Card className="glass">
        <CardHeader><Skeleton className="h-6 w-48" /></CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 aspect-square">
            {[...Array(9)].map((_, i) => <Skeleton key={i} className="rounded-2xl" />)}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="glass border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive">Unable to load talent grid.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: "Total Evaluados", value: data.stats.total_employees, icon: Users, color: "text-primary" },
          { label: "Stars", value: data.stats.stars, icon: Star, color: "text-emerald-500" },
          { label: "Core Players", value: data.stats.core_players, icon: Shield, color: "text-blue-500" },
          { label: "Necesitan Atención", value: data.stats.needs_attention, icon: AlertTriangle, color: "text-rose-500" },
        ].map(kpi => (
          <Card key={kpi.label} className="glass shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-medium text-muted-foreground">{kpi.label}</CardTitle>
              <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{kpi.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-muted/50 rounded-lg w-fit">
        {[
          { id: "grid", label: "📊 Matriz 9-Box" },
          { id: "succession", label: "🔄 Sucesión" },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-1.5 rounded-md text-xs font-bold transition-colors ${
              activeTab === tab.id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "grid" ? (
        <Card className="glass overflow-hidden">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Matriz de Talento 9-Box
            </CardTitle>
            <CardDescription>Performance (X) vs Potencial (Y)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 aspect-square min-h-[500px]">
              {[3, 2, 1].map(y => [1, 2, 3].map(x => {
                const key = `${x}-${y}`;
                const emps = cellEmployees[key] || [];
                const colors = GRID_COLORS[key] || "bg-slate-500/10 border-slate-500/30 text-slate-500";
                const isSelected = selectedCell === key;

                return (
                  <button
                    key={key}
                    onClick={() => setSelectedCell(isSelected ? null : key)}
                    className={`rounded-2xl border p-3 flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer ${
                      colors
                    } ${isSelected ? "ring-2 ring-primary scale-105 shadow-lg" : "hover:scale-[1.02] hover:shadow-md"}`}
                  >
                    <span className="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                      {GRID_CELL_LABELS[key]}
                    </span>
                    <div className={`text-2xl font-extrabold ${emps.length > 0 ? "" : "opacity-30"}`}>
                      {emps.length}
                    </div>
                    <span className="text-[10px] font-medium">
                      {y === 3 ? "Alto Pot." : y === 2 ? "Medio Pot." : "Bajo Pot."}
                      {" · "}
                      {x === 3 ? "Supera" : x === 2 ? "Cumple" : "Mejora"}
                    </span>
                    {emps.length > 0 && (
                      <div className="flex -space-x-2 mt-1">
                        {emps.slice(0, 4).map(emp => (
                          <div key={emp.user_id} className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 border-2 border-white dark:border-slate-800 flex items-center justify-center text-[8px] font-bold text-white">
                            {emp.full_name.split(" ").map(n => n[0]).slice(0, 2).join("")}
                          </div>
                        ))}
                        {emps.length > 4 && (
                          <div className="w-6 h-6 rounded-full bg-muted border-2 border-white dark:border-slate-800 flex items-center justify-center text-[8px] font-bold text-muted-foreground">
                            +{emps.length - 4}
                          </div>
                        )}
                      </div>
                    )}
                  </button>
                );
              }))}
            </div>

            <div className="flex justify-between mt-4">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                ← Performance →
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground" style={{ writingMode: "vertical-rl" }}>
                Potencial ↑
              </span>
            </div>

            {/* Selected Cell Details */}
            {selectedCell && cellEmployees[selectedCell] && (
              <div className="mt-6 pt-6 border-t border-border/40 space-y-3">
                <h4 className="text-sm font-bold flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  {GRID_CELL_LABELS[selectedCell]} — {cellEmployees[selectedCell].length} empleados
                </h4>
                <div className="grid gap-2 sm:grid-cols-2">
                  {cellEmployees[selectedCell].map(emp => (
                    <Link key={emp.user_id} href={`/dashboard/employees/${emp.user_id}`}>
                      <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-muted/30 transition-colors cursor-pointer group border border-border/30">
                        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
                          {emp.full_name.split(" ").map(n => n[0]).slice(0, 2).join("")}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold truncate">{emp.full_name}</p>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <Badge variant="outline" className="capitalize text-[10px]">{emp.department || emp.role}</Badge>
                            <span className="text-[10px] text-muted-foreground">
                              P: {emp.performance_score} / Pot: {emp.potential_score}
                            </span>
                          </div>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Shield className="h-5 w-5 text-amber-500" />
              Planificación de Sucesión
            </CardTitle>
            <CardDescription>Riesgos de sucesión para roles críticos</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.succession_risks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                  <Shield className="w-6 h-6" />
                </div>
                <p className="text-sm text-muted-foreground">Todos los roles críticos tienen sucesión planificada.</p>
              </div>
            ) : (
              data.succession_risks.map(risk => (
                <div key={risk.user_id} className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="text-sm font-bold">{risk.full_name}</p>
                      <Badge className="mt-1 bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-bold">{risk.role}</Badge>
                    </div>
                    <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] font-bold">
                      <AlertTriangle className="w-3 h-3 mr-1" /> {risk.risk}
                    </Badge>
                  </div>
                  {risk.potential_successors.length > 0 ? (
                    <div className="mt-3 space-y-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Candidatos Potenciales</p>
                      {risk.potential_successors.map(s => (
                        <div key={s.user_id} className="flex items-center gap-2 text-sm p-2 rounded-lg bg-muted/20">
                          <span className="font-medium">{s.full_name}</span>
                          <Badge variant="outline" className="text-[10px] capitalize">{s.department || s.role}</Badge>
                          <span className="text-xs text-muted-foreground ml-auto">Score: {s.potential_score}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground mt-2">No se han identificado candidatos internos.</p>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
