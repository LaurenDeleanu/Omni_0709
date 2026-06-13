"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Laptop, CreditCard, GraduationCap, CalendarClock, Activity } from "lucide-react";

interface ModulesTabProps {
  enabledModules: Record<string, boolean> | undefined;
  isModuleActive: (key: string) => boolean;
  handleModuleToggle: (key: string, checked: boolean) => void;
  togglePending: boolean;
  usersCount: number;
  coursesCount: number;
  loadingUsers: boolean;
  loadingCourses: boolean;
}

export function ModulesTab({
  enabledModules, isModuleActive, handleModuleToggle, togglePending,
  usersCount, coursesCount, loadingUsers, loadingCourses
}: ModulesTabProps) {

  const MODULE_CARDS = [
    { key: "it", name: "SuccessCore IT", icon: Laptop, color: "cyan",
      desc: "Gestión avanzada de inventario de hardware, asignación de periféricos, y Service Desk de incidencias internas.",
      tags: ["Ticketing", "Hardware", "SSO/SaaS"] },
    { key: "finance", name: "Finanzas & Gastos", icon: CreditCard, color: "emerald",
      desc: "Control horario mediante geolocalización, escaneo inteligente de tiques por OCR de IA y exportador contable Sage/Holded.",
      tags: ["AI OCR", "Fichajes", "Sage Exporte"] },
    { key: "training", name: "LMS & Academia", icon: GraduationCap, color: "indigo",
      desc: "Catálogo formativo interactivo compatible con paquetes SCORM 1.2/2004, exámenes de evaluación y cumplimiento FUNDAE.",
      tags: ["SCORM", "FUNDAE", "SEPE XML"] },
    { key: "schedules", name: "Automatización", icon: CalendarClock, color: "amber",
      desc: "Generación y distribución automatizada en segundo plano de informes ejecutivos e importaciones de personal en lote.",
      tags: ["Cron", "Informes", "E-Mail"] },
  ];

  const colorMap: Record<string, { border: string; bg: string; shadow: string; icon: string; tag: string; toggle: string }> = {
    cyan:    { border: "border-cyan-500/30",    bg: "bg-cyan-950/10",    shadow: "shadow-[0_4px_20px_-4px_rgba(6,182,212,0.15)]",   icon: "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",    tag: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",    toggle: "peer-focus:ring-cyan-500/40 peer-checked:bg-cyan-500" },
    emerald: { border: "border-emerald-500/30", bg: "bg-emerald-950/10", shadow: "shadow-[0_4px_20px_-4px_rgba(16,185,129,0.15)]", icon: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20", tag: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", toggle: "peer-focus:ring-emerald-500/40 peer-checked:bg-emerald-500" },
    indigo:  { border: "border-indigo-500/30",  bg: "bg-indigo-950/10",  shadow: "shadow-[0_4px_20px_-4px_rgba(99,102,241,0.15)]",  icon: "bg-indigo-500/15 text-indigo-400",                   tag: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",  toggle: "peer-focus:ring-indigo-500/40 peer-checked:bg-indigo-500" },
    amber:   { border: "border-amber-500/30",   bg: "bg-amber-950/10",   shadow: "shadow-[0_4px_20px_-4px_rgba(245,158,11,0.15)]", icon: "bg-amber-500/15 text-amber-400",                     tag: "bg-amber-500/10 text-amber-400 border-amber-500/20",    toggle: "peer-focus:ring-amber-500/40 peer-checked:bg-amber-500" },
  };

  const activeCount = MODULE_CARDS.filter(m => isModuleActive(m.key)).length;

  return (
    <div className="space-y-8">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {MODULE_CARDS.map(mod => {
          const active = isModuleActive(mod.key);
          const c = colorMap[mod.color];
          return (
            <Card key={mod.key} className={`relative overflow-hidden transition-all duration-300 border ${active ? `${c.border} ${c.bg} ${c.shadow}` : "border-border/60 bg-card/20"}`}>
              {active && <div className={`absolute top-0 right-0 w-24 h-24 ${c.bg.replace("950/10", "500/10")} rounded-full blur-2xl`} />}
              <CardHeader className="flex flex-row items-start justify-between pb-4">
                <div className="space-y-2">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${active ? c.icon : "bg-muted/40 text-muted-foreground border-border/40"}`}>
                    <mod.icon className="w-5 h-5" />
                  </div>
                  <CardTitle className="mt-2 text-lg font-bold">{mod.name}</CardTitle>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={(e) => handleModuleToggle(mod.key, e.target.checked)}
                    disabled={togglePending}
                    className="sr-only peer"
                  />
                  <div className={`w-11 h-6 bg-muted-foreground/20 rounded-full peer ${c.toggle} peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-muted-foreground/60 after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:bg-foreground`}></div>
                </label>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground space-y-4">
                <p className="leading-relaxed">{mod.desc}</p>
                <div className="flex gap-2 flex-wrap pt-2">
                  {mod.tags.map(tag => (
                    <span key={tag} className={`text-[10px] uppercase font-bold tracking-wider ${c.tag} px-2 py-0.5 rounded border`}>{tag}</span>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="bg-card/25 backdrop-blur-xl border border-border/50 shadow-md">
        <CardHeader>
          <CardTitle className="text-lg font-bold flex gap-2 items-center"><Activity className="w-5 h-5 text-primary" /> Licencias e Indicadores de Uso</CardTitle>
          <CardDescription>Consumo total de recursos, volumen de empleados y métricas activas en tu inquilino.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-3">
            <div className="p-5 border border-border/60 rounded bg-card/45 flex flex-col justify-center shadow-inner">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Asientos Ocupados</span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-foreground">{loadingUsers ? "..." : usersCount}</span>
                <span className="text-xs text-muted-foreground font-medium">/ 50 de tu plan</span>
              </div>
              <div className="w-full bg-muted-foreground/15 h-1.5 rounded-full mt-3 overflow-hidden">
                <div className="bg-primary h-full rounded-full transition-all duration-300" style={{ width: `${(usersCount / 50) * 100}%` }} />
              </div>
            </div>
            <div className="p-5 border border-border/60 rounded bg-card/45 flex flex-col justify-center shadow-inner">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Cursos en Catálogo</span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-indigo-400">{loadingCourses ? "..." : coursesCount}</span>
                <span className="text-xs text-muted-foreground font-medium">unidades LMS</span>
              </div>
              <div className="w-full bg-muted-foreground/15 h-1.5 rounded-full mt-3 overflow-hidden">
                <div className="bg-indigo-500 h-full rounded-full" style={{ width: "40%" }} />
              </div>
            </div>
            <div className="p-5 border border-border/60 rounded bg-card/45 flex flex-col justify-center shadow-inner">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Módulos Activos</span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-emerald-400">{activeCount}</span>
                <span className="text-xs text-muted-foreground font-medium">/ 4 módulos totales</span>
              </div>
              <div className="w-full bg-muted-foreground/15 h-1.5 rounded-full mt-3 overflow-hidden">
                <div className="bg-emerald-500 h-full rounded-full transition-all duration-300" style={{ width: `${(activeCount / 4) * 100}%` }} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
