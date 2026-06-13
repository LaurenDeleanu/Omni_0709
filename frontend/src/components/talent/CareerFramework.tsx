"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import {
  Briefcase, Star, Target, TrendingUp, ChevronRight, DollarSign,
  Sparkles, ArrowUp, Award
} from "lucide-react";
import { Link } from "@/i18n/routing";

const LEVELS = [
  {
    level: "L1", title: "Junior", years_experience: "0-2",
    salary_range: "24K — 32K EUR",
    competencies: ["Fundamentos técnicos", "Trabajo en equipo", "Aprendizaje continuo", "Comunicación básica"],
    description: "Profesional en etapa inicial. Requiere supervisión cercana y mentoring activo. Enfoque en desarrollo de habilidades fundamentales.",
  },
  {
    level: "L2", title: "Mid", years_experience: "2-5",
    salary_range: "32K — 48K EUR",
    competencies: ["Autonomía técnica", "Resolución de problemas", "Mentoring a juniors", "Comunicación efectiva"],
    description: "Profesional consolidado. Trabaja con autonomía moderada. Contribuye significativamente a proyectos del equipo.",
  },
  {
    level: "L3", title: "Senior", years_experience: "5-8",
    salary_range: "48K — 65K EUR",
    competencies: ["Liderazgo técnico", "Diseño de sistemas", "Pensamiento estratégico", "Gestión de stakeholders"],
    description: "Referente técnico del equipo. Lidera iniciativas complejas. Influye en decisiones de arquitectura y diseño.",
  },
  {
    level: "L4", title: "Staff / Lead", years_experience: "8-12",
    salary_range: "65K — 90K EUR",
    competencies: ["Visión multi-equipo", "Arquitectura organizacional", "Coaching de seniors", "Influencia ejecutiva"],
    description: "Impacto a nivel organizacional. Define estándares y prácticas. Lidera iniciativas cross-funcionales.",
  },
  {
    level: "L5", title: "Principal / Director", years_experience: "12+",
    salary_range: "90K — 140K EUR",
    competencies: ["Estrategia técnica global", "Liderazgo organizacional", "Innovación disruptiva", "Relaciones C-level"],
    description: "Define la estrategia técnica de la compañía. Representa a la organización externamente. Toma decisiones de alto impacto.",
  },
];

const TRACKS = [
  {
    name: "Individual Contributor (IC)", icon: Briefcase,
    paths: [
      { from: "Junior (L1)", to: "Mid (L2)", criteria: "18 meses + revisión de competencias", time_to: "18-24 meses" },
      { from: "Mid (L2)", to: "Senior (L3)", criteria: "Liderazgo en 3+ proyectos + mentor a juniors", time_to: "24-36 meses" },
      { from: "Senior (L3)", to: "Staff (L4)", criteria: "Impacto multi-equipo + iniciativas cross-funcionales", time_to: "24-48 meses" },
      { from: "Staff (L4)", to: "Principal (L5)", criteria: "Reconocimiento industria + innovación", time_to: "36+ meses" },
    ]
  },
  {
    name: "Management Track", icon: Target,
    paths: [
      { from: "Senior (L3)", to: "Team Lead (L4-M)", criteria: "Gestión de equipo + OKRs de departamento", time_to: "12-24 meses" },
      { from: "Team Lead (L4-M)", to: "Engineering Manager (L5-M)", criteria: "Gestión de múltiples equipos", time_to: "24-36 meses" },
    ]
  },
];

export function CareerFramework() {
  return (
    <div className="space-y-6">
      {/* Header KPI */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Niveles Definidos</CardTitle>
            <Briefcase className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{LEVELS.length}</div>
            <p className="text-xs text-muted-foreground mt-1">De L1 a L5</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Tracks de Carrera</CardTitle>
            <Target className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{TRACKS.length}</div>
            <p className="text-xs text-muted-foreground mt-1">IC + Management</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Salario Máximo</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">140K€</div>
            <p className="text-xs text-muted-foreground mt-1">Principal (L5)</p>
          </CardContent>
        </Card>
      </div>

      {/* Levels Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {LEVELS.map((level, i) => (
          <Card key={level.level} className="glass shadow-sm hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <Badge className="bg-primary/10 text-primary border-primary/20 text-xs font-bold">{level.level}</Badge>
                <Badge variant="outline" className="text-[10px]">{level.years_experience} años exp.</Badge>
              </div>
              <CardTitle className="text-lg font-bold mt-2">{level.title}</CardTitle>
              <CardDescription className="text-xs flex items-center gap-1">
                <DollarSign className="h-3 w-3 text-emerald-500" />
                {level.salary_range}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground mb-3">{level.description}</p>
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Competencias Clave</p>
                {level.competencies.map((comp, j) => (
                  <div key={j} className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${
                      j === 0 ? "bg-emerald-500" : j === 1 ? "bg-blue-500" : j === 2 ? "bg-amber-500" : "bg-purple-500"
                    }`} />
                    <span className="text-xs">{comp}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Career Tracks */}
      <div className="grid gap-6 md:grid-cols-2">
        {TRACKS.map((track) => (
          <Card key={track.name} className="glass">
            <CardHeader>
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                <track.icon className="h-5 w-5 text-primary" />
                {track.name}
              </CardTitle>
              <CardDescription>Progresión de carrera y criterios de promoción</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {track.paths.map((path, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-muted/20 border border-border/30">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold">{path.from}</span>
                      <ArrowUp className="h-3 w-3 text-emerald-500" />
                      <span className="text-xs font-bold">{path.to}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-1">{path.criteria}</p>
                  </div>
                  <Badge variant="outline" className="text-[10px] shrink-0">{path.time_to}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
