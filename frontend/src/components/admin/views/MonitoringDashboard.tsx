"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Activity, Zap, Clock, TrendingUp, DollarSign, BarChart3, Users, AlertTriangle } from "lucide-react";

export default function MonitoringDashboard() {
  const [data, setData] = useState<any>({});
  const [loading, setLoading] = useState(true);

  const fetchSection = async (key: string, url: string) => {
    try { const d = await fetchClient(url); setData((prev: any) => ({ ...prev, [key]: d }));       } catch (err: any) {
        console.error(`Monitoring fetch failed for ${key}:`, err);
      }
  };

  useEffect(() => {
    Promise.all([
      fetchSection("costs", "/monitoring/agent-costs?weeks=4"),
      fetchSection("heatmap", "/monitoring/agent-heatmap?days=7"),
      fetchSection("concurrency", "/monitoring/concurrency"),
      fetchSection("provider", "/monitoring/provider-health"),
      fetchSection("api", "/monitoring/api-analytics"),
    ]).finally(() => setLoading(false));
  }, []);

  const costs = data.costs || {};
  const heatmap = data.heatmap || {};
  const concurrency = data.concurrency || {};
  const provider = data.provider || {};
  const api = data.api || {};

  if (loading) return <div className="p-8 text-center text-muted-foreground">Loading...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Monitoring Dashboard</h1>
      <p className="text-sm text-muted-foreground mb-8">Real-time platform health and AI agent metrics</p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <MiniCard icon={<Activity size={18} />} label="Agent Runs (4w)" value={costs.total_runs || 0} />
        <MiniCard icon={<DollarSign size={18} />} label="Total Cost" value={`$${(costs.total_cost || 0).toFixed(2)}`} />
        <MiniCard icon={<Users size={18} />} label="Active Runs" value={concurrency.active_runs || 0} />
        <MiniCard icon={<AlertTriangle size={18} />} label="API Requests" value={api.total_requests || 0} color="text-yellow-400" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-lg border bg-card p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2"><TrendingUp size={16} /> Weekly Cost Trend</h3>
          <div className="space-y-2">
            {(costs.weekly_trend || []).slice(-4).map((w: any) => (
              <div key={w.week} className="flex justify-between text-sm"><span>{w.week}</span><span className="text-muted-foreground">{w.runs} runs</span><span className="font-mono">${w.cost_usd.toFixed(2)}</span></div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2"><Clock size={16} /> Busiest Hours</h3>
          <div className="flex items-end gap-1 h-24">
            {(heatmap.hourly_distribution || []).map((h: any) => {
              const pct = heatmap.total_runs ? (h.count / heatmap.total_runs * 100) : 0;
              return <div key={h.hour} className="flex-1 flex flex-col items-center" title={`${h.hour}:00 — ${h.count} runs (${h.pct}%)`}>
                <div className="w-full bg-primary/30 rounded-t" style={{ height: `${Math.max(pct * 2, 2)}px` }} />
                <span className="text-[9px] text-muted-foreground mt-1">{h.hour}</span>
              </div>;
            })}
          </div>
          <div className="flex justify-between mt-2 text-xs text-muted-foreground">
            <span>Peak: {heatmap.peak_hour}:00 ({heatmap.hourly_distribution?.find((h: any) => h.hour === heatmap.peak_hour)?.count || 0} runs)</span>
            <span>Peak day: {heatmap.peak_day}</span>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2"><BarChart3 size={16} /> Per-Agent Costs</h3>
          <div className="space-y-2">
            {(costs.agent_breakdown || []).slice(0, 5).map((a: any) => (
              <div key={a.agent_id} className="flex justify-between text-sm">
                <span className="truncate max-w-[150px]">{a.agent_name || a.agent_id?.slice(0, 8)}</span>
                <span className="text-muted-foreground">{a.total_runs} runs</span>
                <span className="font-mono">${a.total_cost.toFixed(2)}</span>
                <span className="text-xs text-muted-foreground">{a.success_rate}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2"><Zap size={16} /> Provider Health</h3>
          <div className="space-y-2">
            {(provider.providers || []).map((p: any) => (
              <div key={p.provider} className="flex items-center justify-between text-sm">
                <span className="capitalize">{p.provider}</span>
                <span className={`w-2 h-2 rounded-full ${p.healthy ? "bg-green-400" : "bg-red-400"}`} />
                <span className="text-xs text-muted-foreground">{p.total_attempts} calls, {p.avg_latency_ms}ms avg</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-lg border bg-card p-4">
        <h3 className="font-semibold mb-3">Top API Routes</h3>
        <div className="space-y-1">
          {(api.routes || []).slice(0, 10).map((r: any, i: number) => (
            <div key={i} className="flex justify-between text-xs">
              <span className="font-mono truncate max-w-[400px]">{r.route}</span>
              <span className="text-muted-foreground">{r.count} calls</span>
              <span className="text-muted-foreground">{r.avg_latency_ms}ms</span>
              <span className={r.error_rate > 5 ? "text-red-400" : "text-green-400"}>{r.error_rate}% err</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MiniCard({ icon, label, value, color }: { icon: any; label: string; value: string | number; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 mb-1"><span className={color || "text-muted-foreground"}>{icon}</span><span className="text-xs text-muted-foreground">{label}</span></div>
      <div className={`text-lg font-bold ${color || ""}`}>{value}</div>
    </div>
  );
}
