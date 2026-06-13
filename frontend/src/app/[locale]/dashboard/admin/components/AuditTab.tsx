"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Loader2, Activity } from "lucide-react";

interface AuditTabProps {
  auditLogs: any[];
  loadingLogs: boolean;
}

export function AuditTab({ auditLogs, loadingLogs }: AuditTabProps) {
  const [searchLogs, setSearchLogs] = useState("");

  const filteredLogs = auditLogs?.filter((l: any) =>
    l.action.toLowerCase().includes(searchLogs.toLowerCase()) ||
    l.details.toLowerCase().includes(searchLogs.toLowerCase()) ||
    (l.ip_address && l.ip_address.includes(searchLogs))
  );

  return (
    <Card className="border border-border/50 bg-card/25 backdrop-blur-md shadow-md">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex gap-2 items-center text-lg font-bold"><Activity className="w-5 h-5 text-primary" /> Registro de Auditoría de Acciones</CardTitle>
          <CardDescription>Visualiza las acciones críticas de configuración del inquilino de forma transparente.</CardDescription>
        </div>
        <Input placeholder="Buscar por acción, IP o detalles..." className="h-8 text-xs w-[300px]" value={searchLogs} onChange={e => setSearchLogs(e.target.value)} />
      </CardHeader>
      <CardContent>
        <div className="max-h-[600px] overflow-y-auto pr-4">
          {loadingLogs ? <div className="text-xs text-muted-foreground p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" /> Cargando historial de auditoría...</div> :
            filteredLogs?.length === 0 ? <div className="text-sm text-muted-foreground p-10 text-center flex flex-col items-center gap-2"><Activity className="w-8 h-8 text-muted-foreground/50" /> Sin historial de auditoría registrado.</div> :
              <div className="relative border-l border-border/60 pl-6 space-y-6 ml-3">
                {filteredLogs?.map((log: any) => (
                <div key={log.id} className="relative group">
                  {/* Timeline dot */}
                  <span className="absolute -left-[31px] top-1.5 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-card border-2 border-primary group-hover:scale-110 transition-transform duration-200 shadow-sm" />

                  <div className="flex flex-col gap-1.5 p-4 rounded-lg bg-card/45 border border-border/60 shadow-sm hover:border-primary/20 transition-all duration-300">
                    <div className="flex items-center justify-between gap-4 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-black border ${log.action === "MODULE_TOGGLE" ? "bg-purple-500/10 text-purple-400 border-purple-500/20" :
                            log.action === "ROLE_CHANGED" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                              log.action === "COURSE_ASSIGNED" ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" :
                                "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                          }`}>
                          {log.action}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-mono bg-card px-1.5 py-0.5 rounded border border-border/40">IP: {log.ip_address || "sistema"}</span>
                      </div>
                      <span className="text-xs text-muted-foreground font-semibold">{new Date(log.created_at).toLocaleString("es-ES")}</span>
                    </div>
                    <p className="text-sm font-semibold text-foreground/90 mt-1 leading-relaxed">{log.details}</p>
                    <span className="text-[10px] text-muted-foreground/60 font-mono select-all">Registro: {log.id}</span>
                  </div>
                </div>
              ))}
            </div>
        }
        </div>
      </CardContent>
    </Card>
  );
}
