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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  Users, Plus, Trash2, Sparkles, Loader2, AlertCircle,
  ChevronRight, CheckCircle2
} from "lucide-react";
import { toast } from "sonner";

export function CandidatePoolManager() {
  const queryClient = useQueryClient();
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data: pools, isLoading, error } = useQuery({
    queryKey: ["talent-pools"],
    queryFn: () => fetchClient("/hire/pools"),
  });

  const poolList = (pools as any[]) || [];

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      fetchClient("/hire/pools", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["talent-pools"] });
      setIsCreateOpen(false);
      setNewName("");
      setNewDesc("");
      toast.success("Pool creado");
    },
    onError: () => toast.error("Error al crear el pool"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => fetchClient(`/hire/pools/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["talent-pools"] });
      toast.success("Pool eliminado");
    },
    onError: () => toast.error("Error al eliminar"),
  });

  const handleCreate = () => {
    if (!newName.trim()) return;
    createMutation.mutate({ name: newName.trim(), description: newDesc.trim() });
  };

  return (
    <Card className="glass">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Pools de Talento
          </CardTitle>
          <CardDescription>
            {poolList.length} pool{poolList.length !== 1 ? "s" : ""} definido{poolList.length !== 1 ? "s" : ""}
          </CardDescription>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger render={<Button size="sm" className="gap-1.5"><Plus className="h-4 w-4" /> Nuevo Pool</Button>} />
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2"><Users className="h-5 w-5 text-primary" /> Crear Pool de Talento</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider">Nombre</Label>
                <Input className="bg-card/60" value={newName} onChange={e => setNewName(e.target.value)} placeholder="Ej: Senior Engineers Pipeline" />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-wider">Descripción</Label>
                <Textarea className="bg-card/60 h-16" value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Describe el objetivo de este pool..." />
              </div>
              <Button className="w-full gap-2" onClick={handleCreate} disabled={createMutation.isPending || !newName.trim()}>
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                {createMutation.isPending ? "Creando..." : "Crear Pool"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground text-center py-8">Cargando pools...</p>
        ) : error ? (
          <div className="flex items-center gap-3 py-4 text-sm text-destructive">
            <AlertCircle className="h-5 w-5 shrink-0" />
            Error al cargar pools.
          </div>
        ) : poolList.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Users className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted-foreground">No hay pools definidos.</p>
            <p className="text-xs text-muted-foreground">Crea pools para organizar candidatos por perfil, campaña o Skills Cloud.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {poolList.map((pool: any) => (
              <div key={pool.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-muted/30 transition-colors border border-border/30 group">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
                    <Users className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-bold truncate">{pool.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{pool.description || "Sin descripción"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px] font-bold">
                    {pool.candidate_count || 0}
                  </Badge>
                  <Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => { if (confirm(`¿Eliminar pool "${pool.name}"?`)) deleteMutation.mutate(pool.id); }}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                  <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
