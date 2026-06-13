"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CreditCard, DollarSign, Sparkles, TrendingUp, AlertTriangle,
  Key, Zap, Server, Clock, CheckCircle2, Lock, Eye, EyeOff,
  Loader2, Shield, Download, ExternalLink, RefreshCw
} from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";

export function BillingDashboard() {
  const queryClient = useQueryClient();
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [customKey, setCustomKey] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["billing-settings"],
    queryFn: () => fetchClient("/billing/settings").then(r => r),
  });

  const { data: quota } = useQuery({
    queryKey: ["quota-status"],
    queryFn: () => fetchClient("/billing/quotas").then(r => r),
  });

  const saveKeyMutation = useMutation({
    mutationFn: ({ provider, key }: { provider: string; key: string }) =>
      fetchClient("/billing/settings", {
        method: "PATCH",
        body: JSON.stringify({ [provider]: key }),
      }).then(r => r),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing-settings"] });
      setSelectedProvider(null);
      setCustomKey("");
      toast.success("API Key guardada");
    },
    onError: () => toast.error("Error al guardar la clave"),
  });

  const toggleKey = (provider: string) => {
    setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }));
  };

  const openKeyModal = (provider: string) => {
    setSelectedProvider(provider);
    setCustomKey("");
  };

  const providers = [
    { key: "customOpenAiKey", name: "OpenAI", color: "from-emerald-500/20 to-green-500/20 border-emerald-500/30", short: "openai" },
    { key: "customGeminiKey", name: "Google Gemini", color: "from-blue-500/20 to-cyan-500/20 border-blue-500/30", short: "gemini" },
    { key: "customAnthropicKey", name: "Anthropic Claude", color: "from-orange-500/20 to-amber-500/20 border-orange-500/30", short: "anthropic" },
    { key: "customGroqKey", name: "Groq", color: "from-purple-500/20 to-violet-500/20 border-purple-500/30", short: "groq" },
    { key: "customOpenRouterKey", name: "OpenRouter", color: "from-rose-500/20 to-pink-500/20 border-rose-500/30", short: "openrouter" },
    { key: "customGrokKey", name: "Grok (xAI)", color: "from-slate-500/20 to-zinc-500/20 border-slate-500/30", short: "grok" },
  ];

  const usageLimit = quota?.quotas?.agent_runs?.limit || 1000;
  const usageCurrent = quota?.quotas?.agent_runs?.used || 0;
  const usagePct = usageLimit > 0 ? Math.min((usageCurrent / usageLimit) * 100, 100) : 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Créditos Disponibles</CardTitle>
            <Sparkles className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{usageLimit.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">Límite mensual de agent runs</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Consumo Mensual</CardTitle>
            <Zap className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{usageCurrent.toLocaleString()}</div>
            <div className="flex items-center gap-2 mt-2">
              <Progress value={usagePct} className={`h-1.5 flex-1 ${usagePct > 80 ? "[&>div]:bg-rose-500" : ""}`} />
              <span className="text-[10px] font-bold text-muted-foreground">{usagePct.toFixed(0)}%</span>
            </div>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Plan Actual</CardTitle>
            <Shield className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{settings?.tier || "Growth"}</div>
            <p className="text-xs text-muted-foreground mt-1">{settings?.tier === "enterprise" ? "Agentes ilimitados" : "Hasta 15 agentes"}</p>
          </CardContent>
        </Card>
      </div>

      {/* BYOK Configuration */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Key className="h-5 w-5 text-amber-500" />
            Bring Your Own Keys (BYOK)
          </CardTitle>
          <CardDescription>Configura tus propias API keys de proveedores LLM para mayor control y ahorro</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {providers.map(provider => {
              const existingKey = settings?.[provider.key];
              const isConfigured = existingKey && existingKey.length > 20;
              const isVisible = showKeys[provider.key];

              return (
                <div key={provider.key} className={`p-4 rounded-xl bg-gradient-to-br ${provider.color} border`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-bold">{provider.name}</p>
                    {isConfigured ? (
                      <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Activa
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] text-muted-foreground">No configurada</Badge>
                    )}
                  </div>
                  {isConfigured && (
                    <p className="text-xs font-mono text-muted-foreground mb-2 truncate">
                      {isVisible ? existingKey : existingKey.slice(0, 12) + "••••••••••••••"}
                    </p>
                  )}
                  <div className="flex gap-1">
                    {isConfigured && (
                      <Button size="xs" variant="ghost" className="text-xs" onClick={() => toggleKey(provider.key)}>
                        {isVisible ? <EyeOff className="h-3 w-3 mr-1" /> : <Eye className="h-3 w-3 mr-1" />}
                        {isVisible ? "Ocultar" : "Ver"}
                      </Button>
                    )}
                    <Button size="xs" variant="outline" className="text-xs" onClick={() => openKeyModal(provider.key)}>
                      {isConfigured ? "Cambiar" : "Configurar"}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow cursor-pointer" onClick={() => toast.info("Stripe portal abriendo...")}>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Portal de Facturación</CardTitle>
            <ExternalLink className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Gestiona tu plan, facturas y métodos de pago vía Stripe</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow cursor-pointer" onClick={() => { queryClient.invalidateQueries({ queryKey: ["quota-status"] }); toast.success("Datos actualizados"); }}>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Actualizar Estadísticas</CardTitle>
            <RefreshCw className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Recarga los datos de consumo y cuotas en tiempo real</p>
          </CardContent>
        </Card>
      </div>

      {/* Key Modal */}
      {selectedProvider && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedProvider(null)}>
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold flex items-center gap-2">
              <Lock className="h-5 w-5 text-amber-500" />
              Configurar {providers.find(p => p.key === selectedProvider)?.name}
            </h3>
            <p className="text-sm text-muted-foreground">Tu clave se almacena cifrada y nunca se comparte con terceros.</p>
            <div className="space-y-2">
              <Label className="text-xs font-bold uppercase tracking-wider">API Key</Label>
              <Input
                type="password"
                placeholder="sk-..."
                value={customKey}
                onChange={e => setCustomKey(e.target.value)}
                className="font-mono text-sm bg-card/60"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setSelectedProvider(null)}>Cancelar</Button>
              <Button onClick={() => saveKeyMutation.mutate({ provider: selectedProvider, key: customKey })} disabled={!customKey.trim() || saveKeyMutation.isPending}>
                {saveKeyMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Guardar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
