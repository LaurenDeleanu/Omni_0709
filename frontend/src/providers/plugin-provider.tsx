"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { fetchClient } from "@/lib/api/client";

interface PluginManifest {
  id: string; name: string; icon: string;
  manifest: { sidebar_items?: any[]; widgets?: any[] };
}

interface PluginContext {
  installed: PluginManifest[];
  sidebarItems: any[];
  widgets: any[];
  loading: boolean;
}

const PluginCtx = createContext<PluginContext>({ installed: [], sidebarItems: [], widgets: [], loading: true });

export function usePlugins() { return useContext(PluginCtx); }

export function PluginProvider({ children }: { children: ReactNode }) {
  const [installed, setInstalled] = useState<PluginManifest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchClient("/plugins/installed").then(d => {
      setInstalled(d.installed || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const sidebarItems = installed.flatMap(p => (p.manifest?.sidebar_items || []).map((item: any) => ({
    ...item, pluginName: p.name, pluginIcon: p.icon, pluginId: p.id
  })));

  const widgets = installed.flatMap(p => (p.manifest?.widgets || []).map((w: any) => ({
    ...w, pluginName: p.name, pluginIcon: p.icon, pluginId: p.id
  })));

  return <PluginCtx.Provider value={{ installed, sidebarItems, widgets, loading }}>{children}</PluginCtx.Provider>;
}
