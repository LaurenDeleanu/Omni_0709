"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Link2, Check, X, ExternalLink, Loader2, AlertCircle } from "lucide-react";

interface Connector {
  provider: string; name: string; actions: string[];
}

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);

  useEffect(() => {
    fetchClient("/admin/connectors")
      .then((d) => setConnectors(d.connectors || []))
      .catch((err) => setError(err.message || "Failed to load connectors"))
      .finally(() => setLoading(false));
  }, []);

  const loadConfig = async (provider: string) => {
    setConfigLoading(true);
    setConfigError(null);
    try {
      const d = await fetchClient(`/admin/connectors/${provider}`);
      setConfig(d);
      setSelected(provider);
    } catch (err: any) {
      setConfigError(err.message || "Failed to load configuration");
    } finally {
      setConfigLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-64" />
          <div className="h-4 bg-muted rounded w-96" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-24 bg-card rounded-lg border border-border" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-5xl mx-auto flex flex-col items-center justify-center py-20 gap-3">
        <AlertCircle className="h-10 w-10 text-destructive" />
        <p className="text-sm text-destructive">{error}</p>
        <button onClick={() => window.location.reload()} className="text-xs text-primary hover:underline">Retry</button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Integration Connectors</h1>
      <p className="text-sm text-muted-foreground mb-8">Pre-built connectors for third-party integrations</p>

      {connectors.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 border border-dashed border-border rounded-xl">
          <Link2 className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">No connectors configured.</p>
          <p className="text-xs text-muted-foreground/60">Connectors will appear here once configured by your administrator.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {connectors.map((c) => (
            <button
              key={c.provider}
              onClick={() => loadConfig(c.provider)}
              disabled={configLoading}
              className={`rounded-lg border p-4 text-left transition-colors ${
                selected === c.provider
                  ? "border-primary bg-primary/5"
                  : "bg-card hover:bg-muted/50"
              } disabled:opacity-50`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold">{c.name}</span>
                {configLoading && selected === c.provider ? (
                  <Loader2 size={16} className="animate-spin text-muted-foreground" />
                ) : (
                  <Link2 size={16} className="text-muted-foreground" />
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {c.actions.map((a) => (
                  <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-muted">
                    {a}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      )}

      {configError && (
        <div className="mt-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-destructive" />
          <p className="text-xs text-destructive">{configError}</p>
        </div>
      )}

      {config && (
        <div className="mt-8 rounded-lg border bg-card p-6">
          <h2 className="font-semibold mb-4">{config.name} — Configuration</h2>
          {Object.entries(config.actions || {}).map(([name, action]: [string, any]) => (
            <div key={name} className="mb-4 p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium">{name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary">
                  {action.method}
                </span>
              </div>
              <code className="text-xs bg-background px-3 py-2 rounded block font-mono break-all">
                {action.url}
              </code>
              <details className="mt-2">
                <summary className="text-xs text-muted-foreground cursor-pointer">Body template</summary>
                <code className="text-xs bg-background px-3 py-2 rounded block font-mono mt-1 break-all">
                  {action.body_template}
                </code>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
