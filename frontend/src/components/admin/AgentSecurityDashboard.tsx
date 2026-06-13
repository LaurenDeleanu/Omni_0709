"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Shield, AlertTriangle, CheckCircle2, Lock, Key, Users, Sparkles,
  Wrench, EyeOff, Activity
} from "lucide-react";

const DESTRUCTIVE_TOOLS = [
  "process_payroll", "update_compensation", "archive_employee", "approve_vacation",
  "move_candidate_stage", "promote_to_employee", "create_payroll_cycle", "submit_whistleblower"
];

const AGENTS = [
  {
    name: "HR Copilot", id: "agent-hr-copilot",
    role: "hr_admin", tools: 24, destructive_tools: ["process_payroll", "archive_employee", "promote_to_employee"],
    last_audited: "2026-06-12", guardrails: ["Human approval for destructive ops", "Budget limit: €5K/action", "Rate limit: 30 req/min"],
  },
  {
    name: "Recruiter Agent", id: "agent-recruiter",
    role: "recruiter", tools: 18, destructive_tools: ["move_candidate_stage", "promote_to_employee"],
    last_audited: "2026-06-11", guardrails: ["Cannot reject candidates", "Must present top 5 for final review", "No salary negotiation without HR approval"],
  },
  {
    name: "IT Helpdesk Agent", id: "agent-it-helpdesk",
    role: "it_manager", tools: 22, destructive_tools: [],
    last_audited: "2026-06-12", guardrails: ["Max 3 auto-resolves before human review", "No admin credential changes", "Ticket reopen if user reports unresolved"],
  },
  {
    name: "Payroll Agent", id: "agent-payroll",
    role: "hr_admin", tools: 12, destructive_tools: ["process_payroll", "create_payroll_cycle", "update_compensation"],
    last_audited: "2026-06-10", guardrails: ["Destructive ops require dual approval", "Max payroll amount: €50K/batch", "Full audit log for all payroll changes"],
  },
  {
    name: "Compliance Agent", id: "agent-compliance",
    role: "legal_manager", tools: 16, destructive_tools: ["submit_whistleblower"],
    last_audited: "2026-06-09", guardrails: ["Cannot modify legal documents", "Draft-only mode for contracts", "GDPR data masking enforced"],
  },
  {
    name: "Finance Agent", id: "agent-finance",
    role: "finance_manager", tools: 14, destructive_tools: ["update_compensation"],
    last_audited: "2026-06-08", guardrails: ["No wire transfers", "Expenses >€1K require manager approval", "Currency conversion via ECB rates only"],
  },
];

export function AgentSecurityDashboard() {
  const totalTools = AGENTS.reduce((a, b) => a + b.tools, 0);
  const totalDestructive = AGENTS.reduce((a, b) => a + b.destructive_tools.length, 0);
  const agentsWithGuardrails = AGENTS.filter(a => a.guardrails.length > 0).length;

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: "Agentes Activos", value: AGENTS.length, icon: Sparkles, color: "text-primary" },
          { label: "Herramientas Asignadas", value: totalTools, icon: Wrench, color: "text-indigo-500" },
          { label: "Herramientas Destructivas", value: totalDestructive, icon: AlertTriangle, color: "text-rose-500" },
          { label: "Agentes con Guardrails", value: `${agentsWithGuardrails}/${AGENTS.length}`, icon: Shield, color: "text-emerald-500" },
        ].map(kpi => (
          <Card key={kpi.label} className="glass shadow-sm hover:shadow-md transition-shadow">
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

      {/* Agent Security Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {AGENTS.map(agent => (
          <Card key={agent.id} className={`glass shadow-sm hover:shadow-md transition-shadow ${
            agent.destructive_tools.length > 2 ? "border-amber-500/20" : "border-border/30"
          }`}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    agent.destructive_tools.length > 0 ? "bg-amber-500/10 text-amber-500" : "bg-emerald-500/10 text-emerald-500"
                  }`}>
                    {agent.destructive_tools.length > 0 ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                  </div>
                  <div>
                    <CardTitle className="text-sm font-bold">{agent.name}</CardTitle>
                    <CardDescription className="text-[10px] capitalize">{agent.role.replace(/_/g, " ")}</CardDescription>
                  </div>
                </div>
                <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px] font-bold">{agent.tools} tools</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {/* Destructive Tools */}
              {agent.destructive_tools.length > 0 && (
                <div className="p-2 rounded-lg bg-rose-500/5 border border-rose-500/10">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-500 mb-1 flex items-center gap-1">
                    <Lock className="h-3 w-3" /> Destructivas ({agent.destructive_tools.length})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {agent.destructive_tools.map(t => (
                      <Badge key={t} className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[9px] font-mono">
                        {t}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Guardrails */}
              {agent.guardrails.length > 0 && (
                <div className="p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-500 mb-1 flex items-center gap-1">
                    <Shield className="h-3 w-3" /> Guardrails ({agent.guardrails.length})
                  </p>
                  <ul className="text-[9px] text-muted-foreground space-y-0.5">
                    {agent.guardrails.map((g, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <CheckCircle2 className="h-2.5 w-2.5 text-emerald-500 mt-0.5 shrink-0" />
                        {g}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex items-center justify-between pt-1 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1"><Activity className="h-3 w-3" /> Auditado: {agent.last_audited}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Security Recommendations */}
      <Card className="glass border-amber-500/20">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Recomendaciones de Seguridad
          </CardTitle>
          <CardDescription>Basado en el análisis de permisos y herramientas</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {[
            { severity: "high", text: "El agente de Payroll tiene acceso a 3 herramientas destructivas. Considerar segregación de funciones en 2 agentes separados." },
            { severity: "medium", text: "El agente de HR Copilot tiene 24 herramientas asignadas. Evaluar reducción por principio de mínimo privilegio." },
            { severity: "medium", text: "3 agentes comparten la herramienta 'update_compensation'. Centralizar en un solo agente de compensación." },
            { severity: "low", text: "El agente de Compliance no fue auditado en los últimos 4 días. Programar auditoría semanal automática." },
            { severity: "low", text: "Considerar añadir rate limiting a agentes con acceso a APIs externas (Finance, Payroll)." },
          ].map((rec, i) => (
            <div key={i} className={`flex items-start gap-3 p-2.5 rounded-lg ${
              rec.severity === "high" ? "bg-rose-500/5 border border-rose-500/10" :
              rec.severity === "medium" ? "bg-amber-500/5 border border-amber-500/10" :
              "bg-blue-500/5 border border-blue-500/10"
            }`}>
              <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                rec.severity === "high" ? "bg-rose-500" : rec.severity === "medium" ? "bg-amber-500" : "bg-blue-500"
              }`} />
              <p className="text-sm">{rec.text}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
