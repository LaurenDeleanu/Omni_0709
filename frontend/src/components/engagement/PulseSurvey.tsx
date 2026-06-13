"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Heart, Smile, Frown, Meh, TrendingUp, TrendingDown, Activity,
  Sparkles, CheckCircle2, AlertCircle, Send, ChevronRight,
  BarChart3, PieChart, Target
} from "lucide-react";
import { toast } from "sonner";

const MOODS = [
  { value: 5, emoji: "😍", label: "Excelente", color: "bg-emerald-500/10 border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/20" },
  { value: 4, emoji: "😊", label: "Bien", color: "bg-blue-500/10 border-blue-500/30 text-blue-500 hover:bg-blue-500/20" },
  { value: 3, emoji: "😐", label: "Normal", color: "bg-amber-500/10 border-amber-500/30 text-amber-500 hover:bg-amber-500/20" },
  { value: 2, emoji: "😕", label: "Regular", color: "bg-orange-500/10 border-orange-500/30 text-orange-500 hover:bg-orange-500/20" },
  { value: 1, emoji: "😞", label: "Mal", color: "bg-rose-500/10 border-rose-500/30 text-rose-500 hover:bg-rose-500/20" },
];

const QUESTIONS = [
  { id: "mood", text: "¿Cómo te sientes hoy en el trabajo?", type: "mood" as const },
  { id: "energy", text: "¿Cuál es tu nivel de energía?", type: "scale" as const, options: ["Muy baja", "Baja", "Normal", "Alta", "Muy alta"] },
  { id: "focus", text: "¿Te sientes productivo/a hoy?", type: "scale" as const, options: ["Nada", "Poco", "Normal", "Bastante", "Totalmente"] },
  { id: "support", text: "¿Sientes que tienes el apoyo que necesitas?", type: "scale" as const, options: ["Nada", "Poco", "Normal", "Bastante", "Totalmente"] },
];

const TREND_DATA = [
  { week: "S22", avg: 4.2, responses: 34 },
  { week: "S23", avg: 3.9, responses: 38 },
  { week: "S24", avg: 4.1, responses: 41 },
  { week: "S25", avg: 4.3, responses: 36 },
  { week: "S26", avg: 4.4, responses: 45 },
  { week: "S27", avg: 4.0, responses: 42 },
  { week: "S28", avg: 4.5, responses: 47 },
  { week: "S29", avg: 4.6, responses: 51 },
];

const SENTIMENT_THEMES = [
  { theme: "Colaboración en equipo", sentiment: "positive", pct: 78, mentions: 42 },
  { theme: "Equilibrio trabajo-vida", sentiment: "positive", pct: 72, mentions: 38 },
  { theme: "Herramientas y procesos", sentiment: "neutral", pct: 55, mentions: 31 },
  { theme: "Carga de trabajo", sentiment: "negative", pct: 35, mentions: 24 },
  { theme: "Desarrollo profesional", sentiment: "neutral", pct: 62, mentions: 28 },
];

export function PulseSurvey() {
  const [submitted, setSubmitted] = useState(false);
  const [mood, setMood] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [showHistory, setShowHistory] = useState(false);

  const handleSubmit = () => {
    if (!mood) return;
    setSubmitted(true);
    toast.success("¡Gracias por tu feedback!", { description: "Tu respuesta ayuda a mejorar el ambiente de trabajo." });
  };

  const reset = () => {
    setSubmitted(false);
    setMood(null);
    setAnswers({});
  };

  const avgMood = TREND_DATA.length > 0 ? (TREND_DATA.reduce((a, b) => a + b.avg, 0) / TREND_DATA.length).toFixed(1) : "0";
  const maxTrend = Math.max(...TREND_DATA.map(t => t.responses));
  const currentWeek = TREND_DATA[TREND_DATA.length - 1];
  const trend = currentWeek ? (currentWeek.avg >= 4.3 ? "up" : currentWeek.avg >= 4.0 ? "stable" : "down") : "stable";

  return (
    <div className="space-y-6">
      {/* Header KPI */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Mood Medio</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center gap-2">
              {avgMood}/5
              {trend === "up" ? <TrendingUp className="h-5 w-5 text-emerald-500" /> : trend === "down" ? <TrendingDown className="h-5 w-5 text-rose-500" /> : null}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Últimas 8 semanas</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Participación</CardTitle>
            <PieChart className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{TREND_DATA[TREND_DATA.length - 1].responses}</div>
            <p className="text-xs text-muted-foreground mt-1">Respuestas esta semana</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Tendencia</CardTitle>
            <Target className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{trend === "up" ? "↑ Positiva" : trend === "down" ? "↓ Negativa" : "→ Estable"}</div>
            <p className="text-xs text-muted-foreground mt-1">{trend === "up" ? "+0.3" : trend === "down" ? "-0.3" : "+0.0"} vs mes anterior</p>
          </CardContent>
        </Card>
      </div>

      {/* Today's Pulse Check */}
      {!submitted ? (
        <Card className="glass border-primary/20 bg-gradient-to-br from-primary/5 to-background">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              ¿Cómo te sientes hoy?
            </CardTitle>
            <CardDescription>Tu respuesta es anónima y ayuda a mejorar el ambiente laboral</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-5 gap-2">
              {MOODS.map(m => (
                <button
                  key={m.value}
                  onClick={() => setMood(m.value)}
                  className={`p-3 rounded-xl border-2 text-center transition-all hover:scale-105 ${
                    mood === m.value ? `${m.color} border-2 scale-105 shadow-md` : "border-border/40 hover:border-border"
                  }`}
                >
                  <div className="text-3xl mb-1">{m.emoji}</div>
                  <div className="text-[10px] font-semibold">{m.label}</div>
                </button>
              ))}
            </div>

            {mood && (
              <div className="space-y-4 pt-4 border-t border-border/40">
                {QUESTIONS.filter(q => q.id !== "mood").map(q => (
                  <div key={q.id} className="space-y-2">
                    <p className="text-sm font-medium">{q.text}</p>
                    <div className="flex gap-1">
                      {q.options?.map((opt, i) => (
                        <button
                          key={i}
                          onClick={() => setAnswers(prev => ({ ...prev, [q.id]: i + 1 }))}
                          className={`flex-1 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                            answers[q.id] === i + 1
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted/30 text-muted-foreground hover:bg-muted hover:text-foreground"
                          }`}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}

                <Button onClick={handleSubmit} className="w-full gap-2" size="lg">
                  <Send className="h-4 w-4" /> Enviar Respuesta
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="glass border-emerald-500/20 bg-emerald-500/5">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center">
              <CheckCircle2 className="h-8 w-8 text-emerald-500" />
            </div>
            <div>
              <h3 className="text-lg font-bold">¡Gracias por tu feedback!</h3>
              <p className="text-sm text-muted-foreground mt-1">Tu respuesta ha sido registrada de forma anónima.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={reset}>Enviar otra</Button>
              <Button size="sm" onClick={() => setShowHistory(true)}>Ver tendencias</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trend Chart */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-indigo-500" />
            Evolución del Mood
          </CardTitle>
          <CardDescription>Media semanal de respuestas (últimas 8 semanas)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-2 h-40">
            {TREND_DATA.map(week => {
              const height = (week.avg / 5) * 100;
              const barHeight = (week.responses / maxTrend) * 100;
              const barColor = week.avg >= 4.3 ? "bg-emerald-500" : week.avg >= 4.0 ? "bg-blue-500" : week.avg >= 3.5 ? "bg-amber-500" : "bg-rose-500";
              return (
                <div key={week.week} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex flex-col-reverse h-32 gap-[2px]">
                    <div
                      className={`w-full rounded-t-sm transition-all hover:opacity-80 ${barColor}`}
                      style={{ height: `${barHeight}%`, minHeight: "2px", opacity: 0.3 }}
                    />
                    <div
                      className="w-full rounded-t-sm bg-primary/80 transition-all hover:bg-primary"
                      style={{ height: `${((height - barHeight) * 0.3 + barHeight * 0.3)}%`, minHeight: "2px" }}
                    />
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="text-[10px] font-bold">{week.avg}</span>
                    <span className="text-[8px] text-muted-foreground">{week.week}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Sentiment Themes */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <PieChart className="h-5 w-5 text-primary" />
              Temas Recurrentes
            </CardTitle>
            <CardDescription>Análisis de sentimiento en respuestas abiertas</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {SENTIMENT_THEMES.map(theme => (
              <div key={theme.theme} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      theme.sentiment === "positive" ? "bg-emerald-500" :
                      theme.sentiment === "negative" ? "bg-rose-500" : "bg-amber-500"
                    }`} />
                    <span className="text-sm font-medium">{theme.theme}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{theme.mentions} menciones</span>
                </div>
                <Progress value={theme.pct} className="h-1.5" />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Heart className="h-5 w-5 text-rose-500" />
              eNPS del Equipo
            </CardTitle>
            <CardDescription>Employee Net Promoter Score</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-6">
              <div className="text-5xl font-extrabold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent mb-2">+42</div>
              <p className="text-sm text-muted-foreground">eNPS Score</p>
              <div className="flex justify-center gap-4 mt-4">
                <div className="text-center">
                  <div className="text-lg font-bold text-emerald-500">58%</div>
                  <div className="text-[10px] text-muted-foreground">Promotores</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-amber-500">26%</div>
                  <div className="text-[10px] text-muted-foreground">Neutros</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-rose-500">16%</div>
                  <div className="text-[10px] text-muted-foreground">Detractores</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
