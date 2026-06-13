"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useUser } from "@/hooks/use-user";
import {
  Target, ChevronDown, ChevronRight, ArrowDown, Star, Users,
  Building2, Goal, AlertCircle, Sparkles, CheckCircle2
} from "lucide-react";

interface Objective {
  id: string;
  title: string;
  description?: string;
  owner_id: string;
  status: string;
  progress?: number;
  key_results?: { title: string; target_value: number; current_value: number; unit: string }[];
}

interface OKRTreeNode {
  id: string;
  title: string;
  level: "company" | "department" | "team" | "individual";
  owner: string;
  status: string;
  progress: number;
  keyResults: { title: string; progress: number }[];
  children: OKRTreeNode[];
  collapsed?: boolean;
}

function buildOKRTree(objectives: Objective[]): OKRTreeNode[] {
  const companyOKRs: OKRTreeNode[] = [
    {
      id: "co-1", title: "Expandir a 5 mercados EU", level: "company",
      owner: "CEO", status: "On Track", progress: 72,
      keyResults: [
        { title: "Lanzar en Alemania", progress: 100 },
        { title: "Lanzar en Francia", progress: 80 },
        { title: "Contratar equipo local en UK", progress: 35 },
      ],
      children: []
    },
    {
      id: "co-2", title: "Alcanzar €2.5M ARR", level: "company",
      owner: "CEO", status: "At Risk", progress: 58,
      keyResults: [
        { title: "Cerrar 50 clientes enterprise", progress: 60 },
        { title: "Aumentar NRR al 120%", progress: 45 },
      ],
      children: []
    },
  ];

  const userObjectives = objectives.map(o => {
    const okrProgress = o.progress || 0;
    const krs = (o.key_results || []).map(kr => ({
      title: kr.title,
      progress: kr.target_value > 0 ? Math.round((kr.current_value / kr.target_value) * 100) : 0,
    }));

    const status = okrProgress >= 70 ? "On Track" : okrProgress >= 40 ? "At Risk" : "Behind";

    return {
      id: o.id,
      title: o.title,
      level: "individual" as const,
      owner: "Employee",
      status,
      progress: okrProgress,
      keyResults: krs,
      children: [],
    };
  });

  const deptOKRs: OKRTreeNode[] = [
    {
      id: "dept-eng", title: "Reducir tiempo de deployment a <5 min", level: "department",
      owner: "Engineering", status: "On Track", progress: 85,
      keyResults: [
        { title: "Migrar CI/CD a GitHub Actions", progress: 100 },
        { title: "Implementar cache de builds", progress: 70 },
      ],
      children: userObjectives.filter(o => o.title.toLowerCase().includes("deploy") || o.title.toLowerCase().includes("ci")),
    },
    {
      id: "dept-sales", title: "Aumentar pipeline en un 200%", level: "department",
      owner: "Sales", status: "At Risk", progress: 55,
      keyResults: [
        { title: "Contratar 3 nuevos AEs", progress: 100 },
        { title: "Lanzar campaña outbound", progress: 30 },
      ],
      children: userObjectives.filter(o => o.title.toLowerCase().includes("pipeline") || o.title.toLowerCase().includes("sales")),
    },
  ];

  companyOKRs.forEach(co => {
    co.children = deptOKRs.filter(d => {
      if (co.title.includes("mercados")) return d.owner === "Sales";
      if (co.title.includes("ARR")) return d.owner === "Sales" || d.owner === "Engineering";
      return true;
    });
  });

  return companyOKRs;
}

function OKRNode({ node, depth = 0 }: { node: OKRTreeNode; depth?: number }) {
  const [collapsed, setCollapsed] = useState(depth >= 2);

  const statusBadge = () => {
    if (node.status === "On Track") return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold"><CheckCircle2 className="w-3 h-3 mr-1" /> On Track</Badge>;
    if (node.status === "At Risk") return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-bold"><AlertCircle className="w-3 h-3 mr-1" /> At Risk</Badge>;
    return <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] font-bold"><AlertCircle className="w-3 h-3 mr-1" /> Behind</Badge>;
  };

  const levelIcon = () => {
    if (node.level === "company") return <Building2 className="h-4 w-4 text-indigo-500" />;
    if (node.level === "department") return <Users className="h-4 w-4 text-blue-500" />;
    if (node.level === "team") return <Users className="h-4 w-4 text-cyan-500" />;
    return <Target className="h-4 w-4 text-amber-500" />;
  };

  const hasChildren = node.children.length > 0;
  const totalKRs = node.keyResults.length;

  return (
    <div className="space-y-1">
      <div
        className={`p-4 rounded-xl border transition-all cursor-pointer group ${
          depth === 0
            ? "bg-indigo-500/5 border-indigo-500/20 hover:border-indigo-500/40"
            : depth === 1
            ? "bg-blue-500/5 border-blue-500/20 hover:border-blue-500/40 ml-6"
            : "bg-muted/10 border-border/30 hover:border-border/60 ml-12"
        }`}
        onClick={() => hasChildren && setCollapsed(!collapsed)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            {hasChildren ? (
              collapsed ? <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" /> : <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : (
              <div className="w-4 shrink-0" />
            )}
            {levelIcon()}
            <div className="min-w-0">
              <p className="text-sm font-bold truncate">{node.title}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] text-muted-foreground capitalize">{node.level}</span>
                <span className="text-[10px] text-muted-foreground">· {node.owner}</span>
                <span className="text-[10px] text-muted-foreground">
                  · {totalKRs} KR{totalKRs !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {statusBadge()}
            <div className="w-20">
              <div className="flex items-center gap-1.5">
                <Progress value={node.progress} className="h-1.5 flex-1" />
                <span className="text-xs font-bold text-muted-foreground w-8 text-right">{Math.round(node.progress)}%</span>
              </div>
            </div>
          </div>
        </div>

        {!collapsed && node.keyResults.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border/30 space-y-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground ml-7">Key Results</p>
            {node.keyResults.map((kr, i) => (
              <div key={i} className="flex items-center gap-2 ml-7">
                <div className={`w-1.5 h-1.5 rounded-full ${kr.progress >= 100 ? "bg-emerald-500" : kr.progress >= 50 ? "bg-blue-500" : "bg-amber-500"}`} />
                <span className="text-xs flex-1">{kr.title}</span>
                <span className="text-[10px] font-bold text-muted-foreground">{kr.progress}%</span>
              </div>
            ))}
          </div>
        )}

        {node.children.length > 0 && !collapsed && (
          <div className="mt-1 pt-2">
            {node.children.map(child => (
              <div key={child.id} className="relative">
                <div className="absolute left-8 top-0 bottom-0 w-px bg-border/50" />
                <OKRNode node={child} depth={depth + 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function OKRCascadingTree() {
  const { user } = useUser();
  const [onlyShowMine, setOnlyShowMine] = useState(false);

  const { data: objectives, isLoading, error } = useQuery<Objective[]>({
    queryKey: ["all-objectives"],
    queryFn: () => fetchClient("/goals?limit=100").then(r => r),
  });

  const tree = useMemo(() => buildOKRTree(objectives || []), [objectives]);

  if (isLoading) {
    return (
      <Card className="glass">
        <CardHeader><Skeleton className="h-6 w-48" /></CardHeader>
        <CardContent className="space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Goal className="h-5 w-5 text-primary" />
              Cascada de Objetivos (OKRs)
            </CardTitle>
            <CardDescription>Alineación de objetivos: Empresa → Departamento → Equipo → Individual</CardDescription>
          </div>
          <Badge className="bg-primary/10 text-primary border-primary/20 text-xs font-bold">
            <Sparkles className="h-3 w-3 mr-1" /> {tree.length} objetivos empresa
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {tree.map(companyOKR => (
          <OKRNode key={companyOKR.id} node={companyOKR} />
        ))}
        {tree.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
            <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Goal className="w-7 h-7" />
            </div>
            <p className="text-sm font-semibold">Sin objetivos de empresa</p>
            <p className="text-xs text-muted-foreground max-w-xs">Define objetivos a nivel de compañía para empezar a alinear los OKRs de tu organización.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
