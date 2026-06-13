"use client";

import { useEffect, useState } from "react";
import { Award, User, Send, Heart, HeartOff, Sparkles, Smile, Target, Compass, Gift } from "lucide-react";
import { KudosAPI, UserAPI, Employee, Kudos } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

const BADGES = [
  { name: "Team Player", icon: Compass, color: "from-blue-600 to-indigo-600 bg-blue-500/10 text-blue-500 border-blue-500/20", desc: "Gran compañero y colaborador" },
  { name: "Above & Beyond", icon: Sparkles, color: "from-amber-500 to-orange-600 bg-amber-500/10 text-amber-500 border-amber-500/20", desc: "Supera todas las expectativas" },
  { name: "Innovation Hero", icon: Target, color: "from-violet-600 to-purple-600 bg-violet-500/10 text-violet-500 border-violet-500/20", desc: "Ideas creativas y soluciones innovadoras" },
  { name: "Leadership", icon: Smile, color: "from-emerald-600 to-teal-600 bg-emerald-500/10 text-emerald-500 border-emerald-500/20", desc: "Guía y motivación constante" },
  { name: "Customer Champion", icon: Gift, color: "from-rose-600 to-pink-600 bg-rose-500/10 text-rose-500 border-rose-500/20", desc: "Excelente trato y pasión por el cliente" }
];

export default function KudosWallPage() {
  const { user } = useUser();
  
  // Kudos Wall State
  const [feed, setFeed] = useState<Kudos[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Send Kudos State
  const [showModal, setShowModal] = useState(false);
  const [selectedReceiver, setSelectedReceiver] = useState("");
  const [selectedBadge, setSelectedBadge] = useState("Team Player");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Reaction state (Local simulator for wow effect)
  const [reactions, setReactions] = useState<Record<string, number>>({});

  useEffect(() => {
    // Load Feed
    KudosAPI.getFeed()
      .then(setFeed)
      .catch((err) => console.error("Error loading kudos:", err))
      .finally(() => setLoading(false));

    // Load Employees for autocomplete
    UserAPI.getEmployees()
      .then((data: any) => setEmployees(data))
      .catch((err) => console.error("Error loading employees:", err));
  }, []);

  const handleSendKudos = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReceiver || !message) return;
    
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const newKudos = await KudosAPI.sendKudos({
        receiver_id: selectedReceiver,
        message,
        badge: selectedBadge
      });

      // Insert at top of feed
      setFeed((prev) => [newKudos, ...prev]);
      
      // Reset form
      setMessage("");
      setSelectedReceiver("");
      setSelectedBadge("Team Player");
      setShowModal(false);
    } catch (err: any) {
      setErrorMessage(err?.message || "No se pudo enviar el Kudos. Por favor, inténtalo de nuevo.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const incrementReaction = (kudosId: string) => {
    setReactions((prev) => ({
      ...prev,
      [kudosId]: (prev[kudosId] || 0) + 1
    }));
  };

  const getBadgeIcon = (badgeName: string) => {
    const found = BADGES.find((b) => b.name === badgeName);
    return found ? found.icon : Award;
  };

  const getBadgeColors = (badgeName: string) => {
    const found = BADGES.find((b) => b.name === badgeName);
    return found ? found.color : "from-indigo-600 to-indigo-600 bg-indigo-500/10 text-indigo-500 border-indigo-500/20";
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Upper Jumbotron */}
      <div className="relative overflow-hidden rounded-3xl border border-border/40 bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950 p-8 md:p-10 shadow-lg text-white">
        <div className="absolute right-0 top-0 translate-x-12 -translate-y-12 w-64 h-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 w-fit">
              <Sparkles className="h-3 w-3" /> Reconocimiento y Cultura
            </span>
            <h2 className="text-3xl font-bold tracking-tight">Kudos Wall</h2>
            <p className="text-indigo-200 text-sm max-w-md">
              Agradece el gran trabajo de tus compañeros y destaca sus valores en el feed oficial de la compañía.
            </p>
          </div>
          
          <Button
            onClick={() => setShowModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-xl shadow-indigo-600/20 px-6 h-12 rounded-xl font-bold text-sm flex items-center gap-2"
          >
            <Send className="h-4 w-4" />
            Enviar un Kudos
          </Button>
        </div>
      </div>

      <InlineCopilot
        moduleContext="kudos"
        placeholder="Pregunta sobre reconocimientos y cultura..."
        quickActions={[
          { label: "Ver top empleados reconocidos", message: "Ver top empleados reconocidos" },
          { label: "Analizar tendencias de reconocimiento", message: "Analizar tendencias de reconocimiento" },
          { label: "Sugerir empleados para reconocer", message: "Sugerir empleados para reconocer" },
          { label: "Generar resumen de cultura", message: "Generar resumen de cultura" },
        ]}
      />

      {/* Main Feed List */}
      <div className="space-y-4">
        {loading ? (
          <div className="flex items-center justify-center min-h-[40vh]">
            <div className="text-center space-y-2">
              <div className="h-8 w-8 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin mx-auto" />
              <p className="text-muted-foreground text-sm font-medium">Cargando muro de reconocimientos...</p>
            </div>
          </div>
        ) : feed.length === 0 ? (
          <div className="text-center py-16 px-4 bg-muted/20 border border-border/40 rounded-2xl flex flex-col items-center justify-center space-y-3">
            <Award className="h-10 w-10 text-muted-foreground/60" />
            <h3 className="text-lg font-bold text-foreground">El Muro está de estreno</h3>
            <p className="text-sm text-muted-foreground max-w-[280px]">Sé el primero en agradecer a un compañero por su excelente contribución.</p>
            <Button onClick={() => setShowModal(true)} className="bg-indigo-600 hover:bg-indigo-700 font-semibold">Enviar el primer Kudos</Button>
          </div>
        ) : (
          <div className="grid gap-4">
            {feed.map((k) => {
              const BadgeIcon = getBadgeIcon(k.badge);
              const badgeColors = getBadgeColors(k.badge);
              const reactionCount = reactions[k.id] || 0;

              return (
                <Card key={k.id} className="glass hover:shadow-lg transition-all duration-300 overflow-hidden">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      {/* Sender and Receiver information */}
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-indigo-100 dark:bg-indigo-950/30 flex items-center justify-center text-indigo-600 font-bold border border-indigo-200/50">
                          {k.sender?.full_name ? k.sender.full_name.split(" ").map((n) => n[0]).slice(0,2).join("").toUpperCase() : "U"}
                        </div>
                        <div className="flex items-center gap-1.5 text-sm">
                          <span className="font-bold text-foreground">{k.sender?.full_name || k.sender_id}</span>
                          <span className="text-muted-foreground font-medium text-xs">reconoció a</span>
                          <span className="font-bold text-foreground">{k.receiver?.full_name || k.receiver_id}</span>
                        </div>
                      </div>

                      {/* Branded Value Badge */}
                      <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${badgeColors}`}>
                        <BadgeIcon className="h-3.5 w-3.5" />
                        {k.badge}
                      </span>
                    </div>

                    {/* Gratitude message */}
                    <div className="bg-muted/30 p-4 rounded-xl border border-border/40 text-sm text-foreground italic leading-relaxed break-words font-medium">
                      "{k.message}"
                    </div>

                    {/* Footer Interactions */}
                    <div className="flex items-center justify-between gap-4 text-xs text-muted-foreground border-t border-border/40 pt-3">
                      <span>{new Date(k.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                      
                      <button
                        onClick={() => incrementReaction(k.id)}
                        className={`flex items-center gap-1.5 py-1 px-3 rounded-full font-bold border transition-all duration-150 active:scale-90 ${
                          reactionCount > 0
                            ? "bg-rose-500/10 text-rose-500 border-rose-500/20"
                            : "hover:bg-muted/80 text-muted-foreground border-border/60 hover:text-foreground"
                        }`}
                      >
                        <Heart className={`h-4 w-4 ${reactionCount > 0 ? "fill-rose-500 text-rose-500" : ""}`} />
                        <span>Me encanta</span>
                        {reactionCount > 0 && <span className="ml-0.5 bg-rose-500 text-white rounded-full px-1.5 text-[9px]">{reactionCount}</span>}
                      </button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Creation Modal Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <Card className="w-full max-w-lg shadow-2xl glass animate-in zoom-in-95 duration-200 relative overflow-hidden">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl font-bold"><Award className="text-indigo-600 h-5 w-5" /> Enviar un Kudos de Agradecimiento</CardTitle>
              <CardDescription>Destaca los logros o el compañerismo de tus colegas.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSendKudos} className="space-y-4">
                {/* Receiver Select dropdown */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">¿A quién deseas agradecer?</label>
                  <select
                    required
                    value={selectedReceiver}
                    onChange={(e) => setSelectedReceiver(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="" disabled>Selecciona un compañero...</option>
                    {employees
                      .filter((emp) => emp.id !== user?.id)
                      .map((emp) => (
                        <option key={emp.id} value={emp.id}>{emp.full_name || emp.email}</option>
                      ))}
                  </select>
                </div>

                {/* Badge Grid Picker */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Elige el valor / medalla de reconocimiento</label>
                  <div className="grid grid-cols-2 gap-2">
                    {BADGES.map((b) => {
                      const BIcon = b.icon;
                      const isSelected = selectedBadge === b.name;
                      return (
                        <button
                          key={b.name}
                          type="button"
                          onClick={() => setSelectedBadge(b.name)}
                          className={`p-2.5 text-left border rounded-xl flex items-center gap-2.5 transition-all text-xs ${
                            isSelected
                              ? "bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-600/10 font-bold scale-[1.02]"
                              : "bg-card hover:bg-muted/40 border-border/80 text-foreground"
                          }`}
                        >
                          <BIcon className="h-4.5 w-4.5" />
                          <div className="leading-tight">
                            <p className="font-semibold">{b.name}</p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Personalized Message Input */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Escribe tu mensaje personalizado</label>
                  <textarea
                    required
                    rows={4}
                    placeholder="Ej. Muchas gracias por quedarte ayer a ayudarme a depurar el servidor, ¡tu apoyo fue clave para lanzar la actualización!"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1"
                  />
                </div>

                {errorMessage && <p className="text-xs text-rose-500 font-semibold">{errorMessage}</p>}

                {/* Action Buttons */}
                <div className="flex gap-2 justify-end pt-3">
                  <Button type="button" variant="outline" onClick={() => setShowModal(false)}>
                    Cancelar
                  </Button>
                  <Button type="submit" disabled={isSubmitting} className="bg-indigo-600 hover:bg-indigo-700 font-semibold">
                    {isSubmitting ? "Enviando..." : "Enviar Reconocimiento"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
