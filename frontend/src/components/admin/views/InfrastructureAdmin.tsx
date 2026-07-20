"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Download, Database, HardDrive, Shield, AlertTriangle, Activity, Server } from "lucide-react";
import { toast } from "sonner";

export default function InfrastructureAdmin() {
  const [storage, setStorage] = useState<any>(null);
  const [pool, setPool] = useState<any>(null);
  const [residency, setResidency] = useState<any>(null);
  const [backups, setBackups] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState("overview");

  const fetchAll = async () => {
    try { setStorage(await fetchClient("/admin/storage-usage")); } catch {}
    try { setPool(await fetchClient("/monitoring/pool-stats")); } catch {}
    try { setResidency(await fetchClient("/admin/data-residency-audit")); } catch {}
    try { const b = await fetchClient("/admin/backups"); setBackups(b.backups || []); } catch {}
  };

  useEffect(() => { fetchAll(); }, []);

  const triggerBackup = async () => {
    try { await fetchClient("/admin/backup", { method: "POST" }); toast.success("Backup started"); setTimeout(fetchAll, 3000); } catch (e: any) { toast.error(e.message); }
  };

  const enforceRetention = async () => {
    try { await fetchClient("/admin/retention/enforce", { method: "POST" }); toast.success("Retention enforced"); } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Infrastructure & Compliance</h1>
      <p className="text-sm text-muted-foreground mb-8">Database, storage, backups, and compliance status</p>

      <div className="flex gap-2 mb-6">
        {["overview", "backups", "compliance"].map(t => (
          <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${activeTab === t ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}>{t}</button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard icon={<HardDrive size={20} />} title="Database Size" value={storage?.database?.total_size || "..."} subtitle="PostgreSQL" />
            <StatCard icon={<Server size={20} />} title="Connection Pool" value={`${pool?.checked_out || 0}/${pool?.size || 0}`} subtitle={`${pool?.utilization_pct || 0}% utilized`} />
            <StatCard icon={<Shield size={20} />} title="Data Residency" value={residency?.configured_residency || "EU"} subtitle={`${Object.values(residency?.compliance_checks || {}).filter((c: any) => c.status === "passed").length || 0} checks passed`} />
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-semibold mb-3">Largest Tables</h3>
            <div className="space-y-2">
              {(storage?.largest_tables || []).slice(0, 10).map((t: any) => (
                <div key={t.table} className="flex justify-between text-sm"><span className="font-mono text-xs">{t.table}</span><span className="text-muted-foreground">{t.size}</span></div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "backups" && (
        <div className="space-y-4">
          <button onClick={triggerBackup} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium"><Download size={16} /> Create Backup</button>
          <button onClick={enforceRetention} className="flex items-center gap-2 px-4 py-2 bg-muted rounded-lg text-sm ml-3"><TrashIcon size={16} /> Enforce Retention</button>
          <div className="space-y-2 mt-4">
            {backups.map((b: any) => (
              <div key={b.filename} className="rounded-lg border bg-card p-3 flex justify-between items-center">
                <div><p className="text-sm font-mono">{b.filename}</p><p className="text-xs text-muted-foreground">{b.size_mb} MB</p></div>
              </div>
            ))}
            {backups.length === 0 && <p className="text-center text-muted-foreground py-8">No backups yet</p>}
          </div>
        </div>
      )}

      {activeTab === "compliance" && residency && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-semibold mb-3">Chain of Custody</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(residency.chain_of_custody || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between"><span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</span><span className="font-mono text-xs">{String(v)}</span></div>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            {(residency.compliance_checks || []).map((c: any) => (
              <div key={c.check} className="rounded-lg border bg-card p-3 flex items-center justify-between">
                <div><p className="text-sm font-medium">{c.check}</p><p className="text-xs text-muted-foreground">{c.detail}</p></div>
                <span className={`text-xs px-2 py-1 rounded-full ${c.status === "passed" ? "bg-green-500/10 text-green-400" : c.status === "partial" ? "bg-yellow-500/10 text-yellow-400" : "bg-red-500/10 text-red-400"}`}>{c.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, title, value, subtitle }: { icon: any; title: string; value: string; subtitle: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-muted-foreground">{icon}</span>
        <span className="text-sm font-medium">{title}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>
    </div>
  );
}

function TrashIcon({ size }: { size: number }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
    </svg>
  );
}
