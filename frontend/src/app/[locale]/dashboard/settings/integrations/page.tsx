"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api/client";
import { toast } from "sonner";
import { Calendar, RefreshCcw, CheckCircle2, XCircle } from "lucide-react";

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null);

  const fetchIntegrations = async () => {
    try {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/integrations`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleConnect = async (provider: string) => {
    try {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/integrations/${provider}/auth-url`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        const data = await res.json();
        // Redirect to OAuth URL (Mock or Real)
        window.location.href = data.auth_url;
      }
    } catch (err) {
      toast.error(`Error conectando a ${provider}`);
    }
  };

  const handleDisconnect = async (provider: string) => {
    try {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/integrations/${provider}`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        toast.success(`Desconectado de ${provider}`);
        fetchIntegrations();
      }
    } catch (err) {
      toast.error(`Error desconectando de ${provider}`);
    }
  };

  const handleSync = async (provider: string) => {
    setSyncingProvider(provider);
    try {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/integrations/${provider}/sync`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || "Sincronización exitosa");
        fetchIntegrations();
      } else {
        toast.error("Fallo en sincronización");
      }
    } catch (err) {
      toast.error("Error contactando servidor");
    } finally {
      setSyncingProvider(null);
    }
  };

  const getIntegration = (provider: string) => integrations.find(i => i.provider === provider);

  if (loading) return <div className="p-8">Cargando integraciones...</div>;

  return (
    <div className="max-w-4xl space-y-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Integraciones</h1>
        <p className="text-muted-foreground mt-1">
          Conecta tus herramientas externas para sincronizar calendarios y datos automáticamente.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Google Workspace */}
        <IntegrationCard 
          title="Google Workspace"
          description="Sincronización bidireccional con Google Calendar."
          provider="google"
          icon={<img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" alt="Google" className="w-8 h-8" />}
          integration={getIntegration("google")}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onSync={handleSync}
          isSyncing={syncingProvider === "google"}
        />

        {/* Microsoft 365 */}
        <IntegrationCard 
          title="Microsoft 365"
          description="Sincronización bidireccional con Outlook Calendar."
          provider="microsoft"
          icon={<img src="https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg" alt="Microsoft" className="w-8 h-8" />}
          integration={getIntegration("microsoft")}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onSync={handleSync}
          isSyncing={syncingProvider === "microsoft"}
        />
      </div>
    </div>
  );
}

function IntegrationCard({ title, description, provider, icon, integration, onConnect, onDisconnect, onSync, isSyncing }: any) {
  const isConnected = !!integration;

  return (
    <Card className="border-border/50 bg-card/40 backdrop-blur-xl relative overflow-hidden group">
      <CardHeader className="flex flex-row items-start gap-4">
        <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center p-2">
          {icon}
        </div>
        <div className="flex-1">
          <CardTitle className="text-lg flex justify-between items-center">
            {title}
            {isConnected ? (
              <span className="flex items-center gap-1 text-xs font-medium text-green-600 bg-green-500/10 px-2 py-1 rounded-full">
                <CheckCircle2 className="w-3 h-3" /> Conectado
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs font-medium text-muted-foreground bg-muted px-2 py-1 rounded-full">
                <XCircle className="w-3 h-3" /> Desconectado
              </span>
            )}
          </CardTitle>
          <CardDescription className="mt-1">{description}</CardDescription>
        </div>
      </CardHeader>

      <CardContent>
        {isConnected && (
          <div className="text-sm bg-muted/30 p-3 rounded-lg flex flex-col gap-2 border border-border/50">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Cuenta conectada:</span>
              <span className="font-medium truncate max-w-[200px]">{integration.external_email}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Última sync:</span>
              <span className="text-xs">
                {integration.last_sync_at ? new Date(integration.last_sync_at).toLocaleString() : "Nunca"}
              </span>
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-between gap-3 bg-muted/10 border-t border-border/50 py-3">
        {isConnected ? (
          <>
            <Button variant="outline" className="flex-1 text-red-500 hover:text-red-600 hover:bg-red-500/10" onClick={() => onDisconnect(provider)}>
              Desconectar
            </Button>
            <Button className="flex-1 gap-2" onClick={() => onSync(provider)} disabled={isSyncing}>
              <RefreshCcw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
              Sincronizar
            </Button>
          </>
        ) : (
          <Button className="w-full" onClick={() => onConnect(provider)}>
            Conectar Cuenta
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
