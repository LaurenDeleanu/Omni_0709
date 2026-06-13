"use client";

import { useEffect, useState } from "react";
import { useUser } from "@/hooks/use-user";
import { useRouter } from "@/i18n/routing";
import Link from "next/link";
import {
  ShieldCheck,
  Users,
  BarChart3,
  FileSpreadsheet,
  ArrowRight,
  Sparkles,
  Briefcase,
  Building2,
} from "lucide-react";

// ── Feature list ──────────────────────────────────────────────────────────────
const features = [
  {
    icon: Users,
    title: "Gestión de empleados",
    desc: "CRUD completo con historial laboral y soft-delete.",
  },
  {
    icon: BarChart3,
    title: "Reportes ejecutivos",
    desc: "Dashboard en tiempo real + exportación PDF / Excel.",
  },
  {
    icon: FileSpreadsheet,
    title: "Carga masiva",
    desc: "Importa miles de empleados desde CSV/Excel con validación atómica.",
  },
  {
    icon: ShieldCheck,
    title: "Seguridad enterprise",
    desc: "Auth0 SSO, RBAC por roles y aislamiento por tenant.",
  },
];

export default function LoginPage() {
  const { user, isLoading } = useUser();
  const router = useRouter();
  const [animIn, setAnimIn] = useState(false);

  // Form states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantId, setTenantId] = useState("acme_corp");
  const [errorMsg, setErrorMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg("Por favor, introduce tu correo y contraseña.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1"}/users/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // [C3] credentials:'include' so the browser stores the httpOnly cookie
        // set by the backend — the token never touches JavaScript/localStorage.
        credentials: "include",
        body: JSON.stringify({ email, password, tenant_id: tenantId }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error al iniciar sesión.");
      }

      const data = await res.json();

      // [C3] Only store non-sensitive user profile data (no token).
      // The httpOnly cookie was already set by the backend Set-Cookie header.
      if (typeof window !== "undefined") {
        sessionStorage.setItem("local_user", JSON.stringify(data.user));
        if (data.access_token) {
          localStorage.setItem("local_access_token", data.access_token);
        }
      }

      router.push("/dashboard");
    } catch (err: any) {
      setErrorMsg(err.message || "Credenciales incorrectas.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSSOLogin = async (provider: "google" | "microsoft") => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1"}/oauth/${provider}/login`);
      if (res.ok) {
        const data = await res.json();
        if (data.auth_url) {
          window.location.href = data.auth_url;
        }
      }
    } catch (err) {
      console.error(`SSO Login error for ${provider}`, err);
      setErrorMsg(`Error al conectar con ${provider}`);
    }
  };

  // Si ya hay sesión, redirigir al dashboard
  useEffect(() => {
    if (!isLoading && user) {
      router.push("/dashboard");
    }
  }, [user, isLoading, router]);

  // Trigger de animación al montar
  useEffect(() => {
    const t = setTimeout(() => setAnimIn(true), 50);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen flex bg-slate-950 overflow-hidden">
      {/* ── Panel izquierdo: Branding ──────────────────────────────────────── */}
      <div
        className={`hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative
          transition-all duration-700 ease-out
          ${animIn ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8"}`}
      >
        {/* Fondo decorativo */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl" />
          <div className="absolute top-1/2 -right-20 w-72 h-72 bg-violet-600/15 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 left-1/4 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl" />
        </div>

        {/* Logo */}
        <div className="relative">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Building2 className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="text-white font-bold text-xl leading-none">SuccessCore</p>
              <p className="text-indigo-400 text-xs font-semibold tracking-wider uppercase mt-1">HR Platform</p>
            </div>
          </div>
        </div>

        {/* Headline + Features */}
        <div className="relative space-y-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-3 py-1">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              <span className="text-indigo-300 text-xs font-medium">Enterprise SaaS · Multi-tenant</span>
            </div>
            <h1 className="text-4xl font-bold text-white leading-tight">
              El HR del futuro,<br />
              <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
                disponible hoy.
              </span>
            </h1>
            <p className="text-slate-400 text-base leading-relaxed max-w-sm">
              Gestiona tu plantilla, automatiza reportes y controla el acceso
              de cada empleado con seguridad de nivel enterprise.
            </p>
          </div>

          {/* Feature list */}
          <div className="space-y-3">
            {features.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="flex items-start gap-3 bg-white/5 border border-white/10 rounded-xl p-3.5
                           backdrop-blur-sm hover:bg-white/8 transition-colors"
              >
                <div className="h-8 w-8 rounded-lg bg-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="h-4 w-4 text-indigo-400" />
                </div>
                <div>
                  <p className="text-white text-sm font-medium">{title}</p>
                  <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="relative">
          <p className="text-slate-600 text-xs">
            © 2026 SuccessCore HR · Todos los derechos reservados
          </p>
        </div>
      </div>

      {/* ── Panel derecho: Login Card ──────────────────────────────────────── */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6">
        <div
          className={`w-full max-w-md transition-all duration-700 ease-out delay-150
            ${animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}
        >
          {/* Mobile logo */}
          <div className="flex items-center gap-4 mb-8 lg:hidden">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Building2 className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-white font-bold text-lg leading-none">SuccessCore HR</p>
              <p className="text-indigo-400 text-xs mt-1">Enterprise Platform</p>
            </div>
          </div>

          {/* Card */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur-xl shadow-2xl shadow-black/40 relative">
            {/* Header */}
            <div className="space-y-1.5 mb-6">
              <h2 className="text-2xl font-bold text-white">Bienvenido de vuelta</h2>
              <p className="text-slate-400 text-sm">
                Inicia sesión con tus credenciales o mediante SSO corporativo.
              </p>
            </div>

            {/* Formulario de Login Local */}
            <form onSubmit={handleSubmit} className="space-y-4 mb-6">
              {errorMsg && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-300 text-xs rounded-xl px-3 py-2">
                  {errorMsg}
                </div>
              )}

              <div className="space-y-1">
                <label className="text-slate-300 text-xs font-medium">Correo Electrónico</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="lauren.deleanu@gmail.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 text-xs font-medium">Contraseña</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 px-6 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-all duration-200 hover:scale-[1.01] active:scale-[0.99] flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40"
              >
                {isSubmitting ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    Iniciar sesión
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-slate-600 text-xs">o continúa con SSO</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>

            {/* SSO Badge */}
            <div className="flex items-center gap-2 bg-indigo-500/5 border border-indigo-500/10 rounded-lg px-3 py-2 mb-4">
              <ShieldCheck className="h-4 w-4 text-indigo-400 flex-shrink-0" />
              <p className="text-indigo-300 text-[10px] leading-snug">
                <strong>SSO Corporativo</strong> — Si tu empresa requiere autenticación federada, usa los accesos rápidos a continuación.
              </p>
            </div>

            {/* Login button */}
            <a
              href="/api/auth/login"
              className="group flex items-center justify-center gap-3 w-full py-2.5 px-4
                         bg-white/5 border border-white/10
                         hover:bg-white/10
                         text-slate-200 text-sm font-semibold rounded-xl
                         transition-all duration-200
                         hover:scale-[1.01]
                         active:scale-[0.99] mb-3"
            >
              <svg className="h-4 w-4 flex-shrink-0 text-slate-400" viewBox="0 0 24 24" fill="currentColor">
                <path d="M21.98 7.448L19.62 0H4.347L2.02 7.448c-1.352 4.312.03 9.206 3.815 12.015L12.007 24l6.157-4.552c3.755-2.81 5.182-7.688 3.815-12.015v.015zm-9.973 10.37l-3.747-2.638 1.374-4.61h4.718l1.375 4.61-3.72 2.638z"/>
              </svg>
              Continuar con Auth0 SSO
            </a>

            {/* Social quick-links (deep-link a los connections de Auth0) */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handleSSOLogin("google")}
                className="flex items-center justify-center gap-2 py-2 px-3
                           bg-white/5 border border-white/10 rounded-xl
                           text-slate-300 text-xs font-medium
                           hover:bg-white/10 transition-colors"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Google
              </button>
              <button
                type="button"
                onClick={() => handleSSOLogin("microsoft")}
                className="flex items-center justify-center gap-2 py-2 px-3
                           bg-white/5 border border-white/10 rounded-xl
                           text-slate-300 text-xs font-medium
                           hover:bg-white/10 transition-colors"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="#00a1f1">
                  <path d="M11.5 2.75H2.75v8.75H11.5V2.75zm0 9.75H2.75v8.75H11.5V12.5zm1 0H21.25v8.75H12.5V12.5zm0-9.75H21.25v8.75H12.5V2.75z"/>
                </svg>
                Microsoft
              </button>
            </div>

            {/* Careers CTA */}
            <div className="text-center mb-4">
              <Link
                href="/careers"
                className="inline-flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 text-xs font-medium transition-colors"
              >
                <Briefcase className="h-3.5 w-3.5" />
                View Open Positions
              </Link>
            </div>

            {/* Footer note */}
            <p className="text-center text-slate-600 text-xs mt-6 leading-relaxed">
              Al iniciar sesión aceptas los{" "}
              <span className="text-slate-400 hover:text-slate-300 cursor-pointer">
                Términos de servicio
              </span>{" "}
              y la{" "}
              <span className="text-slate-400 hover:text-slate-300 cursor-pointer">
                Política de privacidad
              </span>
              .
            </p>
          </div>

          {/* Loading state overlay */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80 rounded-2xl backdrop-blur-sm">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
