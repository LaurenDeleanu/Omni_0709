"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Link2, Check, X, ExternalLink } from "lucide-react";

interface Connector {
  provider: string; name: string; actions: string[];
}

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    fetchClient("/admin/connectors").then(d => setConnectors(d.connectors || [])).catch(() => {});
  }, []);

  const loadConfig = async (provider: string) => {
    try {
      const d = await fetchClient(`/admin/connectors/${provider}`);
      setConfig(d);
      setSelected(provider);
    } catch {}
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Integration Connectors</h1>
      <p className="text-sm text-muted-foreground mb-8">Pre-built connectors for third-party integrations</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {connectors.map(c => (
          <button key={c.provider} onClick={() => loadConfig(c.provider)} className={`rounded-lg border p-4 text-left transition-colors ${selected === c.provider ? "border-primary bg-primary/5" : "bg-card hover:bg-muted/50"}`}>
            <div className="flex items-center justify-between mb-3"><span className="font-semibold">{c.name}</span><Link2 size={16} className="text-muted-foreground" /></div>
            <div className="flex flex-wrap gap-1.5">
              {c.actions.map(a => (<span key={a} className="text-xs px-2 py-0.5 rounded-full bg-muted">{a}</span>))}
            </div>
          </button>
        ))}
      </div>

      {config && (
        <div className="mt-8 rounded-lg border bg-card p-6">
          <h2 className="font-semibold mb-4">{config.name} — Configuration</h2>
          {Object.entries(config.actions || {}).map(([name, action]: [string, any]) => (
            <div key={name} className="mb-4 p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-2"><span className="text-sm font-medium">{name}</span><span className="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400">{action.method}</span></div>
              <code className="text-xs bg-background px-3 py-2 rounded block font-mono break-all">{action.url}</code>
              <details className="mt-2"><summary className="text-xs text-muted-foreground cursor-pointer">Body template</summary><code className="text-xs bg-background px-3 py-2 rounded block font-mono mt-1 break-all">{action.body_template}</code></details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
