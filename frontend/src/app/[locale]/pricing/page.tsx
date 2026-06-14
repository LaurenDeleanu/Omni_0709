"use client";

import { Link } from "@/i18n/routing";
import { ArrowLeft, Check, Building2, Sparkles } from "lucide-react";
import { useState, useEffect } from "react";

const plans = [
  {
    name: "Gratuito",
    price: "0€",
    period: "para siempre",
    description: "Para equipos pequeños que quieren probar la plataforma.",
    features: [
      "Hasta 50 empleados",
      "1 agente de IA (Copilot básico)",
      "5.000 llamadas API/mes",
      "100 ejecuciones de agente/mes",
      "100 MB almacenamiento",
      "Módulos core HR",
      "Portal del empleado",
      "Soporte por email",
    ],
    cta: "Comenzar gratis",
    highlighted: false,
  },
  {
    name: "Starter",
    price: "6€",
    period: "/empleado/mes",
    description: "Para startups y pymes en crecimiento.",
    features: [
      "Hasta 250 empleados",
      "3 agentes de IA",
      "50.000 llamadas API/mes",
      "500 ejecuciones de agente/mes",
      "1 GB almacenamiento",
      "Todos los módulos core + avanzados",
      "Control horario digital",
      "Integraciones básicas",
      "Soporte por email prioritario",
    ],
    cta: "Prueba 14 días gratis",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "12€",
    period: "/empleado/mes",
    description: "Para empresas que necesitan automatización avanzada con IA.",
    features: [
      "Hasta 1.000 empleados",
      "7 agentes de IA + personalizados",
      "200.000 llamadas API/mes",
      "2.000 ejecuciones de agente/mes",
      "5 GB almacenamiento",
      "Todos los módulos",
      "API pública",
      "Integraciones premium (Slack, DocuSign)",
      "Soporte prioritario 12/5",
      "Onboarding personalizado",
    ],
    cta: "Prueba 14 días gratis",
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
      "Llamadas API ilimitadas",
      "50.000 ejecuciones de agente/mes",
      "50 GB almacenamiento",
      "Agentes personalizados ilimitados",
      "Multi-tenant avanzado",
      "BYOK (Bring Your Own Key)",
      "SLA 99.9% garantizado",
      "Soporte 24/7 dedicado",
      "Integraciones enterprise a medida",
      "Data residency configurable",
    ],
    cta: "Hablar con ventas",
    highlighted: false,
  },
];

const comparisonFeatures = [
  { name: "Empleados máximos", free: "50", starter: "250", pro: "1.000", enterprise: "Ilimitado" },
  { name: "Agentes de IA", free: "1", starter: "3", pro: "7", enterprise: "10 + Omni" },
  { name: "API calls/mes", free: "5.000", starter: "50.000", pro: "200.000", enterprise: "Ilimitadas" },
  { name: "Ejecuciones agente/mes", free: "100", starter: "500", pro: "2.000", enterprise: "50.000" },
  { name: "Almacenamiento", free: "100 MB", starter: "1 GB", pro: "5 GB", enterprise: "50 GB" },
  { name: "Módulos HR", free: "Core", starter: "Todos", pro: "Todos", enterprise: "Todos" },
  { name: "API pública", free: "—", starter: "—", pro: "✓", enterprise: "✓" },
  { name: "Agentes personalizados", free: "—", starter: "—", pro: "✓", enterprise: "✓" },
  { name: "BYOK", free: "—", starter: "—", pro: "—", enterprise: "✓" },
  { name: "SLA", free: "—", starter: "—", pro: "99.5%", enterprise: "99.9%" },
  { name: "Soporte", free: "Email", starter: "Email prioritario", pro: "12/5", enterprise: "24/7 dedicado" },
  { name: "Onboarding", free: "Self-service", starter: "Guías", pro: "Personalizado", enterprise: "Dedicado" },
];

export default function PricingPage() {
  const [animIn, setAnimIn] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setAnimIn(true), 50);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ── NAV ──────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                <Building2 className="h-5 w-5 text-foreground" />
              </div>
              <span className="text-foreground font-bold text-lg">SuccessCore</span>
            </Link>
            <Link
              href="/login"
              className="py-2 px-4 bg-indigo-600 hover:bg-indigo-500 text-foreground text-sm font-semibold rounded-lg transition-colors"
            >
              Probar gratis
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HEADER ───────────────────────────────────────────────── */}
      <section className="relative pt-20 pb-12 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-[500px] h-[500px] bg-indigo-600/8 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div
            className={`transition-all duration-700 ease-out ${
              animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 mb-6">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              <span className="text-indigo-300 text-sm font-medium">Planes y precios</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold mb-4">
              Planes que escalan{" "}
              <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
                con tu empresa
              </span>
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              Todos los planes incluyen acceso a agentes de IA. Sin costes ocultos.
              Cambia de plan en cualquier momento.
            </p>
          </div>
        </div>
      </section>

      {/* ── PRICING CARDS ────────────────────────────────────────── */}
      <section className="py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`relative rounded-2xl p-6 border transition-all duration-300 ${
                  plan.highlighted
                    ? "bg-gradient-to-b from-indigo-600/10 to-violet-600/5 border-indigo-500/30 shadow-xl shadow-indigo-500/10 lg:scale-[1.02] scale-[1.02] md:scale-100"
                    : "bg-white/3 border-white/5 hover:border-white/10"
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
                  <span className="text-slate-400 text-sm"> {plan.period}</span>
                </div>
                <p className="text-slate-400 text-sm mb-6 leading-relaxed">{plan.description}</p>
                <ul className="space-y-2.5 mb-8">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
                      <Check className="h-4 w-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.cta.includes("ventas") ? "/login" : "/login"}
                  className={`block text-center py-2.5 px-4 rounded-xl font-semibold text-sm transition-all duration-200 ${
                    plan.highlighted
                      ? "bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-foreground shadow-lg shadow-indigo-500/25"
                      : "bg-white/5 border border-white/10 hover:bg-white/10 text-foreground"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── COMPARISON TABLE ─────────────────────────────────────── */}
      <section className="py-20 sm:py-28">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center mb-12">
            Comparativa detallada de planes
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-4 px-4 text-slate-400 font-medium">Funcionalidad</th>
                  <th className="py-4 px-4 text-foreground font-semibold text-center">Gratuito</th>
                  <th className="py-4 px-4 text-foreground font-semibold text-center">Starter</th>
                  <th className="py-4 px-4 text-foreground font-semibold text-center bg-indigo-500/5">Pro</th>
                  <th className="py-4 px-4 text-foreground font-semibold text-center">Enterprise</th>
                </tr>
              </thead>
              <tbody>
                {comparisonFeatures.map((row, i) => (
                  <tr key={row.name} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="py-3 px-4 text-slate-300">{row.name}</td>
                    <td className="py-3 px-4 text-slate-400 text-center">{row.free}</td>
                    <td className="py-3 px-4 text-slate-400 text-center">{row.starter}</td>
                    <td className="py-3 px-4 text-indigo-300 text-center bg-indigo-500/[0.03]">{row.pro}</td>
                    <td className="py-3 px-4 text-slate-400 text-center">{row.enterprise}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────────────── */}
      <section className="py-20 sm:py-28 bg-white/[0.02]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center mb-12">
            Preguntas frecuentes
          </h2>
          <div className="space-y-6">
            {[
              {
                q: "¿Puedo cambiar de plan en cualquier momento?",
                a: "Sí. Puedes subir o bajar de plan cuando quieras. Si subes, se aplica la diferencia prorrateada. Si bajas, el cambio se aplica al siguiente ciclo de facturación.",
              },
              {
                q: "¿Qué son los agentes de IA y cómo funcionan?",
                a: "Los agentes de IA son asistentes especializados que operan sobre los datos reales de tu plataforma. Por ejemplo, el Payroll Specialist puede procesar nóminas, el IT Helpdesk gestiona tickets de soporte, y el Recruiter Pro analiza candidatos. Cada agente tiene permisos RBAC y solo accede a los datos que le corresponden.",
              },
              {
                q: "¿Mis datos están seguros?",
                a: "Absolutamente. Usamos encriptación AES-256, aislamiento por tenant, Auth0 SSO, y cumplimos con GDPR. Con el plan Enterprise puedes usar tus propias claves de API (BYOK) para los proveedores de IA.",
              },
              {
                q: "¿Hay un período de prueba?",
                a: "Sí. Los planes Starter y Pro incluyen 14 días de prueba gratuita sin compromiso. El plan Gratuito es para siempre, sin límite de tiempo.",
              },
              {
                q: "¿Ofrecen soporte para la legislación española?",
                a: "Sí. SuccessCore está diseñado específicamente para cumplir con la legislación laboral española: registro horario digital (RDL 8/2019), FUNDAE para formación bonificada, Estatuto de los Trabajadores, y GDPR.",
              },
              {
                q: "¿Puedo integrar SuccessCore con otras herramientas?",
                a: "Sí. Ofrecemos integraciones nativas con Slack, DocuSign, y una API pública completa. El plan Enterprise incluye integraciones personalizadas a medida.",
              },
            ].map(({ q, a }) => (
              <div key={q} className="bg-white/3 border border-white/5 rounded-xl p-5">
                <h3 className="text-foreground font-semibold mb-2">{q}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────── */}
      <section className="py-20 text-center">
        <div className="max-w-2xl mx-auto px-4">
          <h2 className="text-3xl font-bold mb-4">¿Listo para empezar?</h2>
          <p className="text-slate-400 text-lg mb-8">
            Comienza con el plan Gratuito y escala cuando lo necesites.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/login"
              className="w-full sm:w-auto py-3.5 px-10 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-foreground font-semibold rounded-xl transition-all duration-200 shadow-xl shadow-indigo-500/25 flex items-center justify-center gap-2"
            >
              Comenzar gratis
              <Sparkles className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-slate-600 text-sm">SuccessCore HR © 2026 · Todos los derechos reservados</p>
        </div>
      </footer>
    </div>
  );
}
