"use client";

import { useState } from "react";
import { Zap, Copy, Check, ExternalLink, Activity, ArrowRight, Key, Webhook, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { useTenant } from "@/providers/tenant-provider";

export default function PowerAutomateAdmin() {
  const { name } = useTenant();
  const [copied, setCopied] = useState<string | null>(null);

  const mockApiKey = "sk_live_pa_8f92j10xnc8v7";
  const apiUrl = typeof window !== "undefined" ? window.location.origin + "/api/v1/power-automate" : "https://api.successcore.com/v1/power-automate";

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    toast.success("Copiado al portapapeles");
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-6 rounded-2xl border border-primary/20 bg-gradient-to-br from-card to-primary/5 shadow-lg shadow-primary/5 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-[#0078D4]/10 flex items-center justify-center border border-[#0078D4]/30">
              <Zap className="w-6 h-6 text-[#0078D4]" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Power Automate</h1>
          </div>
          <p className="text-muted-foreground text-sm max-w-xl">
            Integra {name || "Omnius"} con Microsoft Power Automate. Automatiza flujos de trabajo, reacciona a eventos en tiempo real y controla la plataforma desde el ecosistema 365.
          </p>
        </div>
        <a 
          href="https://make.powerautomate.com/" 
          target="_blank" 
          rel="noreferrer"
          className="relative z-10 flex items-center gap-2 px-4 py-2 bg-[#0078D4] hover:bg-[#0078D4]/90 text-white rounded-lg text-sm font-medium transition-colors shadow-md shadow-[#0078D4]/20"
        >
          Abrir Power Automate <ExternalLink className="w-4 h-4" />
        </a>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* API Authentication Panel */}
        <div className="bg-card border border-border/50 rounded-xl p-6 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold">Credenciales de API</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-6 flex-1">
            Utiliza esta clave API (API Key) para autenticar las acciones HTTP desde Power Automate hacia {name}. Debes enviarla en el header <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">Authorization: Bearer YOUR_KEY</code>.
          </p>
          
          <div className="bg-muted/30 border border-border/50 rounded-lg p-3 flex items-center justify-between">
            <div className="font-mono text-sm tracking-tight text-foreground truncate mr-4">
              •••••••••••••••••••••••••••••
            </div>
            <button 
              onClick={() => handleCopy(mockApiKey, "apikey")}
              className="p-2 hover:bg-muted rounded-md transition-colors text-muted-foreground hover:text-foreground"
            >
              {copied === "apikey" ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs text-amber-500 bg-amber-500/10 p-2 rounded-md border border-amber-500/20">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>Manten esta clave en secreto. Nunca la compartas ni la subas a repositorios públicos.</span>
          </div>
        </div>

        {/* Triggers Panel */}
        <div className="bg-card border border-border/50 rounded-xl p-6 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Webhook className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold">Endpoints de Eventos (Triggers)</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-6 flex-1">
            Configura Power Automate para consultar periódicamente estos endpoints y detectar nuevos eventos en la plataforma.
          </p>

          <div className="space-y-3">
            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Nuevo Empleado Contratado</span>
              <div className="bg-muted/30 border border-border/50 rounded-lg p-2.5 flex items-center justify-between">
                <code className="text-xs font-mono text-primary truncate">GET {apiUrl}/triggers/new-employee</code>
                <button onClick={() => handleCopy(`${apiUrl}/triggers/new-employee`, "t1")} className="p-1 hover:bg-muted rounded ml-2">
                  {copied === "t1" ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
                </button>
              </div>
            </div>
            
            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Nuevo Ticket IT</span>
              <div className="bg-muted/30 border border-border/50 rounded-lg p-2.5 flex items-center justify-between">
                <code className="text-xs font-mono text-primary truncate">GET {apiUrl}/triggers/new-ticket</code>
                <button onClick={() => handleCopy(`${apiUrl}/triggers/new-ticket`, "t2")} className="p-1 hover:bg-muted rounded ml-2">
                  {copied === "t2" ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Nuevas Solicitudes de Ausencia (Vacaciones/Permisos)</span>
              <div className="bg-muted/30 border border-border/50 rounded-lg p-2.5 flex items-center justify-between">
                <code className="text-xs font-mono text-primary truncate">GET {apiUrl}/triggers/leave-requests</code>
                <button onClick={() => handleCopy(`${apiUrl}/triggers/leave-requests`, "t3")} className="p-1 hover:bg-muted rounded ml-2">
                  {copied === "t3" ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Actions Guide */}
      <div className="bg-card border border-border/50 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-6">
          <Activity className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold">Acciones Disponibles</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div className="group border border-border/50 rounded-lg p-4 hover:border-primary/50 transition-colors bg-muted/10 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
              <Zap className="w-16 h-16 text-[#0078D4]" />
            </div>
            <div className="mb-1 flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-500/10 text-green-500 border border-green-500/20">POST</span>
              <span className="font-semibold text-sm">Ejecutar Agente AI</span>
            </div>
            <code className="text-xs font-mono text-muted-foreground block mb-3">{apiUrl}/actions/run-agent</code>
            <p className="text-[11px] text-muted-foreground line-clamp-2">Lanza la ejecución de un Agente de IA pasándole un payload específico. Útil para automatizar respuestas o flujos complejos.</p>
          </div>

          <div className="group border border-border/50 rounded-lg p-4 hover:border-primary/50 transition-colors bg-muted/10 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
              <Zap className="w-16 h-16 text-[#0078D4]" />
            </div>
            <div className="mb-1 flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-500/10 text-green-500 border border-green-500/20">POST</span>
              <span className="font-semibold text-sm">Crear Ticket IT</span>
            </div>
            <code className="text-xs font-mono text-muted-foreground block mb-3">{apiUrl}/actions/create-ticket</code>
            <p className="text-[11px] text-muted-foreground line-clamp-2">Crea un ticket de soporte de manera automática. Útil cuando una alerta de infraestructura se dispara en Azure.</p>
          </div>

          <div className="group border border-border/50 rounded-lg p-4 hover:border-primary/50 transition-colors bg-muted/10 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
              <Zap className="w-16 h-16 text-[#0078D4]" />
            </div>
            <div className="mb-1 flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-500/10 text-green-500 border border-green-500/20">POST</span>
              <span className="font-semibold text-sm">Enviar Notificación</span>
            </div>
            <code className="text-xs font-mono text-muted-foreground block mb-3">{apiUrl}/actions/send-notification</code>
            <p className="text-[11px] text-muted-foreground line-clamp-2">Envía una alerta in-app al centro de notificaciones de un empleado (ej: alertas críticas, vencimientos).</p>
          </div>
        </div>
      </div>

    </div>
  );
}
