"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LegalAPI } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, ShieldAlert, Lock, Fingerprint, EyeOff, FileText, CheckCircle2, Server, Scale, Info } from "lucide-react";
import { toast } from "sonner";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function LegalPage() {
  const { user } = useUser();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"submit" | "track" | "admin" | "gdpr">("submit");
  
  const isHrAdmin = user?.role === "hr_admin" || user?.role === "admin" || user?.role === "legal_manager";

  // Form states
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("fraud");
  const [isAnonymous, setIsAnonymous] = useState(true);
  
  // Track state
  const [trackCode, setTrackCode] = useState("");
  const [trackResult, setTrackResult] = useState<any>(null);
  
  // Queries
  const { data: reports, isLoading: loadingReports } = useQuery({
    queryKey: ["adminReports"],
    queryFn: () => LegalAPI.getReports(),
    enabled: isHrAdmin && activeTab === "admin",
  });

  // Mutations
  const submitMutation = useMutation({
    mutationFn: (data: any) => LegalAPI.createReport(data),
    onSuccess: (res: any) => {
      toast.success("Denuncia enviada", { description: "Guarde su código de seguimiento." });
      setTrackCode(res.tracking_code);
      setActiveTab("track");
      handleTrack(res.tracking_code);
      setTitle("");
      setDescription("");
    },
    onError: () => {
      toast.error("Error", { description: "No se pudo enviar la denuncia." });
    }
  });

  const trackMutation = useMutation({
    mutationFn: (code: string) => LegalAPI.trackReport(code),
    onSuccess: (data) => {
      setTrackResult(data);
    },
    onError: () => {
      toast.error("No encontrado", { description: "Código de seguimiento inválido." });
      setTrackResult(null);
    }
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status, resolution_message }: { id: string, status: string, resolution_message?: string }) => LegalAPI.updateReportStatus(id, status, resolution_message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminReports"] });
      toast.success("Estado actualizado");
    }
  });

  const { data: dsarTickets, isLoading: loadingDsar } = useQuery({
    queryKey: ["dsarTickets"],
    queryFn: () => LegalAPI.getDsarTickets(),
    enabled: isHrAdmin && activeTab === "gdpr",
  });

  const createDsarMutation = useMutation({
    mutationFn: (data: { request_type: string, details?: string }) => LegalAPI.createDsarTicket(data),
    onSuccess: () => {
      toast.success("Solicitud enviada al departamento de datos.");
    }
  });

  const updateDsarStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => LegalAPI.updateDsarStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dsarTickets"] });
      toast.success("Ticket actualizado");
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitMutation.mutate({ title, description, category, is_anonymous: isAnonymous });
  };

  const handleTrack = (code: string) => {
    if (!code) return;
    trackMutation.mutate(code);
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto bg-background/50">
      <div className="max-w-6xl mx-auto space-y-8">
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Legal y Cumplimiento</h1>
            <p className="text-muted-foreground mt-1">Canal Ético y de Denuncias corporativo.</p>
          </div>
        </div>

        <InlineCopilot
          moduleContext="legal"
          placeholder="Pregunta sobre cumplimiento normativo o denuncias..."
          quickActions={[
            { label: "Verificar cumplimiento GDPR", message: "Verificar cumplimiento GDPR" },
            { label: "Consultar normativa aplicable", message: "Consultar normativa aplicable" },
            { label: "Revisar políticas de privacidad", message: "Revisar políticas de privacidad" },
            { label: "Analizar riesgos de compliance", message: "Analizar riesgos de compliance" },
          ]}
        />

        {/* Tabs */}
        <div className="flex space-x-2 border-b border-border/60 pb-2">
          <button 
            onClick={() => setActiveTab("submit")}
            className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${activeTab === "submit" ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
          >
            Nueva Denuncia
          </button>
          <button 
            onClick={() => setActiveTab("track")}
            className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${activeTab === "track" ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
          >
            Seguimiento
          </button>
          {isHrAdmin && (
            <button 
              onClick={() => setActiveTab("admin")}
              className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${activeTab === "admin" ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
            >
              Gestión (Admin)
            </button>
          )}
          <button 
            onClick={() => setActiveTab("gdpr")}
            className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${activeTab === "gdpr" ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
          >
            Privacidad (GDPR)
          </button>
        </div>

        {/* Submit Tab */}
        {activeTab === "submit" && (
          <div className="grid md:grid-cols-5 gap-8">
            <div className="md:col-span-3">
              <Card className="border border-border/50 bg-card/40 backdrop-blur-md shadow-md">
                <CardHeader>
                  <CardTitle className="flex gap-2 items-center"><ShieldAlert className="w-5 h-5 text-red-500" /> Formulario de Denuncia</CardTitle>
                  <CardDescription>La información proporcionada está protegida por la directiva Whistleblower de la UE.</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                      <Label>Categoría</Label>
                      <select 
                        value={category} 
                        onChange={e => setCategory(e.target.value)}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      >
                        <option value="fraud">Fraude o Corrupción</option>
                        <option value="harassment">Acoso o Discriminación</option>
                        <option value="safety">Seguridad y Salud</option>
                        <option value="other">Otro</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label>Asunto</Label>
                      <Input required value={title} onChange={e => setTitle(e.target.value)} placeholder="Breve descripción del incidente" />
                    </div>
                    <div className="space-y-2">
                      <Label>Detalles de la denuncia</Label>
                      <Textarea 
                        required 
                        value={description} 
                        onChange={e => setDescription(e.target.value)} 
                        placeholder="Proporcione todos los detalles posibles (fechas, personas involucradas, evidencias)..."
                        className="min-h-[150px]"
                      />
                    </div>
                    <div className="flex items-center space-x-2 pt-2 border-t border-border/60">
                      <input 
                        type="checkbox" 
                        id="anon" 
                        checked={isAnonymous} 
                        onChange={e => setIsAnonymous(e.target.checked)}
                        className="rounded border-border text-primary focus:ring-primary h-4 w-4"
                      />
                      <label htmlFor="anon" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2">
                        <EyeOff className="w-4 h-4 text-muted-foreground" />
                        Deseo permanecer anónimo (Recomendado)
                      </label>
                    </div>
                    <Button type="submit" disabled={submitMutation.isPending} className="w-full mt-4 bg-red-600 hover:bg-red-700 text-white">
                      {submitMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : "Enviar Denuncia de Forma Segura"}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </div>
            <div className="md:col-span-2 space-y-4">
              <Card className="bg-primary/5 border-primary/20">
                <CardHeader>
                  <CardTitle className="text-sm flex gap-2"><Lock className="w-4 h-4" /> Garantía de Confidencialidad</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-4">
                  <p>Al seleccionar la opción anónima, el sistema <strong>no registra su dirección IP ni asocia su cuenta de usuario</strong> a esta denuncia.</p>
                  <p>Se generará un código de seguimiento cifrado de 10 dígitos que será la única forma de interactuar con el departamento legal sobre este caso.</p>
                </CardContent>
              </Card>

              <Card className="bg-muted/40 border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs flex gap-2 text-muted-foreground uppercase tracking-wider"><Scale className="w-4 h-4" /> Directiva UE 2019/1937</CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground space-y-2">
                  <p>Usted tiene derecho a ser informado sobre el estado de su denuncia en un plazo máximo de <strong>3 meses</strong>. Recibirá un acuse de recibo en los próximos <strong>7 días</strong>.</p>
                  <p>Si considera que los canales internos no han sido eficaces, la ley le ampara para acudir a las autoridades nacionales competentes (e.g., Autoridad Independiente de Protección al Informante).</p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Track Tab */}
        {activeTab === "track" && (
          <Card className="max-w-2xl mx-auto border border-border/50 bg-card/40 backdrop-blur-md shadow-md">
            <CardHeader>
              <CardTitle className="flex gap-2 items-center"><Fingerprint className="w-5 h-5 text-primary" /> Seguimiento de Denuncia</CardTitle>
              <CardDescription>Ingrese su código de 10 dígitos para ver el estado de su reporte.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex gap-2">
                <Input 
                  value={trackCode} 
                  onChange={e => setTrackCode(e.target.value.toUpperCase())} 
                  placeholder="Ej: A8FX92MD1B" 
                  className="font-mono uppercase tracking-widest text-lg"
                  maxLength={10}
                />
                <Button onClick={() => handleTrack(trackCode)} disabled={trackMutation.isPending || trackCode.length < 5}>
                  {trackMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Consultar"}
                </Button>
              </div>

              {trackResult && (
                <div className="mt-8 border border-border/60 rounded-lg p-6 bg-card/80 space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-lg">{trackResult.title}</h3>
                      <p className="text-sm text-muted-foreground">Enviado el {new Date(trackResult.created_at).toLocaleDateString()}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-black uppercase border ${
                      trackResult.status === 'resolved' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      trackResult.status === 'investigating' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                      'bg-blue-500/10 text-blue-400 border-blue-500/20'
                    }`}>
                      {trackResult.status === 'resolved' ? 'Resuelto' : 
                       trackResult.status === 'investigating' ? 'En Investigación' : 'Recibido (Abierto)'}
                    </span>
                  </div>
                  
                  <div className="p-4 bg-muted/30 rounded-md">
                    <p className="text-sm whitespace-pre-wrap">{trackResult.description}</p>
                  </div>

                  {trackResult.resolution_message && (
                    <div className="p-4 bg-primary/5 border border-primary/20 rounded-md">
                      <div className="flex gap-2 items-center mb-2">
                        <Info className="w-4 h-4 text-primary" />
                        <h4 className="text-xs font-bold uppercase tracking-wider text-primary">Mensaje de Resolución (Legal)</h4>
                      </div>
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">{trackResult.resolution_message}</p>
                    </div>
                  )}
                  
                  {trackResult.status === 'investigating' && (
                    <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-md flex gap-3 text-amber-600/90 dark:text-amber-400/90 text-sm">
                      <ShieldAlert className="w-5 h-5 shrink-0" />
                      <p>Su denuncia está siendo analizada por el equipo legal y de cumplimiento. Se están tomando las medidas necesarias.</p>
                    </div>
                  )}
                  {trackResult.status === 'resolved' && (
                    <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-md flex gap-3 text-emerald-600/90 dark:text-emerald-400/90 text-sm">
                      <CheckCircle2 className="w-5 h-5 shrink-0" />
                      <p>El caso ha sido concluido según nuestros protocolos internos. Gracias por ayudar a mantener un entorno seguro.</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Admin Tab */}
        {activeTab === "admin" && isHrAdmin && (
          <Card className="border border-border/50 bg-card/40 backdrop-blur-md shadow-md">
            <CardHeader>
              <CardTitle className="flex gap-2 items-center"><FileText className="w-5 h-5 text-indigo-400" /> Panel de Resoluciones</CardTitle>
              <CardDescription>Gestión exclusiva para responsables de cumplimiento y RRHH.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border border-border/60 rounded-lg overflow-x-auto bg-card/20 shadow-md max-h-[600px] overflow-y-auto">
                {loadingReports ? <div className="text-xs text-muted-foreground p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" /> Cargando denuncias...</div> :
                  reports?.length === 0 ? <div className="text-sm text-muted-foreground p-10 text-center">No hay denuncias registradas en el sistema.</div> :
                  <table className="w-full text-sm text-left border-collapse">
                    <thead className="bg-muted text-muted-foreground border-b border-border/60">
                      <tr>
                        <th className="p-4 font-semibold uppercase tracking-wider text-xs">Código</th>
                        <th className="p-4 font-semibold uppercase tracking-wider text-xs">Fecha</th>
                        <th className="p-4 font-semibold uppercase tracking-wider text-xs">Categoría / Asunto</th>
                        <th className="p-4 font-semibold uppercase tracking-wider text-xs">Anonimato</th>
                        <th className="p-4 text-center font-semibold uppercase tracking-wider text-xs">Estado</th>
                        <th className="p-4 text-right font-semibold uppercase tracking-wider text-xs">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {reports?.map((r: any) => (
                        <tr key={r.id} className="hover:bg-muted/15 transition-colors group">
                          <td className="p-4 font-mono font-bold text-foreground text-xs">{r.tracking_code}</td>
                          <td className="p-4 text-muted-foreground text-xs">{new Date(r.created_at).toLocaleDateString()}</td>
                          <td className="p-4">
                            <div className="font-semibold">{r.title}</div>
                            <div className="text-xs text-muted-foreground uppercase tracking-wider mt-0.5">{r.category}</div>
                          </td>
                          <td className="p-4">
                            {r.is_anonymous ? 
                              <span className="text-xs flex items-center gap-1 text-emerald-500"><EyeOff className="w-3 h-3" /> Anónimo</span> : 
                              <span className="text-xs flex items-center gap-1 text-amber-500">Público</span>
                            }
                          </td>
                          <td className="p-4 text-center">
                            <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${
                              r.status === 'resolved' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                              r.status === 'investigating' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                              'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            }`}>
                              {r.status === 'resolved' ? 'Resuelto' : r.status === 'investigating' ? 'Investigando' : 'Abierto'}
                            </span>
                          </td>
                          <td className="p-4 text-right">
                            <select
                              value={r.status}
                              onChange={(e) => {
                                const newStatus = e.target.value;
                                let msg = undefined;
                                if (newStatus !== 'open') {
                                  msg = window.prompt("Ingrese el mensaje de actualización/resolución para el denunciante (Obligatorio bajo norma UE de los 3 meses):") || undefined;
                                }
                                updateStatusMutation.mutate({ id: r.id, status: newStatus, resolution_message: msg });
                              }}
                              disabled={updateStatusMutation.isPending}
                              className="text-xs rounded border border-border/80 bg-card px-2.5 py-1 text-foreground focus:ring-1 focus:ring-primary focus:outline-none cursor-pointer"
                            >
                              <option value="open">Marcar como Abierto</option>
                              <option value="investigating">Marcar en Investigación</option>
                              <option value="resolved">Marcar como Resuelto</option>
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                }
              </div>
            </CardContent>
          </Card>
        )}

      </div>

        {/* GDPR Tab */}
        {activeTab === "gdpr" && (
          <div className="space-y-8">
            <Card className="border border-border/50 bg-card/40 backdrop-blur-md shadow-md">
              <CardHeader>
                <CardTitle className="flex gap-2 items-center"><Server className="w-5 h-5 text-primary" /> Centro de Privacidad y Derechos ARCO</CardTitle>
                <CardDescription>Gestione sus datos personales de acuerdo con el Reglamento General de Protección de Datos (RGPD).</CardDescription>
              </CardHeader>
              <CardContent className="grid md:grid-cols-2 gap-6">
                <div className="p-6 border border-border/60 rounded-lg space-y-4 bg-muted/20">
                  <div>
                    <h3 className="font-semibold mb-1">Derecho de Acceso</h3>
                    <p className="text-sm text-muted-foreground">Solicite una copia completa de todos los datos personales, evaluaciones y registros que la empresa mantiene sobre usted.</p>
                  </div>
                  <Button 
                    variant="outline" 
                    onClick={() => createDsarMutation.mutate({ request_type: "download_data", details: "Employee requested data copy." })}
                    disabled={createDsarMutation.isPending}
                  >
                    Solicitar Copia de Datos (DSAR)
                  </Button>
                </div>
                
                <div className="p-6 border border-red-500/20 rounded-lg space-y-4 bg-red-500/5">
                  <div>
                    <h3 className="font-semibold text-red-600 dark:text-red-400 mb-1">Derecho al Olvido</h3>
                    <p className="text-sm text-muted-foreground">Solicite la eliminación permanente de sus datos no esenciales o cuenta de la plataforma. Sujeto a retención legal por nóminas/impuestos.</p>
                  </div>
                  <Button 
                    variant="destructive"
                    onClick={() => {
                      if(window.confirm("¿Está seguro de que desea enviar una solicitud de eliminación de datos? RRHH evaluará la petición.")) {
                        createDsarMutation.mutate({ request_type: "delete_data", details: "Employee requested account deletion." });
                      }
                    }}
                    disabled={createDsarMutation.isPending}
                  >
                    Solicitar Eliminación
                  </Button>
                </div>
              </CardContent>
            </Card>

            {isHrAdmin && (
              <Card className="border border-border/50 bg-card/40 shadow-md">
                <CardHeader>
                  <CardTitle className="text-lg">Gestión de Solicitudes DSAR (Admins)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="border border-border/60 rounded-lg overflow-x-auto bg-card/20 shadow-md">
                    {loadingDsar ? <div className="p-4 text-center text-xs text-muted-foreground">Cargando tickets...</div> :
                     dsarTickets?.length === 0 ? <div className="p-4 text-center text-xs text-muted-foreground">No hay solicitudes pendientes.</div> :
                     <table className="w-full text-sm text-left border-collapse">
                      <thead className="bg-muted text-muted-foreground border-b border-border/60">
                        <tr>
                          <th className="p-4 font-semibold uppercase text-xs">ID Ticket</th>
                          <th className="p-4 font-semibold uppercase text-xs">Empleado</th>
                          <th className="p-4 font-semibold uppercase text-xs">Tipo Solicitud</th>
                          <th className="p-4 font-semibold uppercase text-xs">Fecha</th>
                          <th className="p-4 text-right font-semibold uppercase text-xs">Estado / Acción</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {dsarTickets?.map((t: any) => (
                          <tr key={t.id} className="hover:bg-muted/15">
                            <td className="p-4 font-mono text-xs">{t.id.slice(0, 8)}</td>
                            <td className="p-4">{t.employee_name}</td>
                            <td className="p-4">
                              <span className={`px-2 py-1 rounded text-xs ${t.request_type === 'delete_data' ? 'bg-red-500/10 text-red-500' : 'bg-blue-500/10 text-blue-500'}`}>
                                {t.request_type === 'delete_data' ? 'Eliminar' : 'Exportar Copia'}
                              </span>
                            </td>
                            <td className="p-4 text-xs text-muted-foreground">{new Date(t.created_at).toLocaleDateString()}</td>
                            <td className="p-4 text-right">
                              <select
                                value={t.status}
                                onChange={(e) => updateDsarStatusMutation.mutate({ id: t.id, status: e.target.value })}
                                disabled={updateDsarStatusMutation.isPending}
                                className="text-xs rounded border border-border/80 bg-card px-2 py-1 text-foreground focus:ring-1 focus:ring-primary"
                              >
                                <option value="pending">Pendiente</option>
                                <option value="processing">Procesando</option>
                                <option value="completed">Completado</option>
                                <option value="rejected">Rechazado (Legal)</option>
                              </select>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                     </table>
                    }
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
  );
}
