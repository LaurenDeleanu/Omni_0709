"use client";

import { useState, useEffect } from "react";
import { Link, useRouter } from "@/i18n/routing";
import { Building2, ArrowRight, Check, X, Loader2, Sparkles, Search } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

const TIERS = [
  { id: "FREE", name: "Free", price: "$0/mo", desc: "Up to 10 employees, basic HR features" },
  { id: "PRO", name: "Pro", price: "$99/mo", desc: "Up to 100 employees, AI agents, full suite" },
  { id: "ENTERPRISE", name: "Enterprise", price: "Custom", desc: "Unlimited, SSO, dedicated support" },
];

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<"form" | "success">("form");
  const [companyName, setCompanyName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [tier, setTier] = useState("FREE");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<any>(null);
  const [checkingName, setCheckingName] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [animIn, setAnimIn] = useState(false);

  useEffect(() => { setAnimIn(true); }, []);

  const checkAvailability = async (name: string) => {
    if (name.length < 2) return;
    setCheckingName(true);
    try {
      const res = await fetch(`${API_BASE}/signup/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include" as RequestCredentials,
      });
      const data = await res.json();
      setValidation(data);
    } catch {
      setValidation(null);
    } finally {
      setCheckingName(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!companyName || !adminName || !adminEmail || !adminPassword) {
      setError("Please fill in all fields.");
      return;
    }
    if (adminPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include" as RequestCredentials,
        body: JSON.stringify({
          company_name: companyName,
          admin_email: adminEmail,
          admin_password: adminPassword,
          admin_name: adminName,
          tier,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Signup failed");
      }
      setResult(data);
      setStep("success");
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (step === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-6">
        <div className={`max-w-md w-full bg-card border border-border rounded-2xl p-8 text-center transition-all duration-500 ${animIn ? "opacity-100 scale-100" : "opacity-0 scale-95"}`}>
          <div className="w-16 h-16 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="h-8 w-8 text-success" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">Workspace Created!</h1>
          <p className="text-muted-foreground text-sm mb-6">
            Your SuccessCore workspace for <strong>{result?.company_name || companyName}</strong> is ready.
          </p>
          {result?.checkout_url && (
            <div className="bg-warning/10 border border-warning/20 rounded-xl p-3 mb-4 text-xs text-warning text-left">
              Complete your payment to activate your {tier} plan. Redirecting...
            </div>
          )}
          <button
            onClick={() => router.push("/login")}
            className="w-full py-3 px-6 bg-primary hover:brightness-110 text-primary-foreground font-semibold rounded-xl transition-all"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-background overflow-hidden">
      {/* Left panel — branding */}
      <div className={`hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative transition-all duration-700 ${animIn ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8"}`}>
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -left-40 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
          <div className="absolute top-1/2 -right-20 w-72 h-72 bg-primary/15 rounded-full blur-3xl" />
        </div>
        <div className="relative">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
              <Building2 className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <p className="text-foreground font-bold text-xl">SuccessCore</p>
              <p className="text-primary/80 text-xs font-semibold tracking-wider uppercase mt-1">Get Started</p>
            </div>
          </div>
        </div>
        <div className="relative space-y-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-full px-3 py-1">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span className="text-primary/80 text-xs font-medium">Free forever tier available</span>
            </div>
            <h1 className="text-3xl font-bold text-foreground leading-tight">Launch your HR<br />in 60 seconds.</h1>
            <p className="text-muted-foreground text-sm leading-relaxed max-w-sm">
              One workspace per company. Automatic schema provisioning, roles, and AI agents included.
            </p>
          </div>
        </div>
        <div className="relative">
          <p className="text-muted-foreground/40 text-xs">© 2026 SuccessCore HR</p>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6">
        <div className={`w-full max-w-md transition-all duration-700 delay-150 ${animIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
          <div className="flex items-center gap-4 mb-6 lg:hidden">
            <div className="h-11 w-11 rounded-xl bg-primary flex items-center justify-center">
              <Building2 className="h-5 w-5 text-primary-foreground" />
            </div>
            <p className="text-foreground font-bold text-lg">SuccessCore</p>
          </div>

          <div className="bg-card/80 border border-border rounded-2xl p-8 backdrop-blur-xl shadow-2xl shadow-foreground/5">
            <div className="space-y-1.5 mb-6">
              <h2 className="text-2xl font-bold text-foreground">Create Workspace</h2>
              <p className="text-muted-foreground text-sm">Set up your company in under a minute.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-xl px-3 py-2">{error}</div>
              )}

              <div className="space-y-1">
                <label className="text-foreground/80 text-xs font-medium">Company Name</label>
                <div className="relative">
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => { setCompanyName(e.target.value); checkAvailability(e.target.value); }}
                    placeholder="Acme Corp"
                    className="w-full bg-muted/20 border border-border rounded-xl px-3.5 py-2.5 text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors"
                  />
                  {checkingName && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />}
                  {!checkingName && validation?.company_taken && (
                    <X className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-destructive" />
                  )}
                  {!checkingName && validation && !validation.company_taken && companyName.length >= 2 && (
                    <Check className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-success" />
                  )}
                </div>
                {validation?.suggestions?.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {validation.suggestions.map((s: string) => (
                      <button key={s} type="button" onClick={() => { setCompanyName(s); checkAvailability(s); }}
                        className="text-[10px] px-2 py-0.5 rounded bg-muted hover:bg-muted/80 text-muted-foreground">{s}</button>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-foreground/80 text-xs font-medium">Your Name</label>
                <input type="text" value={adminName} onChange={(e) => setAdminName(e.target.value)}
                  placeholder="Jane Smith" className="w-full bg-muted/20 border border-border rounded-xl px-3.5 py-2.5 text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors" />
              </div>

              <div className="space-y-1">
                <label className="text-foreground/80 text-xs font-medium">Work Email</label>
                <input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)}
                  placeholder="jane@acmecorp.com" className="w-full bg-muted/20 border border-border rounded-xl px-3.5 py-2.5 text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors" />
                {validation?.email_taken && <p className="text-[10px] text-destructive">This email is already registered.</p>}
              </div>

              <div className="space-y-1">
                <label className="text-foreground/80 text-xs font-medium">Password</label>
                <input type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)}
                  placeholder="Min. 8 characters" className="w-full bg-muted/20 border border-border rounded-xl px-3.5 py-2.5 text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors" />
              </div>

              <fieldset className="space-y-1.5">
                <legend className="text-foreground/80 text-xs font-medium">Plan</legend>
                <div className="grid grid-cols-3 gap-2">
                  {TIERS.map((t) => (
                    <button key={t.id} type="button" onClick={() => setTier(t.id)}
                      className={`text-left rounded-xl border p-3 transition-colors ${tier === t.id ? "border-primary bg-primary/5" : "border-border bg-muted/20 hover:bg-muted/30"}`}>
                      <p className="text-xs font-bold text-foreground">{t.name}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">{t.price}</p>
                    </button>
                  ))}
                </div>
              </fieldset>

              <button type="submit" disabled={isSubmitting}
                className="w-full py-3 px-6 bg-primary hover:brightness-110 disabled:opacity-50 text-primary-foreground font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Create Workspace <ArrowRight className="h-4 w-4" /></>}
              </button>
            </form>

            <p className="text-center text-muted-foreground text-xs mt-6">
              Already have an account?{" "}
              <Link href="/login" className="text-primary hover:underline">Sign in</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
