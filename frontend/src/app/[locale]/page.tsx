"use client";

import { Link } from "@/i18n/routing";
import {
  Users,
  BarChart3,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Building2,
  Bot,
  Globe,
  Banknote,
  GraduationCap,
  Headphones,
  Scale,
  Check,
} from "lucide-react";
import { useState, useEffect } from "react";

const features = [
  {
    icon: Bot,
    title: "10 Agentes de IA Nativos",
    desc: "HR Assistant, Payroll Specialist, Recruiter Pro, IT Helpdesk y más. Agentes especializados que operan sobre tus datos reales con RBAC.",
  },
  {
    icon: Users,
    title: "28 Módulos Integrados",
    desc: "Desde empleados y nóminas hasta CRM, reclutamiento ATS, formación LMS y analítica avanzada. Todo en una sola plataforma.",
  },
  {
    icon: Globe,
    title: "Multi-idioma y Multi-tenant",
    desc: "6 idiomas (ES, EN, FR, DE, PT, AR con RTL). Aislamiento completo de datos por empresa. BYOK para tus propias claves AI.",
  },
  {
    icon: ShieldCheck,
    title: "Compliance Automatizado",
    desc: "GDPR, FUNDAE, registro horario digital (RDL 8/2019), legislación laboral española. Cumplimiento sin esfuerzo.",
  },
  {
    icon: Banknote,
    title: "ROI Medible",
    desc: "Reduce costes operativos de RRHH un 40-60%. Nóminas automatizadas, onboarding sin fricción, soporte IT 24/7 vía AI.",
  },
  {
    icon: Scale,
    title: "Seguridad Enterprise",
    desc: "Auth0 SSO, RBAC granular, CSRF protection, encriptación de datos, PII masking, audit trail completo.",
  },
];

const modules = [
  { name: "Gestión de Empleados", desc: "CRUD completo, historial, org-chart" },
  { name: "Nóminas y Compensación", desc: "Ciclos, payslips, impuestos, bonus" },
  { name: "Reclutamiento ATS", desc: "Pipeline hiring, resume parsing, entrevistas" },
  { name: "Control Horario", desc: "Fichaje digital, turnos, horas extra" },
  { name: "CRM y Ventas", desc: "Pipeline, leads, scoring, email generation" },
  { name: "Formación LMS", desc: "Cursos, progreso, FUNDAE, certificaciones" },
  { name: "Evaluaciones y OKRs", desc: "Performance reviews, objetivos, feedback" },
  { name: "IT Helpdesk", desc: "Tickets, knowledge base, activos" },
  { name: "Legal y Compliance", desc: "Contratos, GDPR, whistleblower" },
  { name: "People Analytics", desc: "Dashboards, reportes PDF/Excel, tendencias" },
  { name: "Proyectos", desc: "Tareas, kanban, wiki, colaboración" },
  { name: "Chat Colaborativo", desc: "Mensajería, menciones, archivos" },
];

const pricingPlans = [
  {
    name: "Starter",
    price: "6€",
    period: "/empleado/mes",
    description: "Para startups y pymes que dan sus primeros pasos en digitalización HR.",
    features: [
      "Hasta 250 empleados",
      "3 agentes de IA",
      "Módulos core HR",
      "Control horario digital",
      "Portal del empleado",
      "Soporte por email",
    ],
    cta: "Comenzar gratis",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "12€",
    period: "/empleado/mes",
    description: "Para empresas en crecimiento que necesitan automatización avanzada.",
    features: [
      "Hasta 1.000 empleados",
      "7 agentes de IA",
      "Todos los módulos",
      "API pública",
      "Integraciones (Slack, DocuSign)",
      "Soporte prioritario",
      "Onboarding personalizado",
    ],
    cta: "Prueba gratuita",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Consultar",
    period: "",
    description: "Para grandes organizaciones con necesidades de personalización y escala.",
    features: [
      "Empleados ilimitados",
      "10 agentes de IA + Omni Master",
      "Agentes personalizados",
      "Multi-tenant avanzado",
      "BYOK (Bring Your Own Key)",
      "SLA 99.9%",
      "Soporte 24/7 dedicado",
      "Integraciones enterprise",
    ],
    cta: "Hablar con ventas",
    highlighted: false,
  },
];

export default function LandingPage() {
  const [animIn, setAnimIn] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setAnimIn(true), 50);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground overflow-hidden">
      {/* ── NAV ──────────────────────────────────────────────────── */}
      <nav
        className={`sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-white/5 transition-all duration-700 ${
          animIn ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <Building2 className="h-5 w-5 text-foreground" />
              </div>
              <span className="text-foreground font-bold text-lg">SuccessCore</span>
              <span className="text-primary text-xs font-semibold hidden sm:inline">HR Platform</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/pricing"
                className="text-primary/80 hover:text-foreground text-sm transition-colors hidden sm:block"
              >
                Precios
              </Link>
              <Link
                href="/login"
                className="text-primary/80 hover:text-foreground text-sm transition-colors"
              >
                Iniciar sesión
              </Link>
              <Link
                href="/login"
                className="py-2 px-4 bg-primary hover:bg-indigo-500 text-foreground text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-indigo-500/25"
              >
                Probar gratis
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* ── HERO ─────────────────────────────────────────────────── */}
      <section className="relative pt-20 pb-32 sm:pt-32 sm:pb-40 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-primary/10 rounded-full blur-3xl" />
          <div className="absolute top-1/3 -right-40 w-[500px] h-[500px] bg-violet-600/8 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 left-1/4 w-[400px] h-[400px] bg-blue-600/5 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div
            className={`transition-all duration-700 ease-out ${
              animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <div className="inline-flex items-center gap-2 bg-primary/10 border border-indigo-500/20 rounded-full px-4 py-1.5 mb-8">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-indigo-300 text-sm font-medium">
                Potenciado con 10 agentes de IA nativos
              </span>
            </div>
          </div>

          <h1
            className={`text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight transition-all duration-700 delay-100 ease-out ${
              animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            El HR del futuro,
            <br />
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
              disponible hoy.
            </span>
          </h1>

          <p
            className={`mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed transition-all duration-700 delay-200 ease-out ${
              animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            La primera plataforma HR todo-en-uno con agentes de IA que automatizan
            el 60% del trabajo administrativo. Gestiona empleados, nóminas,
            reclutamiento, compliance y más desde un solo lugar.
          </p>

          <div
            className={`mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 transition-all duration-700 delay-300 ease-out ${
              animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <Link
              href="/login"
              className="w-full sm:w-auto py-3.5 px-8 bg-gradient-to-r from-primary to-primary/80 hover:from-indigo-500 hover:to-violet-500 text-foreground font-semibold rounded-xl transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] shadow-xl shadow-indigo-500/25 flex items-center justify-center gap-2"
            >
              Comenzar gratis
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/pricing"
              className="w-full sm:w-auto py-3.5 px-8 bg-muted/20 border border-border/20 hover:bg-white/10 text-foreground font-semibold rounded-xl transition-all duration-200"
            >
              Ver planes y precios
            </Link>
          </div>

          <div
            className={`mt-8 text-slate-500 text-sm transition-all duration-700 delay-300 ease-out ${
              animIn ? "opacity-100" : "opacity-0"
            }`}
          >
            Sin tarjeta de crédito · Plan gratuito disponible · Cancelas cuando quieras
          </div>
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────── */}
      <section className="relative py-24 sm:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold">
              Todo lo que necesitas en{" "}
              <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
                una sola plataforma
              </span>
            </h2>
            <p className="mt-4 text-muted-foreground text-lg max-w-2xl mx-auto">
              Elimina la fragmentación de 5-8 herramientas separadas. SuccessCore unifica
              todos tus procesos de RRHH con agentes de IA que trabajan 24/7.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map(({ icon: Icon, title, desc }, i) => (
              <div
                key={title}
                className="bg-white/3 border border-white/5 rounded-2xl p-6 hover:bg-muted/20 hover:border-border/20 transition-all duration-300"
              >
                <div className="h-10 w-10 rounded-xl bg-primary/10 border border-indigo-500/20 flex items-center justify-center mb-4">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="text-foreground font-semibold text-lg mb-2">{title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── MODULES GRID ─────────────────────────────────────────── */}
      <section className="relative py-24 sm:py-32 bg-white/[0.02]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold">
              28 módulos integrados
            </h2>
            <p className="mt-4 text-muted-foreground text-lg max-w-2xl mx-auto">
              Desde la gestión básica de empleados hasta analítica avanzada con IA.
              Todos los módulos se comunican entre sí a través de los agentes.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {modules.map(({ name, desc }) => (
              <div
                key={name}
                className="bg-white/3 border border-white/5 rounded-xl p-4 hover:bg-muted/20 transition-colors"
              >
                <Check className="h-4 w-4 text-primary mb-2" />
                <p className="text-foreground text-sm font-medium">{name}</p>
                <p className="text-slate-500 text-xs mt-1">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PRICING PREVIEW ──────────────────────────────────────── */}
      <section className="relative py-24 sm:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold">
              Planes que escalan contigo
            </h2>
            <p className="mt-4 text-muted-foreground text-lg max-w-2xl mx-auto">
              Desde startups hasta enterprise. Todos los planes incluyen acceso
              a agentes de IA.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className={`relative rounded-2xl p-6 border transition-all duration-300 ${
                  plan.highlighted
                    ? "bg-gradient-to-b from-indigo-600/10 to-violet-600/5 border-indigo-500/30 shadow-xl shadow-indigo-500/10 scale-[1.02]"
                    : "bg-white/3 border-white/5 hover:border-border/20"
                }`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-indigo-500 to-violet-500 text-foreground text-xs font-bold px-3 py-1 rounded-full">
                    Más popular
                  </div>
                )}
                <h3 className="text-foreground font-bold text-lg mb-1">{plan.name}</h3>
                <div className="mb-2">
                  <span className="text-3xl font-bold text-foreground">{plan.price}</span>
                  <span className="text-muted-foreground text-sm">{plan.period}</span>
                </div>
                <p className="text-muted-foreground text-sm mb-6">{plan.description}</p>
                <ul className="space-y-2.5 mb-8">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-primary/80">
                      <Check className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/login"
                  className={`block text-center py-2.5 px-4 rounded-xl font-semibold text-sm transition-all duration-200 ${
                    plan.highlighted
                      ? "bg-gradient-to-r from-primary to-primary/80 hover:from-indigo-500 hover:to-violet-500 text-foreground"
                      : "bg-muted/20 border border-border/20 hover:bg-white/10 text-foreground"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>

          <div className="text-center mt-10">
            <Link
              href="/pricing"
              className="text-primary hover:text-indigo-300 text-sm font-medium inline-flex items-center gap-1 transition-colors"
            >
              Ver comparativa completa de planes
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────── */}
      <section className="relative py-24 sm:py-32 bg-white/[0.02]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            ¿Listo para transformar tu departamento de RRHH?
          </h2>
          <p className="text-muted-foreground text-lg mb-10 max-w-2xl mx-auto">
            Únete a las empresas que ya confían en SuccessCore para automatizar sus
            procesos de RRHH con inteligencia artificial.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/login"
              className="w-full sm:w-auto py-3.5 px-10 bg-gradient-to-r from-primary to-primary/80 hover:from-indigo-500 hover:to-violet-500 text-foreground font-semibold rounded-xl transition-all duration-200 hover:scale-[1.02] shadow-xl shadow-indigo-500/25 flex items-center justify-center gap-2"
            >
              Empezar ahora
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/pricing"
              className="w-full sm:w-auto py-3.5 px-8 text-primary/80 hover:text-foreground font-medium transition-colors"
            >
              Hablar con ventas
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              <span className="text-muted-foreground text-sm">SuccessCore HR © 2026</span>
            </div>
            <div className="flex items-center gap-6">
              <span className="text-muted-foreground/60 text-sm cursor-pointer hover:text-muted-foreground transition-colors">
                Términos de servicio
              </span>
              <span className="text-muted-foreground/60 text-sm cursor-pointer hover:text-muted-foreground transition-colors">
                Política de privacidad
              </span>
              <span className="text-muted-foreground/60 text-sm cursor-pointer hover:text-muted-foreground transition-colors">
                Contacto
              </span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
