"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  Search, BookOpen, Tag, ThumbsUp, Eye, Plus, Trash2, ChevronDown,
  ChevronUp, Sparkles, AlertCircle, Loader2, ExternalLink, Filter, X,
  CheckCircle2
} from "lucide-react";
import { toast } from "sonner";

interface KBArticle {
  id: string;
  title: string;
  problem_description: string | null;
  symptoms: string[];
  root_cause: string | null;
  resolution_steps: string[];
  prevention_tips: string[];
  category: string;
  tags: string[];
  source_ticket_id: string | null;
  author: string | null;
  view_count: number;
  helpful_count: number;
  created_at: string;
}

interface KBData {
  articles: KBArticle[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface TagsData {
  tags: { name: string; count: number }[];
  categories: string[];
}

export function ITKBBrowser() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [expandedArticle, setExpandedArticle] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [page, setPage] = useState(1);

  const { data: articlesData, isLoading, error } = useQuery<KBData>({
    queryKey: ["kb-articles", page, categoryFilter],
    queryFn: () =>
      fetchClient(`/it/kb/articles?page=${page}&page_size=20${categoryFilter ? `&category=${encodeURIComponent(categoryFilter)}` : ""}`).then(r => r),
  });

  const { data: tagsData } = useQuery<TagsData>({
    queryKey: ["kb-tags"],
    queryFn: () => fetchClient("/it/kb/tags").then(r => r),
  });

  const searchMutation = useMutation({
    mutationFn: (query: string) => fetchClient(`/it/kb/search?query=${encodeURIComponent(query)}&top_k=10`).then(r => r),
  });

  const helpfulMutation = useMutation({
    mutationFn: (articleId: string) => fetchClient(`/it/kb/articles/${articleId}/helpful`, { method: "POST" }).then(r => r),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-articles"] });
      toast.success("¡Gracias por tu feedback!");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (articleId: string) => fetchClient(`/it/kb/articles/${articleId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-articles"] });
      toast.success("Artículo eliminado");
    },
  });

  const articles = articlesData?.articles || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary" />
            Base de Conocimiento IT
          </h3>
          <p className="text-sm text-muted-foreground">
            {articlesData?.total || 0} artículos disponibles
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger render={<Button size="sm" className="gap-1.5"><Plus className="h-4 w-4" /> Nuevo Artículo</Button>} />
          <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Crear Artículo KB</DialogTitle>
            </DialogHeader>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              await fetchClient("/it/kb/articles", {
                method: "POST",
                body: JSON.stringify({
                  title: fd.get("title"),
                  problem_description: fd.get("problem_description"),
                  root_cause: fd.get("root_cause"),
                  resolution_steps: (fd.get("resolution_steps") as string).split("\n").filter(Boolean),
                  symptoms: (fd.get("symptoms") as string).split("\n").filter(Boolean),
                  category: fd.get("category") || "general",
                  tags: (fd.get("tags") as string).split(",").map(t => t.trim()).filter(Boolean),
                }),
              }).then(r => r);
              queryClient.invalidateQueries({ queryKey: ["kb-articles"] });
              setIsCreateOpen(false);
              toast.success("Artículo creado");
            }} className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Título</Label>
                <Input name="title" className="bg-card/60" required />
              </div>
              <div className="space-y-2">
                <Label>Descripción del problema</Label>
                <Textarea name="problem_description" className="bg-card/60 h-20" />
              </div>
              <div className="space-y-2">
                <Label>Causa raíz</Label>
                <Input name="root_cause" className="bg-card/60" />
              </div>
              <div className="space-y-2">
                <Label>Pasos de resolución (uno por línea)</Label>
                <Textarea name="resolution_steps" className="bg-card/60 h-20" placeholder="1. Verificar conexión..." />
              </div>
              <div className="space-y-2">
                <Label>Síntomas (uno por línea)</Label>
                <Textarea name="symptoms" className="bg-card/60 h-16" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Categoría</Label>
                  <Input name="category" className="bg-card/60" placeholder="hardware, software, network..." />
                </div>
                <div className="space-y-2">
                  <Label>Tags (separados por coma)</Label>
                  <Input name="tags" className="bg-card/60" placeholder="wifi, vpn, printer..." />
                </div>
              </div>
              <Button type="submit" className="w-full gap-2">Crear Artículo</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 bg-card/60"
            placeholder="Buscar en la base de conocimiento..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && searchQuery.trim()) searchMutation.mutate(searchQuery); }}
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {tagsData?.categories.map(cat => (
            <Button
              key={cat}
              variant={categoryFilter === cat ? "default" : "outline"}
              size="xs"
              className="text-xs"
              onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
            >
              {cat}
            </Button>
          ))}
        </div>
      </div>

      {/* Tag Cloud */}
      {tagsData?.tags && tagsData.tags.length > 0 && (
        <div className="flex gap-1.5 flex-wrap">
          {tagsData.tags.slice(0, 15).map(tag => (
            <button
              key={tag.name}
              onClick={() => setTagFilter(tagFilter === tag.name ? null : tag.name)}
              className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors ${
                tagFilter === tag.name
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {tag.name} <span className="opacity-60">({tag.count})</span>
            </button>
          ))}
        </div>
      )}

      {/* Search Results */}
      {searchMutation.data && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold">Resultados para &quot;{searchQuery}&quot;</h4>
            <Button variant="ghost" size="xs" onClick={() => { searchMutation.reset(); setSearchQuery(""); }}><X className="h-3 w-3 mr-1" /> Limpiar</Button>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {(searchMutation.data as any)?.results?.map((item: any) => (
              <div key={item.document_id} className="p-3 rounded-xl border border-border/40 bg-muted/10">
                <p className="text-sm font-semibold">{item.title || "Artículo KB"}</p>
                <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{item.content}</p>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline" className="text-[10px]">{item.category}</Badge>
                  <span className="text-[10px] text-muted-foreground">{(item.similarity * 100).toFixed(0)}% match</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Articles Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
        </div>
      ) : articles.length === 0 ? (
        <Card className="glass">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center gap-3">
            <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <BookOpen className="w-7 h-7" />
            </div>
            <p className="text-sm font-semibold">Sin artículos</p>
            <p className="text-xs text-muted-foreground max-w-xs">
              {categoryFilter ? "No hay artículos en esta categoría." : "Crea el primer artículo de la base de conocimiento."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {articles.map(article => (
              <Card key={article.id} className="glass shadow-sm hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base font-bold leading-snug">{article.title}</CardTitle>
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => helpfulMutation.mutate(article.id)}
                        className="p-1.5 rounded-lg hover:bg-emerald-500/10 hover:text-emerald-500 transition-colors text-muted-foreground"
                        title="Marcar como útil"
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => { if (confirm("¿Eliminar artículo?")) deleteMutation.mutate(article.id); }}
                        className="p-1.5 rounded-lg hover:bg-rose-500/10 hover:text-rose-500 transition-colors text-muted-foreground"
                        title="Eliminar"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px]">{article.category}</Badge>
                    {article.tags?.slice(0, 3).map(tag => (
                      <Badge key={tag} variant="outline" className="text-[10px]">{tag}</Badge>
                    ))}
                    {article.source_ticket_id && (
                      <Badge variant="outline" className="text-[10px] text-muted-foreground">Ticket #{article.source_ticket_id.slice(0, 8)}</Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{article.problem_description}</p>

                  {expandedArticle === article.id && (
                    <div className="space-y-3 pt-3 border-t border-border/40">
                      {article.symptoms?.length > 0 && (
                        <div className="p-2 rounded-lg bg-amber-500/5 border border-amber-500/10">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-500 mb-1.5">Síntomas</p>
                          <ul className="text-xs space-y-1">
                            {article.symptoms.map((s, i) => <li key={i} className="text-muted-foreground">• {s}</li>)}
                          </ul>
                        </div>
                      )}
                      {article.resolution_steps?.length > 0 && (
                        <div className="p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-500 mb-1.5">Resolución</p>
                          <ol className="text-xs space-y-1 list-decimal list-inside">
                            {article.resolution_steps.map((s, i) => <li key={i} className="text-muted-foreground">{s}</li>)}
                          </ol>
                        </div>
                      )}
                      {article.root_cause && (
                        <div className="p-2 rounded-lg bg-rose-500/5 border border-rose-500/10">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-500 mb-1">Causa Raíz</p>
                          <p className="text-xs text-muted-foreground">{article.root_cause}</p>
                        </div>
                      )}
                      {article.author && (
                        <p className="text-[10px] text-muted-foreground">Autor: {article.author}</p>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1"><Eye className="h-3 w-3" /> {article.view_count}</span>
                      <span className="flex items-center gap-1"><ThumbsUp className="h-3 w-3" /> {article.helpful_count}</span>
                    </div>
                    <button
                      onClick={() => setExpandedArticle(expandedArticle === article.id ? null : article.id)}
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      {expandedArticle === article.id ? (
                        <><ChevronUp className="h-3 w-3" /> Colapsar</>
                      ) : (
                        <><ChevronDown className="h-3 w-3" /> Expandir</>
                      )}
                    </button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {articlesData && articlesData.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" size="xs" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
              <span className="text-xs text-muted-foreground">Pág. {page} de {articlesData.total_pages}</span>
              <Button variant="outline" size="xs" disabled={page >= articlesData.total_pages} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
