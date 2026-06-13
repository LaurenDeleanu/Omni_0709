"use client";

import { useMutation } from "@tanstack/react-query";
import { LegalAPI } from "@/lib/api";
import { Shield, ShieldAlert, Lock, Info, CheckCircle2, Copy } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function WhistleblowerReportPortal() {
  const [submittedCode, setSubmittedCode] = useState<string | null>(null);

  const createReportMutation = useMutation({
    mutationFn: LegalAPI.createReport,
    onSuccess: (data: any) => {
      setSubmittedCode(data.tracking_code);
    },
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    createReportMutation.mutate({
      title: formData.get("title") as string,
      category: formData.get("category") as string,
      description: formData.get("description") as string,
      is_anonymous: true, // Force anonymity
    });
  };

  const copyToClipboard = () => {
    if (submittedCode) {
      navigator.clipboard.writeText(submittedCode);
      alert("Código copiado al portapapeles.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-background py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 mb-4">
            <Shield className="w-8 h-8" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground">Canal Ético y de Denuncias</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Este es un espacio seguro y estrictamente confidencial para reportar irregularidades, acoso, fraude o violaciones de código de conducta.
          </p>
        </div>

        {/* Security Notice */}
        <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-900/30 rounded-xl p-5 flex items-start gap-4">
          <Lock className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-bold text-emerald-800 dark:text-emerald-500">Garantía de Anonimato (Directiva UE 2019/1937)</h3>
            <p className="text-sm text-emerald-700/80 dark:text-emerald-400/80 mt-1">
              La información enviada mediante este formulario es 100% anónima. El sistema omite intencionadamente la captura de su cuenta, IP o ubicación geográfica. Su reporte será encriptado y únicamente visible por el Comité de Compliance.
            </p>
          </div>
        </div>

        {/* Form or Success State */}
        {submittedCode ? (
          <div className="bg-card border border-border shadow-xl rounded-2xl p-8 text-center space-y-6">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-foreground">Denuncia Enviada de Forma Segura</h2>
              <p className="text-muted-foreground mt-2">
                Gracias por ayudar a mantener un entorno seguro. El comité de Compliance investigará su reporte.
              </p>
            </div>
            
            <div className="bg-muted p-6 rounded-xl border border-border/50 max-w-sm mx-auto">
              <p className="text-sm font-semibold text-foreground uppercase tracking-wider mb-2">Su Código de Seguimiento</p>
              <div className="flex items-center justify-between bg-background border border-border px-4 py-3 rounded-lg text-lg font-mono tracking-widest font-bold">
                {submittedCode}
                <button onClick={copyToClipboard} className="text-muted-foreground hover:text-primary transition-colors p-1" title="Copiar código">
                  <Copy className="w-5 h-5" />
                </button>
              </div>
              <div className="flex items-start gap-2 mt-4 text-xs text-muted-foreground text-left">
                <Info className="w-4 h-4 shrink-0 mt-0.5" />
                <p>Guarde este código en un lugar seguro. Es la <strong>única forma</strong> que tendrá de consultar el estado de la investigación en el futuro sin revelar su identidad.</p>
              </div>
            </div>

            <Button onClick={() => setSubmittedCode(null)} variant="outline" className="mt-4">
              Volver al inicio
            </Button>
          </div>
        ) : (
          <div className="bg-card border border-border shadow-xl rounded-2xl overflow-hidden">
            <div className="px-6 py-4 bg-muted/50 border-b border-border flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-muted-foreground" />
              <h2 className="font-semibold text-foreground">Formulario de Reporte</h2>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="space-y-2">
                <Label htmlFor="category" className="text-base">¿Qué tipo de incidencia desea reportar? <span className="text-red-500">*</span></Label>
                <select 
                  id="category" 
                  name="category" 
                  required
                  className="flex h-11 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="" disabled selected>Seleccione una categoría...</option>
                  <option value="Acoso o Discriminación">Acoso, abuso o discriminación en el trabajo</option>
                  <option value="Fraude y Corrupción">Fraude financiero, robo o corrupción</option>
                  <option value="Seguridad Laboral">Riesgos para la salud o seguridad en el entorno laboral</option>
                  <option value="Brecha de Datos">Brecha de seguridad o mal uso de datos personales</option>
                  <option value="Otro">Otras infracciones graves del código ético</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="title" className="text-base">Título descriptivo breve <span className="text-red-500">*</span></Label>
                <Input 
                  id="title" 
                  name="title" 
                  required 
                  placeholder="Ej: Irregularidades en facturas del departamento de compras" 
                  className="h-11"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-base">Descripción detallada de los hechos <span className="text-red-500">*</span></Label>
                <Textarea 
                  id="description" 
                  name="description" 
                  required 
                  placeholder="Por favor, explique con el mayor nivel de detalle posible lo que ha ocurrido, quién está involucrado y cuándo sucedió. Al ser anónimo, los detalles concretos son cruciales para iniciar una investigación..." 
                  className="min-h-[200px] resize-y"
                />
              </div>

              <div className="pt-4 flex justify-end">
                <Button 
                  type="submit" 
                  disabled={createReportMutation.isPending}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white h-11 px-8 text-base w-full sm:w-auto"
                >
                  {createReportMutation.isPending ? "Procesando de forma segura..." : "Enviar Denuncia Anónima"}
                </Button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
