"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Plus, Trash2, RefreshCw, Key, Copy, Check, ExternalLink, Activity } from "lucide-react";
import { toast } from "sonner";

interface OAuthClient {
  id: string; client_id: string; name: string; description: string;
  redirect_uris: string; scopes: string; is_active: boolean; created_at: string;
}

export default function DeveloperPortal() {
  const [clients, setClients] = useState<OAuthClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [newClient, setNewClient] = useState({ name: "", redirect_uris: "", scopes: "read:all", description: "" });
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"clients" | "analytics" | "docs">("clients");
  const [analytics, setAnalytics] = useState<any>({});

  const fetchClients = async () => {
    setLoading(true);
    try { const data = await fetchClient("/oauth/clients"); setClients(data); } catch {}
    setLoading(false);
  };

  const fetchAnalytics = async () => {
    try { const data = await fetchClient("/oauth/analytics"); setAnalytics(data); } catch {}
  };

  useEffect(() => { fetchClients(); fetchAnalytics(); }, []);

  const createClient = async () => {
    try {
      const data = await fetchClient("/oauth/clients", { method: "POST", body: JSON.stringify(newClient) });
      setNewSecret(data.client_secret);
      setNewClient({ name: "", redirect_uris: "", scopes: "read:all", description: "" });
      await fetchClients();
      toast.success("OAuth client created");
    } catch (e: any) { toast.error(e.message || "Failed to create client"); }
  };

  const rotateSecret = async (clientId: string) => {
    try {
      const data = await fetchClient(`/oauth/clients/${clientId}/rotate-secret`, { method: "POST" });
      setNewSecret(data.client_secret);
      toast.success("Secret rotated");
    } catch (e: any) { toast.error(e.message || "Failed to rotate"); }
  };

  const deactivateClient = async (clientId: string) => {
    try {
      await fetchClient(`/oauth/clients/${clientId}`, { method: "DELETE" });
      await fetchClients();
      toast.success("Client deactivated");
    } catch (e: any) { toast.error(e.message || "Failed to deactivate"); }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Developer Portal</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage OAuth2 applications and API access</p>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {(["clients", "analytics", "docs"] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}>
            {tab === "clients" ? "Applications" : tab === "analytics" ? "Usage Analytics" : "API Docs"}
          </button>
        ))}
      </div>

      {activeTab === "clients" && (
        <>
          {newSecret && (
            <div className="mb-6 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
              <div className="flex items-center gap-2 mb-2"><Key size={16} className="text-yellow-400" /><span className="font-bold text-sm">New Client Secret — Copy this now. It won&apos;t be shown again.</span></div>
              <code className="text-sm bg-background px-3 py-2 rounded block font-mono break-all">{newSecret}</code>
              <button onClick={() => { navigator.clipboard.writeText(newSecret); toast.success("Copied"); setNewSecret(null); }} className="mt-2 text-xs text-primary hover:underline">Copy and dismiss</button>
            </div>
          )}

          <div className="rounded-lg border bg-card p-4 mb-6">
            <h2 className="font-semibold mb-4">Register New Application</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input placeholder="Application name" value={newClient.name} onChange={e => setNewClient({...newClient, name: e.target.value})} className="bg-background border rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Redirect URIs (comma-separated)" value={newClient.redirect_uris} onChange={e => setNewClient({...newClient, redirect_uris: e.target.value})} className="bg-background border rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Scopes (e.g. read:all, write:employees)" value={newClient.scopes} onChange={e => setNewClient({...newClient, scopes: e.target.value})} className="bg-background border rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Description (optional)" value={newClient.description} onChange={e => setNewClient({...newClient, description: e.target.value})} className="bg-background border rounded-lg px-3 py-2 text-sm" />
            </div>
            <button onClick={createClient} disabled={!newClient.name || !newClient.redirect_uris} className="mt-3 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50">
              Register Application
            </button>
          </div>

          <div className="space-y-3">
            {clients.map(c => (
              <div key={c.id} className="rounded-lg border bg-card p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2"><span className="font-medium">{c.name}</span><span className={`text-xs px-2 py-0.5 rounded-full ${c.is_active ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>{c.is_active ? "Active" : "Disabled"}</span></div>
                  <p className="text-xs text-muted-foreground mt-1">Client ID: {c.client_id}</p>
                  <p className="text-xs text-muted-foreground">Scopes: {c.scopes}</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => rotateSecret(c.client_id)} className="p-2 hover:bg-muted rounded-lg" title="Rotate Secret"><RefreshCw size={14} /></button>
                  <button onClick={() => deactivateClient(c.client_id)} className="p-2 hover:bg-red-500/10 rounded-lg text-red-400" title="Deactivate"><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
            {clients.length === 0 && !loading && <p className="text-center text-muted-foreground py-12">No applications registered yet</p>}
          </div>
        </>
      )}

      {activeTab === "analytics" && (
        <div className="rounded-lg border bg-card p-6">
          <h2 className="font-semibold mb-4">API Usage Analytics</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-muted"><div className="text-2xl font-bold">{analytics.total_apps || 0}</div><div className="text-xs text-muted-foreground">Registered Apps</div></div>
            <div className="p-4 rounded-lg bg-muted"><div className="text-2xl font-bold">{analytics.clients ? Object.keys(analytics.clients).length : 0}</div><div className="text-xs text-muted-foreground">Active Clients</div></div>
            <div className="p-4 rounded-lg bg-muted"><div className="text-2xl font-bold">{Object.values(analytics.clients || {}).reduce((s: number, c: any) => s + (c.calls || 0), 0)}</div><div className="text-xs text-muted-foreground">Total API Calls</div></div>
          </div>
        </div>
      )}

      {activeTab === "docs" && (
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h2 className="font-semibold">API Documentation</h2>
          <p className="text-sm text-muted-foreground">Full OpenAPI 3.1 specification available at:</p>
          <code className="text-sm bg-background px-3 py-2 rounded block font-mono">GET /openapi.json</code>
          <div className="flex gap-3 mt-2">
            <a href={`${process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? ""}/docs`} target="_blank" className="flex items-center gap-1 text-sm text-primary hover:underline"><ExternalLink size={14} /> Swagger UI</a>
            <a href={`${process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? ""}/postman.json`} target="_blank" className="flex items-center gap-1 text-sm text-primary hover:underline"><ExternalLink size={14} /> Postman Collection</a>
            <a href={`${process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? ""}/sdk.tgz`} className="flex items-center gap-1 text-sm text-primary hover:underline"><ExternalLink size={14} /> TypeScript SDK (.tgz)</a>
          </div>
        </div>
      )}
    </div>
  );
}
