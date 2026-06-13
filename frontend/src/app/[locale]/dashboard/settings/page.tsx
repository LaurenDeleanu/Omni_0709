"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { TenantAPI, AdminAPI, TenantSettings, fetchClient } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Loader2, Save, UploadCloud, Building2, Palette, Component, ShieldCheck, CreditCard, Key, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import RolesTab from "./roles-tab";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("general");
  const [name, setName] = useState("");
  const [color, setColor] = useState("#3b82f6");

  // Billing & BYOK states
  const [billingSettings, setBillingSettings] = useState<any>(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [keysState, setKeysState] = useState<any>({
    customOpenAiKey: "",
    customGeminiKey: "",
    customOpenRouterKey: "",
    customAnthropicKey: "",
    customGrokKey: "",
    customGroqKey: ""
  });

  const loadBillingSettings = async () => {
    setBillingLoading(true);
    try {
      const data = await fetchClient("/billing/settings");
      setBillingSettings(data);
      setKeysState({
        customOpenAiKey: data.customOpenAiKey || "",
        customGeminiKey: data.customGeminiKey || "",
        customOpenRouterKey: data.customOpenRouterKey || "",
        customAnthropicKey: data.customAnthropicKey || "",
        customGrokKey: data.customGrokKey || "",
        customGroqKey: data.customGroqKey || ""
      });
    } catch (err) {
      toast.error("Error al cargar facturación");
    } finally {
      setBillingLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "billing") {
      loadBillingSettings();
    }
  }, [activeTab]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("debt") === "paid") {
        toast.success("¡Pago exitoso!", { description: "Tu saldo deudor ha sido liquidado correctamente." });
        window.history.replaceState({}, document.title, window.location.pathname);
      } else if (params.get("upgrade") === "success") {
        const t = params.get("tier");
        toast.success(`¡Suscripción actualizada!`, { description: `Tu organización ha sido actualizada al plan ${t} con éxito.` });
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
  }, []);

  const handleCheckout = async (action: string, tier?: string) => {
    try {
      const res = await fetchClient("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({
          action,
          tier
        })
      });
      if (res && res.url) {
        toast.success("Redirigiendo a la pasarela de pago...");
        window.location.href = res.url;
      } else {
        toast.error("Error al iniciar checkout");
      }
    } catch (err) {
      toast.error("Error al procesar el pago");
    }
  };

  const { data: settings, isLoading } = useQuery({
    queryKey: ["tenantSettings"],
    queryFn: async () => {
      const data = await TenantAPI.getSettings();
      setName(data.name || "");
      setColor(data.primary_color || "#3b82f6");
      return data;
    },
  });

  const updateSettingsMutation = useMutation({
    mutationFn: (data: Partial<TenantSettings>) => TenantAPI.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenantSettings"] });
      toast.success("Configuración guardada", { description: "Los cambios se han aplicado correctamente." });
      
      // Forzar recarga visual si cambia el color
      setTimeout(() => window.location.reload(), 1000);
    },
    onError: () => {
      toast.error("Error", { description: "No se pudo guardar la configuración." });
    }
  });

  const uploadLogoMutation = useMutation({
    mutationFn: (file: File) => TenantAPI.uploadLogo(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenantSettings"] });
      toast.success("Logo actualizado", { description: "El logo se ha subido con éxito." });
    },
    onError: () => {
      toast.error("Error al subir", { description: "Asegúrate de que es una imagen válida." });
    }
  });

  const TABS = [
    { id: "general", name: "Organización General", icon: Building2 },
    { id: "appearance", name: "Apariencia y Colores", icon: Palette },
    { id: "modules", name: "Módulos y Ecosistema", icon: Component },
    { id: "roles", name: "Roles y Permisos", icon: ShieldCheck },
    { id: "billing", name: "Facturación & API Keys", icon: CreditCard }
  ];

  const { data: modulesData, isLoading: modulesLoading } = useQuery({
    queryKey: ["tenantModules"],
    queryFn: () => AdminAPI.getModules(),
    enabled: activeTab === "modules"
  });

  const toggleModulesMutation = useMutation({
    mutationFn: (enabled_modules: Record<string, boolean>) => AdminAPI.toggleModules({ enabled_modules }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenantModules"] });
      toast.success("Módulos actualizados", { description: "Los cambios requieren recargar la página." });
      setTimeout(() => window.location.reload(), 1500);
    }
  });

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Ajustes Globales (Super Admin)</h1>
        <p className="text-muted-foreground mt-2 text-sm md:text-base">
          Gestiona la configuración general, apariencia, y el ecosistema de módulos activos.
        </p>
      </div>

      {/* PREMIUM HORIZONTAL TABS CONTROLLER */}
      <div className="flex border-b border-border/50 gap-6 overflow-x-auto pb-px scrollbar-none">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 pb-4 px-1 text-sm font-semibold border-b-2 transition-all duration-200 whitespace-nowrap cursor-pointer ${
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground/80"
              }`}
            >
              <tab.icon className={`w-4.5 h-4.5 transition-colors ${isActive ? "text-primary" : "text-muted-foreground"}`} />
              {tab.name}
            </button>
          );
        })}
      </div>

      <div className="mt-6">
        {/* TAB GENERAL */}
        {activeTab === "general" && (
          <Card className="border border-border/60 bg-card/25 backdrop-blur-md shadow-md">
            <CardHeader>
              <CardTitle className="text-lg font-bold flex gap-2 items-center"><Building2 className="w-5 h-5 text-primary" /> Información de la Organización</CardTitle>
              <CardDescription>
                Actualiza el nombre y otros detalles de tu empresa.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="companyName" className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Nombre de la Empresa</Label>
                <Input
                  id="companyName"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Acme Corp"
                  className="bg-card/60"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-bold text-foreground/80 uppercase tracking-wider">ID de Entorno (Schema)</Label>
                <Input
                  disabled
                  value={settings?.schema_name}
                  className="bg-muted/40 text-muted-foreground border-border/60 cursor-not-allowed select-all"
                />
                <p className="text-xs text-muted-foreground">
                  Este es tu identificador único de base de datos. No se puede cambiar.
                </p>
              </div>

              <Button
                onClick={() => updateSettingsMutation.mutate({ name })}
                disabled={updateSettingsMutation.isPending}
                className="bg-primary hover:bg-primary/95 text-white transition-colors cursor-pointer"
              >
                {updateSettingsMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Save className="w-4 h-4 mr-2" />
                Guardar Cambios
              </Button>
            </CardContent>
          </Card>
        )}

        {/* TAB APARIENCIA */}
        {activeTab === "appearance" && (
          <div className="grid gap-6 md:grid-cols-2">
            
            <Card className="border border-border/60 bg-card/25 backdrop-blur-md shadow-md">
              <CardHeader>
                <CardTitle className="text-lg font-bold flex gap-2 items-center"><Palette className="w-5 h-5 text-primary" /> Color de Marca</CardTitle>
                <CardDescription>
                  Personaliza el color principal de los botones y elementos destacados.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center space-x-4">
                  <div className="relative">
                    <input
                      type="color"
                      value={color}
                      onChange={(e) => setColor(e.target.value)}
                      className="h-14 w-14 rounded-md border-0 p-1 cursor-pointer bg-transparent"
                    />
                  </div>
                  <div className="flex-1 space-y-1">
                    <Label className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Código HEX</Label>
                    <Input
                      value={color}
                      onChange={(e) => setColor(e.target.value)}
                      placeholder="#3b82f6"
                      className="font-mono uppercase bg-card/60"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-border/60">
                  <Label className="mb-3 block text-xs font-bold text-foreground/80 uppercase tracking-wider">Vista Previa</Label>
                  <div className="flex gap-2.5">
                    <Button style={{ backgroundColor: color, color: '#fff' }} className="shadow-sm">Botón Principal</Button>
                    <Button variant="outline" style={{ borderColor: color, color: color }} className="hover:bg-muted/10">Secundario</Button>
                  </div>
                </div>

                <Button
                  onClick={() => updateSettingsMutation.mutate({ primary_color: color })}
                  disabled={updateSettingsMutation.isPending}
                  className="w-full bg-primary hover:bg-primary/95 text-white transition-colors cursor-pointer"
                >
                  {updateSettingsMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Aplicar Color
                </Button>
              </CardContent>
            </Card>

            <Card className="border border-border/60 bg-card/25 backdrop-blur-md shadow-md">
              <CardHeader>
                <CardTitle className="text-lg font-bold flex gap-2 items-center"><UploadCloud className="w-5 h-5 text-primary animate-bounce" /> Logo Corporativo</CardTitle>
                <CardDescription>
                  Sube tu logo para mostrarlo en el menú de navegación lateral.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex justify-center border-2 border-dashed border-border rounded-lg p-6 bg-accent/20 shadow-inner">
                  {settings?.logo_url ? (
                    <img 
                      src={settings.logo_url} 
                      alt="Logo actual" 
                      className="max-h-[100px] object-contain drop-shadow-sm transition-transform hover:scale-105"
                    />
                  ) : (
                    <div className="text-center text-muted-foreground flex flex-col items-center">
                      <UploadCloud className="w-10 h-10 mb-2 opacity-50" />
                      <span className="text-sm">Sin logo configurado</span>
                    </div>
                  )}
                </div>

                <div className="space-y-2.5">
                  <Label htmlFor="logoFile" className="text-xs font-bold text-foreground/80 uppercase tracking-wider">Seleccionar archivo</Label>
                  <Input 
                    id="logoFile" 
                    type="file" 
                    accept="image/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        uploadLogoMutation.mutate(file);
                      }
                    }}
                    className="bg-card/60 cursor-pointer"
                  />
                  <p className="text-xs text-muted-foreground">Recomendado: PNG o SVG transparente, max 2MB.</p>
                </div>
                
                {uploadLogoMutation.isPending && (
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin text-primary" /> Subiendo...
                  </div>
                )}
              </CardContent>
            </Card>

          </div>
        )}

        {/* TAB MODULES (ECOSYSTEM) */}
        {activeTab === "modules" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center bg-card/40 p-4 rounded-xl border border-border/50">
              <div>
                <h3 className="font-bold text-lg text-foreground">Marketplace de Módulos</h3>
                <p className="text-sm text-muted-foreground">Activa o desactiva pilares enteros de la plataforma.</p>
              </div>
              <Button
                onClick={() => {
                  if (modulesData?.enabled_modules) {
                    toggleModulesMutation.mutate(modulesData.enabled_modules);
                  }
                }}
                disabled={toggleModulesMutation.isPending}
                className="bg-primary hover:bg-primary/95 text-white"
              >
                {toggleModulesMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Save className="w-4 h-4 mr-2" /> Guardar Ecosistema
              </Button>
            </div>

            {modulesLoading ? (
              <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                  { id: "people", name: "People & HR", desc: "Gestión de empleados, organigrama y ausencias.", color: "bg-blue-500/10 text-blue-500" },
                  { id: "finance", name: "Finance & OCR", desc: "Control de gastos, tickets y pre-nóminas.", color: "bg-emerald-500/10 text-emerald-500" },
                  { id: "it", name: "IT & Devices", desc: "Inventario de equipos, licencias y ticketing.", color: "bg-cyan-500/10 text-cyan-500" },
                  { id: "training", name: "Academy & LMS", desc: "Cursos SCORM y cumplimiento FUNDAE.", color: "bg-indigo-500/10 text-indigo-500" },
                  { id: "hire", name: "ATS & Recruiting", desc: "Portal de empleo, pipeline y ofertas.", color: "bg-orange-500/10 text-orange-500" },
                  { id: "work", name: "Project Management", desc: "Kanban, horas facturables y Wiki.", color: "bg-purple-500/10 text-purple-500" },
                  { id: "sales", name: "CRM & Sales", desc: "Pipeline de ventas, clientes y presupuestos.", color: "bg-pink-500/10 text-pink-500" },
                ].map(mod => {
                  const isEnabled = modulesData?.enabled_modules?.[mod.id] ?? false;
                  return (
                    <Card key={mod.id} className={`border transition-all ${isEnabled ? "border-primary/50 shadow-sm bg-card/60" : "border-border/40 opacity-70 bg-card/20"}`}>
                      <CardHeader className="pb-4">
                        <div className="flex justify-between items-start">
                          <div className={`p-2.5 rounded-lg ${mod.color}`}>
                            <Component className="w-5 h-5" />
                          </div>
                          <Switch 
                            checked={isEnabled} 
                            onCheckedChange={(checked: boolean) => {
                               if (modulesData) {
                                 modulesData.enabled_modules[mod.id] = checked;
                                 queryClient.setQueryData(["tenantModules"], { ...modulesData });
                               }
                            }}
                          />
                        </div>
                        <CardTitle className="mt-4 text-lg">{mod.name}</CardTitle>
                        <CardDescription className="text-xs">{mod.desc}</CardDescription>
                      </CardHeader>
                    </Card>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB ROLES (RBAC) */}
        {activeTab === "roles" && (
          <RolesTab />
        )}

        {/* TAB BILLING & BYOK */}
        {activeTab === "billing" && (
          <div className="space-y-8 animate-fade-in text-white">
            {/* Resumen de Facturación & Saldo */}
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="border border-border/60 bg-card/25 backdrop-blur-md shadow-md relative overflow-hidden group hover:border-primary/30 transition-all duration-300">
                <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-bl-full pointer-events-none transition-transform group-hover:scale-110" />
                <CardHeader>
                  <CardTitle className="text-lg font-bold flex gap-2 items-center text-white">
                    <CreditCard className="w-5 h-5 text-primary" /> Facturación de IA Reseller
                  </CardTitle>
                  <CardDescription className="text-zinc-400">
                    Monitorea tus gastos acumulados y suscripción actual.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex justify-between items-center bg-zinc-950/40 p-4 rounded-xl border border-white/5">
                    <div>
                      <span className="text-xs text-zinc-400 block font-light uppercase tracking-wider">Plan de Suscripción</span>
                      <span className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 uppercase">
                        {billingSettings?.tier || "FREE"}
                      </span>
                    </div>
                    <span className="text-xs font-bold text-zinc-400 px-3 py-1 bg-white/5 border border-white/10 rounded-full">
                      Organización
                    </span>
                  </div>

                  <div className="flex justify-between items-center bg-zinc-950/40 p-4 rounded-xl border border-white/5">
                    <div>
                      <span className="text-xs text-zinc-400 block font-light uppercase tracking-wider">Consumo Deudor Acumulado</span>
                      <span className="text-2xl font-black text-red-400">
                        ${billingSettings?.currentDebt?.toFixed(4) || "0.0000"} USD
                      </span>
                    </div>
                    {billingSettings?.currentDebt > 0 && (
                      <Button
                        onClick={() => handleCheckout("pay_debt")}
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 text-xs font-bold py-2 px-4 rounded-xl transition-all cursor-pointer"
                      >
                        Pagar Saldo
                      </Button>
                    )}
                  </div>
                  
                  <div className="flex gap-2 items-start text-xs text-zinc-400 bg-white/5 border border-white/5 p-3.5 rounded-xl">
                    <ShieldAlert className="w-4.5 h-4.5 text-amber-500 shrink-0 mt-0.5" />
                    <p className="leading-relaxed font-light">
                      <strong className="text-zinc-300 font-bold">Nota BYOK:</strong> Si configuras tus propias claves API (BYOK) para los proveedores de modelos activos, todo el consumo se facturará directamente a tus cuentas y no incurrirás en saldos deudores en la plataforma.
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Upgrade Tiers Cards */}
              <Card className="border border-border/60 bg-card/25 backdrop-blur-md shadow-md relative overflow-hidden group hover:border-primary/30 transition-all duration-300">
                <CardHeader>
                  <CardTitle className="text-lg font-bold flex gap-2 items-center text-white">
                    <Palette className="w-5 h-5 text-primary" /> Planes & Escalamiento
                  </CardTitle>
                  <CardDescription className="text-zinc-400">
                    Mejora tu suscripción para desbloquear modelos enterprise avanzados y mayores límites de loops.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {[
                    { id: "PRO", name: "SaaS PRO", price: "$99/mes", desc: "Desbloquea Claude 3.5 Sonnet, soporte extendido y 25 loops máx por agente.", color: "from-cyan-500/20 to-blue-500/5 hover:border-cyan-500/40" },
                    { id: "MAX", name: "SaaS MAX", price: "$299/mes", desc: "Soporte RAG extendido, analíticas premium y 50 loops por ejecución.", color: "from-emerald-500/20 to-teal-500/5 hover:border-emerald-500/40" },
                    { id: "OMNI", name: "SaaS OMNI", price: "$999/mes", desc: "Loops ilimitados, Omni Master Controller integrado y prioridad SLA.", color: "from-purple-500/20 to-violet-500/5 hover:border-purple-500/40" }
                  ].map((plan) => {
                    const isCurrent = (billingSettings?.tier || "FREE") === plan.id;
                    return (
                      <div
                        key={plan.id}
                        className={`flex justify-between items-center p-4 rounded-xl border border-white/5 bg-gradient-to-r ${plan.color} transition-all duration-300`}
                      >
                        <div className="space-y-1 pr-4">
                          <div className="flex items-center gap-2">
                            <span className="font-extrabold text-sm text-white">{plan.name}</span>
                            <span className="text-[10px] font-bold text-zinc-400 bg-white/5 border border-white/10 px-2 py-0.5 rounded-full">{plan.price}</span>
                          </div>
                          <p className="text-[11px] text-zinc-400 font-light leading-relaxed">{plan.desc}</p>
                        </div>
                        <Button
                          disabled={isCurrent}
                          onClick={() => handleCheckout("upgrade", plan.id)}
                          className={`text-xs font-bold py-2 px-4 rounded-xl cursor-pointer ${
                            isCurrent
                              ? "bg-zinc-800 text-zinc-500 border border-zinc-700 cursor-not-allowed hover:bg-zinc-800"
                              : "bg-primary hover:bg-primary/95 text-white"
                          }`}
                        >
                          {isCurrent ? "Actual" : "Mejorar"}
                        </Button>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </div>

            {/* API Keys Configuration Card */}
            <Card className="border border-border/60 bg-card/25 backdrop-blur-md shadow-md">
              <CardHeader>
                <CardTitle className="text-lg font-bold flex gap-2 items-center text-white">
                  <Key className="w-5 h-5 text-primary" /> Claves API de Proveedores (BYOK)
                </CardTitle>
                <CardDescription className="text-zinc-400">
                  Ingresa tus claves API para usarlas de forma global en la organización. Se almacenan cifradas en la base de datos.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {billingLoading ? (
                  <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
                ) : (
                  <>
                    <div className="grid gap-6 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="customOpenAiKey" className="text-xs font-bold text-zinc-400 uppercase tracking-wider">OpenAI API Key</Label>
                        <Input
                          id="customOpenAiKey"
                          type="password"
                          placeholder={billingSettings?.customOpenAiKey === "********" ? "********" : "sk-proj-..."}
                          value={keysState.customOpenAiKey === "********" ? "********" : keysState.customOpenAiKey}
                          onChange={(e) => setKeysState({ ...keysState, customOpenAiKey: e.target.value })}
                          className="bg-zinc-950/60 border-zinc-800 text-white font-mono text-xs"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="customAnthropicKey" className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Anthropic API Key</Label>
                        <Input
                          id="customAnthropicKey"
                          type="password"
                          placeholder={billingSettings?.customAnthropicKey === "********" ? "********" : "sk-ant-..."}
                          value={keysState.customAnthropicKey === "********" ? "********" : keysState.customAnthropicKey}
                          onChange={(e) => setKeysState({ ...keysState, customAnthropicKey: e.target.value })}
                          className="bg-zinc-950/60 border-zinc-800 text-white font-mono text-xs"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="customGeminiKey" className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Gemini API Key</Label>
                        <Input
                          id="customGeminiKey"
                          type="password"
                          placeholder={billingSettings?.customGeminiKey === "********" ? "********" : "AIzaSy..."}
                          value={keysState.customGeminiKey === "********" ? "********" : keysState.customGeminiKey}
                          onChange={(e) => setKeysState({ ...keysState, customGeminiKey: e.target.value })}
                          className="bg-zinc-950/60 border-zinc-800 text-white font-mono text-xs"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="customOpenRouterKey" className="text-xs font-bold text-zinc-400 uppercase tracking-wider">OpenRouter API Key</Label>
                        <Input
                          id="customOpenRouterKey"
                          type="password"
                          placeholder={billingSettings?.customOpenRouterKey === "********" ? "********" : "sk-or-..."}
                          value={keysState.customOpenRouterKey === "********" ? "********" : keysState.customOpenRouterKey}
                          onChange={(e) => setKeysState({ ...keysState, customOpenRouterKey: e.target.value })}
                          className="bg-zinc-950/60 border-zinc-800 text-white font-mono text-xs"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="customGrokKey" className="text-xs font-bold text-zinc-400 uppercase tracking-wider">xAI Grok API Key</Label>
                        <Input
                          id="customGrokKey"
                          type="password"
                          placeholder={billingSettings?.customGrokKey === "********" ? "********" : "xai-..."}
                          value={keysState.customGrokKey === "********" ? "********" : keysState.customGrokKey}
                          onChange={(e) => setKeysState({ ...keysState, customGrokKey: e.target.value })}
                          className="bg-zinc-950/60 border-zinc-800 text-white font-mono text-xs"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="customGroqKey" className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Groq API Key</Label>
                        <Input
                          id="customGroqKey"
                          type="password"
                          placeholder={billingSettings?.customGroqKey === "********" ? "********" : "gsk-..."}
                          value={keysState.customGroqKey === "********" ? "********" : keysState.customGroqKey}
                          onChange={(e) => setKeysState({ ...keysState, customGroqKey: e.target.value })}
                          className="bg-zinc-950/60 border-zinc-800 text-white font-mono text-xs"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
                      <Button
                        onClick={async () => {
                          try {
                            await fetchClient("/billing/settings", {
                              method: "PATCH",
                              body: JSON.stringify(keysState)
                            });
                            toast.success("Credenciales actualizadas", { description: "Tus claves BYOK se han guardado de forma cifrada." });
                            loadBillingSettings();
                          } catch (err) {
                            toast.error("Error al actualizar claves");
                          }
                        }}
                        className="bg-primary hover:bg-primary/95 text-white font-bold text-xs py-2.5 px-6 rounded-xl flex items-center gap-2 cursor-pointer"
                      >
                        <Save className="w-4 h-4" /> Guardar Claves
                      </Button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        )}

      </div>
    </div>
  );
}
