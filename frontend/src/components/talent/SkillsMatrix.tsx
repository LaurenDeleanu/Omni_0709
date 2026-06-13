"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Target, Zap, Search, Star, TrendingUp, ChevronRight, Filter,
  Brain, Sparkles, AlertTriangle, CheckCircle2, BookOpen, Users
} from "lucide-react";

const SKILLS_DATA = {
  roles: [
    {
      role: "Senior Software Engineer",
      department: "Engineering",
      required_skills: [
        { name: "Python", level_required: 4, level_actual: 4.2, category: "Técnica" },
        { name: "System Design", level_required: 4, level_actual: 3.8, category: "Técnica" },
        { name: "AWS / Cloud", level_required: 3, level_actual: 3.5, category: "Técnica" },
        { name: "TypeScript", level_required: 3, level_actual: 3.1, category: "Técnica" },
        { name: "Mentoring", level_required: 3, level_actual: 2.8, category: "Liderazgo" },
        { name: "Code Review", level_required: 4, level_actual: 4.5, category: "Técnica" },
        { name: "Communication", level_required: 3, level_actual: 3.6, category: "Soft Skills" },
        { name: "Agile / Scrum", level_required: 2, level_actual: 3.2, category: "Metodología" },
      ],
      headcount: 12,
    },
    {
      role: "Product Manager",
      department: "Product",
      required_skills: [
        { name: "User Research", level_required: 4, level_actual: 3.5, category: "Producto" },
        { name: "Roadmapping", level_required: 4, level_actual: 4.1, category: "Producto" },
        { name: "Data Analysis", level_required: 3, level_actual: 2.9, category: "Analítica" },
        { name: "Stakeholder Mgmt", level_required: 4, level_actual: 3.7, category: "Soft Skills" },
        { name: "SQL", level_required: 2, level_actual: 2.5, category: "Técnica" },
        { name: "A/B Testing", level_required: 3, level_actual: 2.8, category: "Analítica" },
      ],
      headcount: 5,
    },
    {
      role: "QA Engineer",
      department: "Engineering",
      required_skills: [
        { name: "Test Automation", level_required: 4, level_actual: 3.6, category: "Técnica" },
        { name: "Cypress / Playwright", level_required: 3, level_actual: 3.4, category: "Técnica" },
        { name: "API Testing", level_required: 3, level_actual: 3.8, category: "Técnica" },
        { name: "CI/CD Integration", level_required: 2, level_actual: 2.3, category: "DevOps" },
        { name: "Bug Triage", level_required: 3, level_actual: 4.0, category: "Metodología" },
      ],
      headcount: 4,
    },
  ],
  org_gaps: [
    { skill: "Kubernetes / Docker", demand_level: 3, current_avg: 1.8, roles_affected: 3, recommendation: "Programa de formación en contenedores Q3" },
    { skill: "Machine Learning", demand_level: 2, current_avg: 0.9, roles_affected: 2, recommendation: "Contratar ML Engineer o formar equipo existente" },
    { skill: "Cybersecurity", demand_level: 3, current_avg: 1.5, roles_affected: 4, recommendation: "Workshop de seguridad + certificación CISSP" },
    { skill: "Data Engineering", demand_level: 2, current_avg: 1.2, roles_affected: 2, recommendation: "Curso de Data Engineering en plataforma online" },
    { skill: "UX Research", demand_level: 2, current_avg: 1.6, roles_affected: 1, recommendation: "Mentoring con consultor UX externo" },
  ],
};

const CATEGORY_COLORS: Record<string, string> = {
  "Técnica": "bg-blue-500/10 text-blue-500 border-blue-500/20",
  "Soft Skills": "bg-purple-500/10 text-purple-500 border-purple-500/20",
  "Liderazgo": "bg-amber-500/10 text-amber-500 border-amber-500/20",
  "Metodología": "bg-indigo-500/10 text-indigo-500 border-indigo-500/20",
  "Analítica": "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
  "Producto": "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  "DevOps": "bg-rose-500/10 text-rose-500 border-rose-500/20",
};

export function SkillsMatrix() {
  const [selectedRole, setSelectedRole] = useState(0);
  const [searchSkill, setSearchSkill] = useState("");

  const role = SKILLS_DATA.roles[selectedRole];
  const filteredSkills = useMemo(() => {
    if (!searchSkill) return role.required_skills;
    return role.required_skills.filter(s =>
      s.name.toLowerCase().includes(searchSkill.toLowerCase()) ||
      s.category.toLowerCase().includes(searchSkill.toLowerCase())
    );
  }, [role, searchSkill]);

  const avgGap = useMemo(() => {
    const gaps = role.required_skills.map(s => s.level_required - s.level_actual);
    return (gaps.reduce((a, b) => a + b, 0) / gaps.length).toFixed(1);
  }, [role]);

  const skillsOnTrack = role.required_skills.filter(s => s.level_actual >= s.level_required).length;

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Roles Definidos</CardTitle>
            <Target className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{SKILLS_DATA.roles.length}</div>
            <p className="text-[10px] text-muted-foreground mt-1">Con matriz de skills</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Skills Cubiertas</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{skillsOnTrack}/{role.required_skills.length}</div>
            <p className="text-[10px] text-muted-foreground mt-1">En nivel requerido</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Gap Medio</CardTitle>
            <TrendingUp className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{parseFloat(avgGap) > 0 ? `+${avgGap}` : avgGap}</div>
            <p className="text-[10px] text-muted-foreground mt-1">Diferencia promedio</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Headcount</CardTitle>
            <Users className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{role.headcount}</div>
            <p className="text-[10px] text-muted-foreground mt-1">{role.department}</p>
          </CardContent>
        </Card>
      </div>

      {/* Role Selector */}
      <div className="flex gap-1.5 flex-wrap">
        {SKILLS_DATA.roles.map((r, i) => (
          <Button
            key={r.role}
            variant={selectedRole === i ? "default" : "outline"}
            size="sm"
            className="text-xs"
            onClick={() => setSelectedRole(i)}
          >
            {r.role}
          </Button>
        ))}
      </div>

      {/* Skills Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary" />
                Skills Requeridas — {role.role}
              </CardTitle>
              <div className="relative">
                <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="h-7 pl-8 w-36 text-xs bg-card/60"
                  placeholder="Filtrar skill..."
                  value={searchSkill}
                  onChange={e => setSearchSkill(e.target.value)}
                />
              </div>
            </div>
            <CardDescription>Nivel requerido vs nivel actual del equipo ({role.headcount} personas)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {filteredSkills.map(skill => {
              const gap = skill.level_required - skill.level_actual;
              const isOnTrack = gap <= 0;
              const actualPct = (skill.level_actual / 5) * 100;
              const requiredPct = (skill.level_required / 5) * 100;

              return (
                <div key={skill.name} className="p-3 rounded-xl bg-muted/10 border border-border/30 hover:border-border/60 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold">{skill.name}</span>
                      <Badge className={`text-[9px] ${CATEGORY_COLORS[skill.category] || "bg-slate-500/10 border-slate-500/20 text-slate-500"}`}>
                        {skill.category}
                      </Badge>
                    </div>
                    {isOnTrack ? (
                      <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold">
                        <CheckCircle2 className="w-3 h-3 mr-0.5" /> Cubierta
                      </Badge>
                    ) : (
                      <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-bold">
                        <AlertTriangle className="w-3 h-3 mr-0.5" /> Gap: {Math.abs(gap).toFixed(1)}
                      </Badge>
                    )}
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground w-16">Requerido</span>
                      <div className="flex-1 h-2 bg-muted/30 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-indigo-500/40"
                          style={{ width: `${requiredPct}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-bold text-muted-foreground w-6 text-right">{skill.level_required}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground w-16">Actual</span>
                      <div className="flex-1 h-2 bg-muted/30 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isOnTrack ? "bg-emerald-500" : "bg-amber-500"}`}
                          style={{ width: `${actualPct}%` }}
                        />
                      </div>
                      <span className={`text-[10px] font-bold w-6 text-right ${isOnTrack ? "text-emerald-500" : "text-amber-500"}`}>
                        {skill.level_actual}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Org-Wide Gaps */}
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Gaps Organizacionales
            </CardTitle>
            <CardDescription>Skills con mayor brecha en la organización y recomendaciones</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {SKILLS_DATA.org_gaps.map(gap => {
              const severity = gap.current_avg < gap.demand_level * 0.5 ? "high" : gap.current_avg < gap.demand_level * 0.8 ? "medium" : "low";
              return (
                <div key={gap.skill} className={`p-4 rounded-xl border ${
                  severity === "high" ? "border-rose-500/20 bg-rose-500/5" :
                  severity === "medium" ? "border-amber-500/20 bg-amber-500/5" :
                  "border-border/30 bg-muted/5"
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        severity === "high" ? "bg-rose-500" :
                        severity === "medium" ? "bg-amber-500" : "bg-blue-500"
                      }`} />
                      <span className="text-sm font-bold">{gap.skill}</span>
                    </div>
                    <Badge variant="outline" className="text-[10px]">{gap.roles_affected} roles</Badge>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] text-muted-foreground">Nivel actual: {gap.current_avg}</span>
                    <ChevronRight className="h-3 w-3 text-muted-foreground" />
                    <span className="text-[10px] text-muted-foreground">Requerido: {gap.demand_level}</span>
                  </div>
                  <Progress value={(gap.current_avg / gap.demand_level) * 100} className={`h-1.5 mb-2 ${
                    severity === "high" ? "[&>div]:bg-rose-500" :
                    severity === "medium" ? "[&>div]:bg-amber-500" : "[&>div]:bg-blue-500"
                  }`} />
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <BookOpen className="h-3 w-3 text-primary" />
                    {gap.recommendation}
                  </p>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
