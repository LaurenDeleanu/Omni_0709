"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Database, FileText, Layers, Search, Brain, Sparkles,
  Activity, RefreshCw, AlertCircle, CheckCircle2, Upload,
  Clock
} from "lucide-react";
import { toast } from "sonner";

const MOCK_AGENTS = [
  {
    id: "agent-hr-copilot",
    name: "HR Copilot",
    doc_count: 124,
    chunk_count: 856,
    total_chars: 312000,
    last_indexed: "2026-06-12T15:30:00",
    embedding_model: "text-embedding-3-small",
  },
  {
    id: "agent-recruiter",
    name: "Recruiter Agent",
    doc_count: 89,
    chunk_count: 612,
    total_chars: 245000,
    last_indexed: "2026-06-11T10:15:00",
    embedding_model: "text-embedding-3-small",
  },
  {
    id: "agent-it-helpdesk",
    name: "IT Helpdesk Agent",
    doc_count: 203,
    chunk_count: 1420,
    total_chars: 580000,
    last_indexed: "2026-06-12T18:45:00",
    embedding_model: "text-embedding-3-small",
  },
  {
    id: "agent-payroll",
    name: "Payroll Agent",
    doc_count: 45,
    chunk_count: 310,
    total_chars: 128000,
    last_indexed: "2026-06-10T09:00:00",
    embedding_model: "text-embedding-3-small",
  },
  {
    id: "agent-compliance",
    name: "Compliance Agent",
    doc_count: 167,
    chunk_count: 980,
    total_chars: 420000,
    last_indexed: "2026-06-12T14:20:00",
    embedding_model: "text-embedding-3-small",
  },
];

// Snapshot timestamp for the static mock data above (kept out of render for purity).
const MOCK_NOW_TS = Date.now();

const QUERY_STATS = [
  { agent: "HR Copilot", queries_24h: 342, avg_similarity: 0.78, avg_latency_ms: 120, cache_hit_rate: 45 },
  { agent: "IT Helpdesk", queries_24h: 512, avg_similarity: 0.82, avg_latency_ms: 95, cache_hit_rate: 62 },
  { agent: "Recruiter", queries_24h: 218, avg_similarity: 0.71, avg_latency_ms: 140, cache_hit_rate: 38 },
  { agent: "Compliance", queries_24h: 89, avg_similarity: 0.85, avg_latency_ms: 110, cache_hit_rate: 55 },
];

export function RAGMonitor() {
  const totalDocs = MOCK_AGENTS.reduce((a, b) => a + b.doc_count, 0);
  const totalChunks = MOCK_AGENTS.reduce((a, b) => a + b.chunk_count, 0);
  const totalChars = MOCK_AGENTS.reduce((a, b) => a + b.total_chars, 0);
  const totalQueries = QUERY_STATS.reduce((a, b) => a + b.queries_24h, 0);
  const avgLatency = Math.round(QUERY_STATS.reduce((a, b) => a + b.avg_latency_ms, 0) / QUERY_STATS.length);

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: "Documentos Totales", value: totalDocs.toLocaleString(), icon: FileText, color: "text-primary" },
          { label: "Chunks Indexados", value: totalChunks.toLocaleString(), icon: Layers, color: "text-indigo-500" },
          { label: "Consultas en 24h", value: totalQueries.toLocaleString(), icon: Search, color: "text-blue-500" },
          { label: "Latencia Media RAG", value: `${avgLatency}ms`, icon: Clock, color: "text-emerald-500" },
        ].map(kpi => (
          <Card key={kpi.label} className="glass shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-medium text-muted-foreground">{kpi.label}</CardTitle>
              <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{kpi.value}</div>
              <p className="text-[10px] text-muted-foreground mt-1">Total acumulado</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Agent Knowledge Bases */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              Bases de Conocimiento por Agente
            </CardTitle>
            <CardDescription>Documentos y chunks indexados en RAG</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {MOCK_AGENTS.map(agent => {
              const maxDocs = MOCK_AGENTS.reduce((a, b) => Math.max(a, b.doc_count), 0);
              const maxChunks = MOCK_AGENTS.reduce((a, b) => Math.max(a, b.chunk_count), 0);
              const avgCharsPerDoc = agent.total_chars / Math.max(agent.doc_count, 1);
              const lastIndexed = new Date(agent.last_indexed);
              const hoursAgo = Math.round((MOCK_NOW_TS - lastIndexed.getTime()) / 3600000);

              return (
                <div key={agent.id} className="p-3 rounded-xl bg-muted/10 border border-border/30 hover:border-border/60 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                        <Brain className="h-3.5 w-3.5" />
                      </div>
                      <span className="text-sm font-bold">{agent.name}</span>
                    </div>
                    <Badge variant="outline" className="text-[10px]">{agent.embedding_model}</Badge>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground w-20">Documentos</span>
                      <div className="flex-1 h-1.5 bg-muted/30 rounded-full overflow-hidden">
                        <div className="h-full bg-primary rounded-full" style={{ width: `${(agent.doc_count / maxDocs) * 100}%` }} />
                      </div>
                      <span className="text-[10px] font-bold text-muted-foreground w-8 text-right">{agent.doc_count}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground w-20">Chunks</span>
                      <div className="flex-1 h-1.5 bg-muted/30 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${(agent.chunk_count / maxChunks) * 100}%` }} />
                      </div>
                      <span className="text-[10px] font-bold text-muted-foreground w-8 text-right">{agent.chunk_count}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-[10px] text-muted-foreground">
                    <span>~{Math.round(avgCharsPerDoc / 1000)}K chars/doc</span>
                    <span>{hoursAgo}h desde último indexado</span>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Query Performance */}
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Activity className="h-5 w-5 text-amber-500" />
              Rendimiento de Consultas RAG
            </CardTitle>
            <CardDescription>Métricas de búsqueda semántica en 24h</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {QUERY_STATS.map(stat => (
              <div key={stat.agent} className="p-3 rounded-xl bg-muted/10 border border-border/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold">{stat.agent}</span>
                  <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px] font-bold">{stat.queries_24h} consultas</Badge>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center p-2 rounded-lg bg-background/50">
                    <p className="text-lg font-extrabold">{(stat.avg_similarity * 100).toFixed(0)}%</p>
                    <p className="text-[9px] text-muted-foreground">Similitud media</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-background/50">
                    <p className="text-lg font-extrabold">{stat.avg_latency_ms}ms</p>
                    <p className="text-[9px] text-muted-foreground">Latencia</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-background/50">
                    <p className="text-lg font-extrabold">{stat.cache_hit_rate}%</p>
                    <p className="text-[9px] text-muted-foreground">Cache hits</p>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Health Status */}
      <Card className="glass border-emerald-500/20 bg-emerald-500/5">
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            <div>
              <p className="text-sm font-bold">RAG Service — Operativo</p>
              <p className="text-xs text-muted-foreground">
                {totalDocs} documentos en {MOCK_AGENTS.length} agentes. Embeddings actualizados.
              </p>
            </div>
          </div>
          <Button variant="outline" size="xs" className="gap-1.5" onClick={() => toast.success("Índice regenerado")}>
            <RefreshCw className="h-3.5 w-3.5" /> Reindexar Todo
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
