"use client";

import { useState, useEffect } from "react";
import { Link } from "@/i18n/routing";
import {
  BookOpen,
  Code2,
  Bot,
  Shield,
  Building2,
  ArrowRight,
  ChevronRight,
  Database,
  Globe,
  Key,
  Server,
  Webhook,
  Terminal,
  Workflow,
} from "lucide-react";

const sections = [
  {
    id: "introduccion",
    title: "Introducción",
    icon: BookOpen,
    content: `SuccessCore HR es una plataforma SaaS empresarial de gestión de recursos humanos 
potenciada por 10 agentes de inteligencia artificial nativos.

La plataforma expone una API REST completa documentada con OpenAPI. 
Todas las peticiones requieren autenticación mediante JWT (Auth0) o API key.

URL base: https://api.successcore.com/api/v1`,
  },
  {
    id: "autenticacion",
    title: "Autenticación",
    icon: Shield,
    content: `La API utiliza dos métodos de autenticación:

1. JWT Bearer Token (Auth0 SSO)
   Authorization: Bearer <jwt_token>

2. API Key (para integraciones y agentes públicos)
   X-API-Key: <api_key>

Headers requeridos en todas las peticiones:
- X-Tenant-ID: Identificador único del tenant
- Content-Type: application/json`,
  },
  {
    id: "modulos",
    title: "Módulos de la API",
    icon: Database,
    content: `La plataforma expone 58 endpoints organizados en los siguientes módulos:

| Módulo | Ruta base | Descripción |
|--------|-----------|-------------|
| Usuarios | /users | CRUD de empleados y perfiles |
| Empleados | /employees | Historial laboral y org-chart |
| Nóminas | /pay | Ciclos de nómina, payslips |
| Finanzas | /finance | Gastos, ledger contable |
| Reclutamiento | /hire | Pipeline ATS, candidatos |
| Formación | /training | Cursos, progreso, FUNDAE |
| Rendimiento | /grow | OKRs, evaluaciones |
| IT | /it | Tickets, knowledge base |
| CRM | /sales | Pipeline ventas, leads |
| Calendario | /calendar | Eventos, PTO, vacaciones |
| Proyectos | /work | Tareas, proyectos |
| Legal | /legal | Contratos, compliance |
| Reportes | /reports | PDF, Excel, programados |
| Agentes IA | /agents | CRUD y ejecución de agentes |
| Chat | /chat | Mensajería colaborativa |
| Workflows | /workflows | Automatización de procesos |
| RBAC | /rbac | Roles y permisos |
| Notificaciones | /notifications | Push, email, in-app |
| Integraciones | /integrations | Slack, DocuSign, OAuth |
| Billing | /billing | Facturación, API keys |`,
  },
  {
    id: "agentes-ia",
    title: "Agentes de IA",
    icon: Bot,
    content: `El sistema de agentes de IA es el núcleo diferenciador de SuccessCore.

Agentes disponibles:
- Copiloto de Plataforma (COPILOT): Asistente general con delegación
- HR Assistant Pro (HR_ASSISTANT): Consultas de empleados, org-chart
- Payroll Specialist (PAYROLL_SPECIALIST): Nóminas, impuestos
- IT Helpdesk (IT_HELPDESK): Tickets, knowledge base
- Recruiter Pro (RECRUITER): Pipeline hiring
- Sales Coach (SALES_COACH): CRM, leads
- Performance Coach (PERFORMANCE_COACH): OKRs, evaluaciones
- Onboarding Buddy (ONBOARDING_BUDDY): Planes onboarding
- Compliance Officer (COMPLIANCE_OFFICER): Legal, GDPR, FUNDAE
- Data Analyst (DATA_ANALYST): Analytics, tendencias
- Finance Manager (FINANCE_MANAGER): Ledger, presupuestos

Ejecutar un agente:
POST /api/v1/agents/{agent_id}/run
{
  "message": "¿Cuál es el salario neto de María García?",
  "user_id": "user_123"
}`,
  },
  {
    id: "copilot",
    title: "API del Copilot",
    icon: Terminal,
    content: `El endpoint principal del copilot:

POST /api/v1/ai/copilot
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-ID: acme_corp

{
  "message": "Necesito aprobar las vacaciones del equipo de ventas",
  "module_context": "calendar",
  "user_context": {
    "user_id": "user_123",
    "roles": ["manager"],
    "department": "Ventas",
    "tenant_id": "acme_corp"
  }
}

Respuesta:
{
  "response": "He revisado las solicitudes pendientes...",
  "delegated": false,
  "tools_used": ["get_team_calendar"],
  "knowledge_sources": ["doc_vacaciones_v1"]
}`,
  },
  {
    id: "webhooks",
    title: "Webhooks y Eventos",
    icon: Webhook,
    content: `La plataforma emite eventos que pueden disparar webhooks y agentes:

Eventos disponibles:
- employee.created
- employee.updated
- employee.archived
- vacation.requested
- vacation.approved
- payroll.processed
- ticket.created
- ticket.resolved
- candidate.stage_changed
- onboarding.completed

Configurar un webhook:
POST /api/v1/agents/triggers
{
  "event": "employee.created",
  "agent_id": "onboarding_buddy_001",
  "filter_condition": "department == 'Engineering'",
  "auto_approve": true
}`,
  },
  {
    id: "errores",
    title: "Códigos de Error",
    icon: Code2,
    content: `La API utiliza códigos HTTP estándar:

- 200: Éxito
- 201: Recurso creado
- 400: Error de validación (datos inválidos)
- 401: No autenticado (token inválido o expirado)
- 403: No autorizado (sin permisos suficientes)
- 404: Recurso no encontrado
- 429: Rate limit excedido (demasiadas peticiones)
- 500: Error interno del servidor

Formato de error:
{
  "detail": "Descripción del error",
  "code": "VALIDATION_ERROR",
  "fields": {
    "email": "El email no es válido"
  }
}`,
  },
  {
    id: "rate-limits",
    title: "Límites y Rate Limiting",
    icon: Globe,
    content: `Límites por plan:

| Plan | API calls/mes | Agent runs/mes | Rate limit |
|------|---------------|----------------|------------|
| Free | 5.000 | 100 | 10 req/s |
| Starter | 50.000 | 500 | 50 req/s |
| Pro | 200.000 | 2.000 | 100 req/s |
| Enterprise | Ilimitadas | 50.000 | 500 req/s |

Headers de rate limit en cada respuesta:
- X-RateLimit-Limit: Límite de peticiones por ventana
- X-RateLimit-Remaining: Peticiones restantes
- X-RateLimit-Reset: Timestamp de reinicio`,
  },
  {
    id: "sdk",
    title: "SDKs y Librerías",
    icon: Key,
    content: `La API pública de agentes puede consumirse desde cualquier lenguaje.

Ejemplo con Python:
import httpx

async def run_agent(message: str, agent_id: str, api_key: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.successcore.com/api/v1/public/agents/{agent_id}/run",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            json={"message": message},
        )
        return response.json()

Ejemplo con TypeScript:
const response = await fetch(
  \`https://api.successcore.com/api/v1/public/agents/\${agentId}/run\`,
  {
    method: "POST",
    headers: {
      "X-API-Key": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  }
);`,
  },
  {
    id: "seguridad",
    title: "Seguridad y Compliance",
    icon: Shield,
    content: `Medidas de seguridad implementadas:

1. Autenticación: Auth0 SSO (Google, Microsoft, SAML) + login local
2. Autorización: RBAC granular por tenant
3. Transporte: TLS 1.3 en todas las comunicaciones
4. CSRF Protection: Tokens anti-CSRF
5. Rate Limiting: Por IP, API key y tenant
6. Encryption: AES-256 para datos sensibles en reposo
7. PII Masking: Enmascaramiento automático en respuestas AI
8. Audit Trail: Registro completo de acciones y ejecuciones AI
9. Data Residency: Almacenamiento configurable (EU por defecto)
10. GDPR: Derecho al olvido, exportación de datos, consentimiento`,
  },
];

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState("introduccion");
  const [animIn, setAnimIn] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setAnimIn(true), 50);
    return () => clearTimeout(t);
  }, []);

  const activeContent = sections.find((s) => s.id === activeSection);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* NAV */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-3 hover:opacity-80">
              <Building2 className="h-5 w-5 text-indigo-400" />
              <span className="text-foreground font-bold">SuccessCore</span>
              <span className="text-slate-500 text-sm">/ docs</span>
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"}/docs`}
                target="_blank"
                className="text-indigo-400 hover:text-indigo-300 text-sm transition-colors"
              >
                OpenAPI →
              </Link>
              <Link
                href="/login"
                className="py-2 px-4 bg-indigo-600 hover:bg-indigo-500 text-foreground text-sm font-semibold rounded-lg transition-colors"
              >
                Dashboard
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex gap-8">
          {/* Sidebar */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <nav className="sticky top-24 space-y-1">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 ${
                    activeSection === section.id
                      ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                      : "text-slate-400 hover:text-foreground hover:bg-white/5"
                  }`}
                >
                  <section.icon className="h-4 w-4 flex-shrink-0" />
                  {section.title}
                </button>
              ))}
            </nav>
          </aside>

          {/* Mobile section selector */}
          <div className="lg:hidden w-full mb-6">
            <select
              value={activeSection}
              onChange={(e) => setActiveSection(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-foreground text-sm"
            >
              {sections.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>

          {/* Content */}
          <main className="flex-1 min-w-0">
            {activeContent && (
              <div
                className={`transition-all duration-500 ${
                  animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                }`}
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                    <activeContent.icon className="h-5 w-5 text-indigo-400" />
                  </div>
                  <h1 className="text-3xl font-bold">{activeContent.title}</h1>
                </div>

                <div className="prose prose-invert max-w-none">
                  {activeContent.content.split("\n\n").map((paragraph, i) => {
                    // Check if it's a code block
                    if (paragraph.includes("```")) {
                      const codeContent = paragraph.replace(/```/g, "");
                      return (
                        <pre
                          key={i}
                          className="bg-white/5 border border-white/10 rounded-xl p-4 my-4 overflow-x-auto text-sm text-slate-300 font-mono leading-relaxed"
                        >
                          <code>{codeContent}</code>
                        </pre>
                      );
                    }

                    // Check if it's a markdown table
                    if (paragraph.includes("|") && paragraph.includes("---")) {
                      const lines = paragraph.split("\n").filter((l) => l.includes("|"));
                      const headers = lines[0]
                        .split("|")
                        .filter(Boolean)
                        .map((h) => h.trim());
                      const rows = lines.slice(2).map((line) =>
                        line
                          .split("|")
                          .filter(Boolean)
                          .map((c) => c.trim())
                      );

                      return (
                        <div key={i} className="overflow-x-auto my-4">
                          <table className="w-full text-sm border border-white/10 rounded-xl overflow-hidden">
                            <thead>
                              <tr className="bg-white/5">
                                {headers.map((h) => (
                                  <th key={h} className="text-left px-4 py-2 text-slate-300 font-medium">
                                    {h}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {rows.map((row, ri) => (
                                <tr
                                  key={ri}
                                  className="border-t border-white/5 hover:bg-white/[0.02]"
                                >
                                  {row.map((cell, ci) => (
                                    <td key={ci} className="px-4 py-2 text-slate-400">
                                      {cell}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      );
                    }

                    return (
                      <p key={i} className="text-slate-300 leading-relaxed mb-4 whitespace-pre-line">
                        {paragraph}
                      </p>
                    );
                  })}
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
