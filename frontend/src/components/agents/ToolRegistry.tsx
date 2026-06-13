"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Wrench, Search, Shield, Filter, BookOpen, Zap, Eye, Key, 
  Users, Calendar, CreditCard, Building, Briefcase, GraduationCap,
  TrendingUp, Clock, Sparkles, AlertCircle, ChevronRight
} from "lucide-react";

interface ToolDef {
  name: string;
  category: string;
  role_required: string;
}

interface ToolRegistryData {
  total_tools: number;
  modules: { name: string; count: number; tools: ToolDef[] }[];
  categories: Record<string, number>;
  role_requirements: Record<string, number>;
}

const MODULE_ICONS: Record<string, React.ReactNode> = {
  hr: <Users className="h-4 w-4" />,
  calendar: <Calendar className="h-4 w-4" />,
  payroll: <CreditCard className="h-4 w-4" />,
  finance: <CreditCard className="h-4 w-4" />,
  it: <Wrench className="h-4 w-4" />,
  sales: <TrendingUp className="h-4 w-4" />,
  training: <GraduationCap className="h-4 w-4" />,
  projects: <Building className="h-4 w-4" />,
  hire: <Briefcase className="h-4 w-4" />,
  scheduling: <Clock className="h-4 w-4" />,
  compliance: <Shield className="h-4 w-4" />,
};

const MODULE_COLORS: Record<string, string> = {
  hr: "bg-blue-500/10 border-blue-500/20 text-blue-500",
  calendar: "bg-indigo-500/10 border-indigo-500/20 text-indigo-500",
  payroll: "bg-emerald-500/10 border-emerald-500/20 text-emerald-500",
  finance: "bg-teal-500/10 border-teal-500/20 text-teal-500",
  it: "bg-amber-500/10 border-amber-500/20 text-amber-500",
  sales: "bg-rose-500/10 border-rose-500/20 text-rose-500",
  training: "bg-purple-500/10 border-purple-500/20 text-purple-500",
  projects: "bg-cyan-500/10 border-cyan-500/20 text-cyan-500",
  hire: "bg-orange-500/10 border-orange-500/20 text-orange-500",
  scheduling: "bg-violet-500/10 border-violet-500/20 text-violet-500",
  compliance: "bg-red-500/10 border-red-500/20 text-red-500",
};

const CATEGORY_BADGES: Record<string, string> = {
  read: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  create: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  update: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  delete: "bg-rose-500/10 text-rose-500 border-rose-500/20",
  action: "bg-purple-500/10 text-purple-500 border-purple-500/20",
};

const ROLE_LABELS: Record<string, string> = {
  employee: "Empleado", manager: "Manager", hr_admin: "Admin RH",
  sys_admin: "SysAdmin", recruiter: "Reclutador",
  finance_manager: "Finanzas", it_manager: "IT Manager", legal_manager: "Legal",
};

export function ToolRegistry() {
  const [search, setSearch] = useState("");
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery<ToolRegistryData>({
    queryKey: ["tool-registry"],
    queryFn: () => fetchClient("/tools/registry").then(r => r),
  });

  const filteredTools = useMemo(() => {
    if (!data) return [];
    let tools: (ToolDef & { module: string })[] = [];
    for (const mod of data.modules) {
      for (const tool of mod.tools) {
        if (selectedModule && mod.name !== selectedModule) continue;
        if (selectedCategory && tool.category !== selectedCategory) continue;
        if (search && !tool.name.includes(search.toLowerCase())) continue;
        tools.push({ ...tool, module: mod.name });
      }
    }
    return tools;
  }, [data, selectedModule, selectedCategory, search]);

  if (isLoading) {
    return (
      <Card className="glass">
        <CardHeader><Skeleton className="h-6 w-40" /></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="glass border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive">Unable to load tool registry.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI + Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
            <Wrench className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold">{data.total_tools} Herramientas</h3>
            <p className="text-xs text-muted-foreground">{data.modules.length} módulos · {Object.keys(data.categories).length} categorías</p>
          </div>
        </div>
        <div className="relative">
          <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="h-8 pl-8 w-48 text-xs bg-card/60"
            placeholder="Buscar herramienta..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Module + Category Filters */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setSelectedModule(null)}
          className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${!selectedModule ? "bg-primary text-primary-foreground" : "bg-muted/30 text-muted-foreground hover:bg-muted"}`}
        >
          Todos ({data.total_tools})
        </button>
        {data.modules.map(mod => (
          <button
            key={mod.name}
            onClick={() => setSelectedModule(selectedModule === mod.name ? null : mod.name)}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all capitalize flex items-center gap-1.5 ${
              selectedModule === mod.name ? "bg-primary text-primary-foreground" : "bg-muted/30 text-muted-foreground hover:bg-muted"
            }`}
          >
            {MODULE_ICONS[mod.name] || <Wrench className="h-3 w-3" />}
            {mod.name} ({mod.count})
          </button>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        {Object.entries(data.categories).map(([cat, count]) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-bold transition-all capitalize ${
              selectedCategory === cat ? "bg-primary text-primary-foreground" : "bg-muted/30 text-muted-foreground hover:bg-muted"
            }`}
          >
            {cat} ({count})
          </button>
        ))}
      </div>

      {/* Tools Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filteredTools.map(tool => (
          <div key={`${tool.module}-${tool.name}`} className={`p-3 rounded-xl border transition-all hover:shadow-md ${MODULE_COLORS[tool.module] || "bg-slate-500/10 border-slate-500/20 text-slate-500"}`}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5">
                {MODULE_ICONS[tool.module] || <Wrench className="h-3 w-3" />}
                <span className="text-sm font-bold">{tool.name}</span>
              </div>
              <Badge className={`text-[9px] ${CATEGORY_BADGES[tool.category] || ""}`}>{tool.category}</Badge>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <Shield className="h-3 w-3" />
              <span className="capitalize">{ROLE_LABELS[tool.role_required] || tool.role_required}</span>
            </div>
          </div>
        ))}
        {filteredTools.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center py-8 text-center gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Wrench className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted-foreground">No se encontraron herramientas con los filtros actuales.</p>
          </div>
        )}
      </div>
    </div>
  );
}
