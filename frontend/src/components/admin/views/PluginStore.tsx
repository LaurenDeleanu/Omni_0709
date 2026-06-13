"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Star, Download, Puzzle, Search, Check, X, ExternalLink } from "lucide-react";
import { toast } from "sonner";

interface Plugin {
  id: string; name: string; version: string; author: string; description: string;
  category: string; icon: string; install_count: number; avg_rating: number; is_verified: boolean;
}

interface Review {
  id: string; user_name: string; rating: number; review: string; created_at: string;
}

export default function PluginStore() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [installed, setInstalled] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchPlugins(); fetchInstalled(); }, [category, search]);

  const fetchPlugins = async () => {
    try {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (search) params.set("search", search);
      const d = await fetchClient(`/plugins?${params}`);
      setPlugins(d.plugins || []);
    } catch {} finally { setLoading(false); }
  };

  const fetchInstalled = async () => {
    try { const d = await fetchClient("/plugins/installed"); setInstalled((d.installed || []).map((p: any) => p.id)); } catch {}
  };

  const fetchReviews = async (pluginId: string) => {
    try { const d = await fetchClient(`/plugins/${pluginId}/reviews`); setReviews(d.reviews || []); } catch {}
  };

  const install = async (pluginId: string) => {
    try { await fetchClient(`/plugins/${pluginId}/install`, { method: "POST", body: JSON.stringify({ config: {} }) }); setInstalled([...installed, pluginId]); toast.success("Installed"); fetchPlugins(); } catch (e: any) { toast.error(e.message); }
  };

  const uninstall = async (pluginId: string) => {
    try { await fetchClient(`/plugins/${pluginId}/uninstall`, { method: "POST" }); setInstalled(installed.filter(id => id !== pluginId)); toast.success("Uninstalled"); fetchPlugins(); } catch (e: any) { toast.error(e.message); }
  };

  const addReview = async (pluginId: string) => {
    const rating = parseInt(prompt("Rating (1-5):") || "0");
    if (rating < 1 || rating > 5) return;
    const review = prompt("Your review:") || "";
    try { await fetchClient(`/plugins/${pluginId}/reviews`, { method: "POST", body: JSON.stringify({ rating, review }) }); toast.success("Review submitted"); fetchReviews(pluginId); fetchPlugins(); } catch (e: any) { toast.error(e.message); }
  };

  const selectedPlugin = plugins.find(p => p.id === selected);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Plugin Marketplace</h1>
          <p className="text-sm text-muted-foreground mt-1">Browse, install, and rate extensions for your platform</p>
        </div>
      </div>

      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-2.5 text-muted-foreground" />
          <input placeholder="Search plugins..." value={search} onChange={e => setSearch(e.target.value)} className="w-full pl-9 pr-3 py-2 bg-background border rounded-lg text-sm" />
        </div>
        <select value={category} onChange={e => setCategory(e.target.value)} className="bg-background border rounded-lg px-3 py-2 text-sm">
          <option value="">All Categories</option>
          <option value="tools">Tools</option>
          <option value="hr">HR</option>
          <option value="communication">Communication</option>
          <option value="analytics">Analytics</option>
          <option value="compliance">Compliance</option>
          <option value="productivity">Productivity</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {plugins.map(p => (
          <div key={p.id} onClick={() => { setSelected(p.id); fetchReviews(p.id); }} className={`rounded-lg border p-4 text-left transition-colors cursor-pointer ${selected === p.id ? "border-primary bg-primary/5" : "bg-card hover:bg-muted/50"}`}>
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xl">{p.icon}</span>
                <div>
                  <div className="flex items-center gap-1.5"><span className="font-medium">{p.name}</span>{p.is_verified && <Check size={12} className="text-blue-400" />}</div>
                  <p className="text-xs text-muted-foreground">by {p.author} · v{p.version}</p>
                </div>
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Star size={12} className="text-yellow-400" /><span>{p.avg_rating.toFixed(1)}</span>
                <Download size={12} className="ml-2" /><span>{p.install_count}</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">{p.description}</p>
            <div className="flex gap-2 mt-3">
              {installed.includes(p.id) ? (
                <button onClick={(e) => { e.stopPropagation(); uninstall(p.id); }} className="text-xs px-2 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20"><X size={12} className="inline mr-1" />Uninstall</button>
              ) : (
                <button onClick={(e) => { e.stopPropagation(); install(p.id); }} className="text-xs px-2 py-1 rounded bg-primary/10 text-primary hover:bg-primary/20"><Download size={12} className="inline mr-1" />Install</button>
              )}
              <button onClick={(e) => { e.stopPropagation(); addReview(p.id); }} className="text-xs px-2 py-1 rounded bg-muted hover:bg-muted/80"><Star size={12} className="inline mr-1" />Rate</button>
            </div>
          </div>
        ))}
      </div>

      {selectedPlugin && reviews.length > 0 && (
        <div className="mt-6 rounded-lg border bg-card p-4">
          <h3 className="font-semibold mb-3">Reviews for {selectedPlugin.name}</h3>
          <div className="space-y-2">
            {reviews.map(r => (
              <div key={r.id} className="p-2 rounded bg-muted/50">
                <div className="flex items-center gap-1 mb-1"><span className="text-xs font-medium">{r.user_name}</span><span className="text-yellow-400 text-xs">{"★".repeat(r.rating)}{"☆".repeat(5-r.rating)}</span></div>
                <p className="text-xs text-muted-foreground">{r.review}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {plugins.length === 0 && !loading && (
        <div className="text-center py-16 text-muted-foreground">
          <Puzzle size={48} className="mx-auto mb-4 opacity-20" />
          <p>No plugins found. Be the first to publish one!</p>
        </div>
      )}
    </div>
  );
}
