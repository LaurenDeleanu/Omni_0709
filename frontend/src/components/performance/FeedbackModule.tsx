"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  MessageSquare, Plus, Star, Calendar, Clock, CheckCircle2,
  AlertCircle, Send, ChevronRight, Heart, Sparkles, Loader2
} from "lucide-react";
import { toast } from "sonner";

interface OneOnOne {
  id: string;
  employee_name: string;
  employee_id: string;
  scheduled_date: string;
  status: "upcoming" | "completed" | "missed";
  notes: string;
  action_items: { text: string; done: boolean }[];
}

interface FeedbackItem {
  id: string;
  from_name: string;
  to_name: string;
  message: string;
  type: "praise" | "suggestion" | "general";
  created_at: string;
}

const MOCK_ONEONONES: OneOnOne[] = [
  {
    id: "1", employee_name: "Ana García", employee_id: "emp1",
    scheduled_date: "2026-06-14T10:00:00", status: "upcoming",
    notes: "Revisar progreso Q2 OKRs. Discutir necesidades de formación.",
    action_items: [
      { text: "Aprobar presupuesto formación", done: false },
      { text: "Agendar sesión de mentoring", done: true },
      { text: "Revisar KPIs de equipo", done: false },
    ]
  },
  {
    id: "2", employee_name: "Carlos Méndez", employee_id: "emp2",
    scheduled_date: "2026-06-10T11:00:00", status: "completed",
    notes: "1:1 trimestral. Buen desempeño. Solicita más autonomía en decisiones técnicas.",
    action_items: [
      { text: "Delegar revisión de PRs", done: true },
      { text: "Incluir en reuniones de arquitectura", done: true },
    ]
  },
  {
    id: "3", employee_name: "Laura Fernández", employee_id: "emp3",
    scheduled_date: "2026-06-17T14:00:00", status: "upcoming",
    notes: "Preparar evaluación de desempeño semestral. Recopilar feedback de compañeros.",
    action_items: [
      { text: "Solicitar peer feedback", done: false },
      { text: "Preparar agenda de desarrollo", done: false },
    ]
  },
];

const MOCK_FEEDBACK: FeedbackItem[] = [
  { id: "f1", from_name: "Tú", to_name: "Ana García", message: "Excelente presentación en la demo al cliente. Muy clara y bien estructurada.", type: "praise", created_at: "2026-06-08" },
  { id: "f2", from_name: "Carlos Méndez", to_name: "Laura Fernández", message: "Gran trabajo en la optimización del pipeline de CI. Redujiste los tiempos en un 40%.", type: "praise", created_at: "2026-06-07" },
  { id: "f3", from_name: "Tú", to_name: "Carlos Méndez", message: "Sugiero dedicar más tiempo a documentar las decisiones de arquitectura para el equipo.", type: "suggestion", created_at: "2026-06-05" },
  { id: "f4", from_name: "Ana García", to_name: "Tú", message: "Gracias por el apoyo en la resolución del incidente del viernes.", type: "praise", created_at: "2026-06-02" },
];

export function FeedbackModule() {
  const [activeTab, setActiveTab] = useState<"oneonones" | "feedback">("oneonones");
  const [newFeedback, setNewFeedback] = useState("");
  const [selectedRecipient, setSelectedRecipient] = useState("");
  const [selectedType, setSelectedType] = useState<"praise" | "suggestion" | "general">("praise");

  const handleSendFeedback = () => {
    if (!newFeedback.trim()) return;
    toast.success("Feedback enviado", { description: "El feedback se ha compartido de forma privada." });
    setNewFeedback("");
  };

  const toggleActionItem = (oneOnOneId: string, itemIndex: number) => {
    toast.success("Acción actualizada");
  };

  return (
    <div className="space-y-6">
      <Card className="glass">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-primary" />
                Feedback & 1:1s
              </CardTitle>
              <CardDescription>Conversaciones de desarrollo continuo</CardDescription>
            </div>
          </div>
          <div className="flex gap-1 mt-3 p-1 bg-muted/50 rounded-lg">
            <button
              onClick={() => setActiveTab("oneonones")}
              className={`flex-1 py-1.5 px-3 rounded-md text-xs font-bold transition-colors ${
                activeTab === "oneonones" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Calendar className="h-3.5 w-3.5 inline mr-1" /> 1:1s
            </button>
            <button
              onClick={() => setActiveTab("feedback")}
              className={`flex-1 py-1.5 px-3 rounded-md text-xs font-bold transition-colors ${
                activeTab === "feedback" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Heart className="h-3.5 w-3.5 inline mr-1" /> Feedback
            </button>
          </div>
        </CardHeader>

        {activeTab === "oneonones" ? (
          <CardContent className="space-y-3">
            {MOCK_ONEONONES.map(oneonone => (
              <div key={oneonone.id} className="p-4 rounded-xl border border-border/40 hover:bg-muted/20 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold ${
                      oneonone.status === "completed" ? "bg-emerald-500/10 text-emerald-500" :
                      oneonone.status === "upcoming" ? "bg-blue-500/10 text-blue-500" :
                      "bg-slate-500/10 text-slate-500"
                    }`}>
                      {oneonone.employee_name.split(" ").map(n => n[0]).join("").toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{oneonone.employee_name}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {new Date(oneonone.scheduled_date).toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  </div>
                  <Badge className={oneonone.status === "completed"
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] font-bold"
                    : oneonone.status === "upcoming"
                    ? "bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px] font-bold"
                    : "bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] font-bold"
                  }>
                    {oneonone.status === "completed" ? <CheckCircle2 className="w-3 h-3 mr-1" /> : <Clock className="w-3 h-3 mr-1" />}
                    {oneonone.status === "completed" ? "Completado" : oneonone.status === "upcoming" ? "Próximo" : "Perdido"}
                  </Badge>
                </div>

                {oneonone.notes && (
                  <p className="text-sm text-muted-foreground mt-2 ml-12 italic">&quot;{oneonone.notes}&quot;</p>
                )}

                {oneonone.action_items.length > 0 && (
                  <div className="mt-3 ml-12 space-y-1.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Action Items</p>
                    {oneonone.action_items.map((item, i) => (
                      <div key={i} className="flex items-center gap-2 group">
                        <button
                          onClick={() => toggleActionItem(oneonone.id, i)}
                          className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                            item.done ? "bg-emerald-500 border-emerald-500" : "border-muted-foreground/30 hover:border-primary"
                          }`}
                        >
                          {item.done && <CheckCircle2 className="w-3 h-3 text-white" />}
                        </button>
                        <span className={`text-sm ${item.done ? "line-through text-muted-foreground" : ""}`}>{item.text}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            <Button variant="outline" className="w-full gap-2 mt-2" size="sm">
              <Plus className="h-4 w-4" /> Programar 1:1
            </Button>
          </CardContent>
        ) : (
          <CardContent className="space-y-4">
            {/* Send Feedback */}
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 space-y-3">
              <p className="text-sm font-semibold flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-primary" /> Enviar Feedback
              </p>
              <div className="flex gap-1">
                {(["praise", "suggestion", "general"] as const).map(type => (
                  <button
                    key={type}
                    onClick={() => setSelectedType(type)}
                    className={`px-3 py-1 rounded-full text-xs font-bold transition-colors ${
                      selectedType === type
                        ? type === "praise" ? "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30"
                          : type === "suggestion" ? "bg-amber-500/20 text-amber-500 border border-amber-500/30"
                          : "bg-blue-500/20 text-blue-500 border border-blue-500/30"
                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                    }`}
                  >
                    {type === "praise" ? "🌟 Elogio" : type === "suggestion" ? "💡 Sugerencia" : "💬 General"}
                  </button>
                ))}
              </div>
              <Textarea
                className="bg-card/60 text-sm h-20"
                placeholder="Comparte tu feedback de forma constructiva..."
                value={newFeedback}
                onChange={e => setNewFeedback(e.target.value)}
              />
              <div className="flex justify-end">
                <Button size="sm" className="gap-1.5" onClick={handleSendFeedback}>
                  <Send className="h-3.5 w-3.5" /> Enviar
                </Button>
              </div>
            </div>

            {/* Feedback Feed */}
            <div className="space-y-3">
              {MOCK_FEEDBACK.map(fb => (
                <div key={fb.id} className="p-3 rounded-xl bg-muted/20 border border-border/30">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{fb.from_name}</span>
                      <ChevronRight className="h-3 w-3 text-muted-foreground" />
                      <span className="text-sm font-semibold">{fb.to_name}</span>
                    </div>
                    <Badge className={
                      fb.type === "praise" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px]" :
                      fb.type === "suggestion" ? "bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px]" :
                      "bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px]"
                    }>
                      {fb.type === "praise" ? "🌟 Elogio" : fb.type === "suggestion" ? "💡 Sugerencia" : "💬 General"}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{fb.message}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">{fb.created_at}</p>
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
