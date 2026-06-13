"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchClient } from "@/lib/api/client";
import { HireAPI, type CandidatePool } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Users, Plus, Send, Clock, TrendingUp, Mail, Calendar, Target,
  Sparkles, ChevronRight, CheckCircle2, AlertCircle, Loader2
} from "lucide-react";
import { toast } from "sonner";

interface TalentPool {
  id: string;
  name: string;
  description: string;
  size: number;
  avg_score: number;
  stage_counts: Record<string, number>;
}

interface Campaign {
  id: string;
  name: string;
  type: string;
  status: string;
  audience_size: number;
  open_rate: number;
  created_at: string;
}

const MOCK_POOLS: TalentPool[] = [
  { id: "1", name: "Tech Top Talent", description: "Senior engineers identified for future roles", size: 34, avg_score: 87, stage_counts: { sourced: 20, contacted: 10, engaged: 4 } },
  { id: "2", name: "Sales Leaders Pipeline", description: "Director+ level sales candidates", size: 18, avg_score: 82, stage_counts: { sourced: 12, contacted: 4, engaged: 2 } },
  { id: "3", name: "Graduate Program", description: "University outreach and intern pipeline", size: 56, avg_score: 75, stage_counts: { sourced: 40, contacted: 12, engaged: 4 } },
  { id: "4", name: "Design Talent", description: "UI/UX designers from portfolio review", size: 22, avg_score: 91, stage_counts: { sourced: 15, contacted: 5, engaged: 2 } },
];

const MOCK_CAMPAIGNS: Campaign[] = [
  { id: "c1", name: "Q3 Tech Outreach", type: "email", status: "active", audience_size: 34, open_rate: 62, created_at: "2026-05-15" },
  { id: "c2", name: "Graduate Welcome", type: "email", status: "scheduled", audience_size: 56, open_rate: 0, created_at: "2026-06-01" },
  { id: "c3", name: "Sales Leaders Nudge", type: "linkedin", status: "active", audience_size: 18, open_rate: 45, created_at: "2026-04-20" },
];

export function TalentCRM() {
  const queryClient = useQueryClient();
  const [activeCampaign, setActiveCampaign] = useState<string | null>(null);
  const [newCampaignName, setNewCampaignName] = useState("");
  const [newPoolName, setNewPoolName] = useState("");
  const [newPoolDesc, setNewPoolDesc] = useState("");

  const { data: pools, isLoading } = useQuery({
    queryKey: ["talent-pools"],
    queryFn: () => fetchClient("/hire/pools"),
  });

  const poolList = (pools as any[]) || [];

  const handleCreateCampaign = () => {
    if (!newCampaignName.trim()) return;
    toast.success("Campaign created", { description: `${newCampaignName} scheduled for launch.` });
    setNewCampaignName("");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Talent CRM
          </h3>
          <p className="text-sm text-muted-foreground">Pools de talento y campañas de nurturing</p>
        </div>
        <Button size="sm" className="gap-1.5" onClick={() => toast.info("Usa el gestor de pools debajo para crear y gestionar tus pools de talento.")}>
          <Plus className="h-4 w-4" /> Nuevo Pool
        </Button>
      </div>

      {/* Pools Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {isLoading ? (
          <p className="text-sm text-muted-foreground col-span-2 text-center py-4">Cargando pools...</p>
        ) : poolList.length === 0 ? (
          <div className="col-span-2 flex flex-col items-center justify-center py-8 text-center gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Users className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted-foreground">No hay pools de talento definidos.</p>
            <p className="text-xs text-muted-foreground">Crea un pool para agrupar candidatos por perfil o campaña.</p>
          </div>
        ) : (
          poolList.slice(0, 6).map((pool: any) => (
            <Card key={pool.id} className="glass shadow-sm hover:shadow-md transition-shadow cursor-pointer group">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-semibold">{pool.name}</CardTitle>
                  <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px] font-bold">
                    {pool.candidate_count || 0} candidatos
                  </Badge>
                </div>
                <CardDescription className="text-xs">{pool.description || "Sin descripción"}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Creado: {pool.created_at ? new Date(pool.created_at).toLocaleDateString("es-ES") : "—"}</span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Nurture Campaigns */}
      <Card className="glass">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Mail className="h-5 w-5 text-indigo-500" />
              Campañas de Nurturing
            </CardTitle>
            <CardDescription>Crea secuencias de email para tus pools de talento</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
            <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-500">
              <Mail className="w-6 h-6" />
            </div>
            <p className="text-sm text-muted-foreground">Las campañas de nurturing estarán disponibles próximamente.</p>
            <p className="text-xs text-muted-foreground">Conecta con candidatos pasivos mediante secuencias automatizadas de email.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
