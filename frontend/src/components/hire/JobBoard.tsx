"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Briefcase, MapPin, Building, Clock, Search, ExternalLink,
  Sparkles, ChevronRight, Loader2, AlertCircle, Globe, Code, Copy
} from "lucide-react";
import { Link } from "@/i18n/routing";
import { toast } from "sonner";

interface PublicJob {
  id: string;
  title: string;
  department: string | null;
  location: string | null;
  employment_type: string | null;
  description: string | null;
  posted_at: string | null;
  status: string;
}

const DEPT_COLORS: Record<string, string> = {
  "Engineering": "from-cyan-500/20 to-blue-500/20 border-cyan-500/30",
  "HR": "from-purple-500/20 to-pink-500/20 border-purple-500/30",
  "Sales": "from-amber-500/20 to-orange-500/20 border-amber-500/30",
  "Finance": "from-emerald-500/20 to-teal-500/20 border-emerald-500/30",
  "Marketing": "from-rose-500/20 to-pink-500/20 border-rose-500/30",
  "IT": "from-indigo-500/20 to-violet-500/20 border-indigo-500/30",
  "Operations": "from-slate-500/20 to-zinc-500/20 border-slate-500/30",
};

export function JobBoard() {
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState<string | null>(null);
  const [locFilter, setLocFilter] = useState<string | null>(null);

  const { data: rawJobs, isLoading, error } = useQuery<PublicJob[]>({
    queryKey: ["public-jobs"],
    queryFn: () => fetchClient("/hire/public/jobs"),
  });

  const departs = [...new Set(rawJobs?.map(j => j.department).filter(Boolean) || [])];
  const locs = [...new Set(rawJobs?.map(j => j.location).filter(Boolean) || [])];

  const filteredJobs = (rawJobs || []).filter(j => {
    const matchesSearch = !search || j.title.toLowerCase().includes(search.toLowerCase()) || (j.description || "").toLowerCase().includes(search.toLowerCase());
    const matchesDept = !deptFilter || j.department === deptFilter;
    const matchesLoc = !locFilter || j.location === locFilter;
    return matchesSearch && matchesDept && matchesLoc;
  });

  const xmlFeedUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/api/v1/hire/public/jobs/feed.xml`;

  const copyXmlUrl = () => {
    navigator.clipboard.writeText(xmlFeedUrl);
    toast.success("XML feed URL copiada", { description: "Pega esta URL en portales de empleo compatibles." });
  };

  if (isLoading) {
    return (
      <Card className="glass">
        <CardHeader><Skeleton className="h-6 w-48" /></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="glass">
        <CardContent className="flex items-center gap-3 py-4">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-muted-foreground">No hay vacantes públicas disponibles.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hero Card */}
      <Card className="glass overflow-hidden relative bg-gradient-to-br from-primary/5 via-background to-indigo-500/5">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl -mr-24 -mt-24" />
        <CardContent className="p-8 relative z-10">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-xs font-bold">
                <Sparkles className="h-3 w-3 mr-1" /> {(rawJobs?.length || 0)} posiciones abiertas
              </Badge>
              <h2 className="text-2xl font-extrabold tracking-tight">Únete a SuccessCore</h2>
              <p className="text-sm text-muted-foreground max-w-md">
                Estamos construyendo el futuro del trabajo con IA. Explora nuestras oportunidades y forma parte del equipo.
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" className="gap-2" size="sm" onClick={copyXmlUrl}>
                <Code className="h-4 w-4" /> Copiar XML Feed
              </Button>
              <Link href={xmlFeedUrl} target="_blank">
                <Button variant="outline" className="gap-2" size="sm">
                  <Globe className="h-4 w-4" /> Ver XML
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 bg-card/60"
            placeholder="Buscar por título o descripción..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {departs.map(dept => (
            <Button
              key={dept}
              variant={deptFilter === dept ? "default" : "outline"}
              size="xs"
              className="text-xs"
              onClick={() => setDeptFilter(deptFilter === dept ? null : dept)}
            >
              <Building className="h-3 w-3 mr-1" /> {dept}
            </Button>
          ))}
          {locs.map(loc => (
            <Button
              key={loc}
              variant={locFilter === loc ? "default" : "outline"}
              size="xs"
              className="text-xs"
              onClick={() => setLocFilter(locFilter === loc ? null : loc)}
            >
              <MapPin className="h-3 w-3 mr-1" /> {loc}
            </Button>
          ))}
        </div>
      </div>

      {/* Jobs Grid */}
      {filteredJobs.length === 0 ? (
        <Card className="glass">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center gap-3">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Briefcase className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold">No hay vacantes activas</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              {rawJobs?.length ? "No se encontraron resultados con los filtros actuales." : "No hay posiciones abiertas en este momento. Vuelve pronto."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredJobs.map(job => (
            <Card key={job.id} className={`glass shadow-sm hover:shadow-md transition-shadow cursor-pointer group bg-gradient-to-br ${DEPT_COLORS[job.department || ""] || "from-slate-500/20 to-zinc-500/20 border-slate-500/30"}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-bold">{job.title}</CardTitle>
                <CardDescription className="text-xs line-clamp-2">{job.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {job.department && (
                    <Badge variant="outline" className="text-[10px] flex items-center gap-1">
                      <Building className="h-2.5 w-2.5" /> {job.department}
                    </Badge>
                  )}
                  {job.location && (
                    <Badge variant="outline" className="text-[10px] flex items-center gap-1">
                      <MapPin className="h-2.5 w-2.5" /> {job.location}
                    </Badge>
                  )}
                  {job.employment_type && (
                    <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px] flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5" /> {job.employment_type}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">
                    {job.posted_at ? new Date(job.posted_at).toLocaleDateString("es-ES") : "—"}
                  </span>
                  <Button variant="ghost" size="xs" className="text-xs gap-1">
                    Ver detalle <ExternalLink className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
