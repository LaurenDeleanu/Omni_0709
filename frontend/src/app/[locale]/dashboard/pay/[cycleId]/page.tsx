"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PayAPI, PayrollCycle, Payslip } from "@/lib/api";
import { ArrowLeft, Play, CheckCircle2, Download, AlertCircle, RefreshCw } from "lucide-react";
import { Link } from "@/i18n/routing";
import { useParams } from "next/navigation";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export default function PayrollRunDetails() {
  const params = useParams();
  const cycleId = params.cycleId as string;
  const queryClient = useQueryClient();

  const { data: cycles, isLoading: isLoadingCycles } = useQuery({
    queryKey: ["payCycles"],
    queryFn: PayAPI.getCycles,
  });
  
  const cycle = cycles?.find((c: PayrollCycle) => c.id === cycleId);

  const { data: payslips, isLoading: isLoadingPayslips } = useQuery({
    queryKey: ["payPayslips", cycleId],
    queryFn: () => PayAPI.getCyclePayslips(cycleId),
  });

  const processPayrollMutation = useMutation({
    mutationFn: () => PayAPI.processPayroll(cycleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payCycles"] });
      queryClient.invalidateQueries({ queryKey: ["payPayslips", cycleId] });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: (status: string) => PayAPI.updateCycleStatus(cycleId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payCycles"] });
      queryClient.invalidateQueries({ queryKey: ["payPayslips", cycleId] });
    },
  });

  const isDraft = cycle?.status === 'draft';
  const isProcessing = cycle?.status === 'processing';
  const isPaid = cycle?.status === 'paid';

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-xl px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/pay" className="p-2 hover:bg-muted rounded-full transition-colors text-muted-foreground hover:text-foreground">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">Ciclo: {cycle?.period_name}</h1>
              {isDraft && <span className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-0.5 rounded text-xs font-bold uppercase">Borrador</span>}
              {isProcessing && <span className="bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded text-xs font-bold uppercase">Procesando</span>}
              {isPaid && <span className="bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 px-2 py-0.5 rounded text-xs font-bold uppercase">Pagado</span>}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {new Date(cycle?.start_date || "").toLocaleDateString()} - {new Date(cycle?.end_date || "").toLocaleDateString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {isDraft && (
            <Button 
              onClick={() => processPayrollMutation.mutate()} 
              disabled={processPayrollMutation.isPending}
              className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              {processPayrollMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Procesar Empleados
            </Button>
          )}

          {isProcessing && (
            <Button 
              onClick={() => updateStatusMutation.mutate("paid")} 
              disabled={updateStatusMutation.isPending}
              className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              <CheckCircle2 className="h-4 w-4" />
              Aprobar y Emitir Pagos
            </Button>
          )}

          {isPaid && (
            <Button variant="outline" className="gap-2">
              <Download className="h-4 w-4" />
              Descargar Reporte
            </Button>
          )}
        </div>
      </div>

      {/* Stats Summary */}
      {!isDraft && (
        <div className="bg-muted/30 border-b border-border p-6 shrink-0">
          <div className="max-w-4xl mx-auto flex gap-12">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Total Bruto</p>
              <p className="text-2xl font-bold">{new Intl.NumberFormat(undefined, { style: "currency", currency: cycle?.currency || "EUR" }).format(cycle?.total_gross || 0)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Total Deducciones (Impuestos)</p>
              <p className="text-2xl font-bold text-red-500">
                {new Intl.NumberFormat(undefined, { style: "currency", currency: cycle?.currency || "EUR" }).format((cycle?.total_gross || 0) - (cycle?.total_net || 0))}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Total Neto (A pagar)</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{new Intl.NumberFormat(undefined, { style: "currency", currency: cycle?.currency || "EUR" }).format(cycle?.total_net || 0)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Empleados</p>
              <p className="text-2xl font-bold">{payslips?.length || 0}</p>
            </div>
          </div>
        </div>
      )}

      {/* Payslips Table */}
      <div className="flex-1 overflow-auto p-6 bg-muted/10">
        <div className="max-w-5xl mx-auto">
          {isDraft ? (
            <div className="bg-card border-2 border-dashed border-border rounded-xl p-12 text-center">
              <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium text-foreground">El ciclo está en borrador</h3>
              <p className="text-muted-foreground mt-2 max-w-md mx-auto">
                Haz clic en "Procesar Empleados" para generar las nóminas (payslips) en base a los salarios actuales y las reglas fiscales configuradas.
              </p>
            </div>
          ) : (
            <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
                  <tr>
                    <th className="px-6 py-4 font-medium">Empleado</th>
                    <th className="px-6 py-4 font-medium text-right">Sueldo Bruto</th>
                    <th className="px-6 py-4 font-medium text-right text-red-500">Deducciones</th>
                    <th className="px-6 py-4 font-medium text-right text-emerald-600">Sueldo Neto</th>
                    <th className="px-6 py-4 font-medium text-center">Estado</th>
                    <th className="px-6 py-4 font-medium text-right">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoadingPayslips ? (
                    <tr><td colSpan={6} className="text-center py-8">Cargando recibos...</td></tr>
                  ) : (
                    payslips?.map((payslip: Payslip) => (
                      <tr key={payslip.id} className="border-b border-border/50 hover:bg-muted/30">
                        <td className="px-6 py-4">
                          <div className="font-semibold">{payslip.employee_name}</div>
                          <div className="text-xs text-muted-foreground">{payslip.employee_email}</div>
                        </td>
                        <td className="px-6 py-4 text-right font-medium">
                          {new Intl.NumberFormat(undefined, { style: "currency", currency: payslip.currency || "EUR" }).format(payslip.gross_salary)}
                        </td>
                        <td className="px-6 py-4 text-right text-red-500 font-medium">
                          -{new Intl.NumberFormat(undefined, { style: "currency", currency: payslip.currency || "EUR" }).format(payslip.deductions)}
                        </td>
                        <td className="px-6 py-4 text-right text-emerald-600 dark:text-emerald-400 font-bold">
                          {new Intl.NumberFormat(undefined, { style: "currency", currency: payslip.currency || "EUR" }).format(payslip.net_salary)}
                        </td>
                        <td className="px-6 py-4 text-center">
                          {payslip.status === 'finalized' ? (
                            <span className="bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase">Finalizado</span>
                          ) : (
                            <span className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[10px] px-2 py-0.5 rounded font-bold uppercase">Borrador</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                           <Dialog>
                            <DialogTrigger render={
                              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                                Ver Desglose
                              </Button>
                            } />
                            <DialogContent className="max-w-md">
                              <DialogHeader>
                                <DialogTitle>Desglose de Nómina</DialogTitle>
                              </DialogHeader>
                              <div className="space-y-4 py-4">
                                <div className="flex justify-between font-bold text-sm border-b pb-2">
                                  <span>Concepto</span>
                                  <span>Importe</span>
                                </div>
                                <div className="space-y-2">
                                  {(payslip as any).line_items?.map((li: any) => (
                                    <div key={li.id} className="flex justify-between text-sm">
                                      <span className={li.type === 'deduction' ? 'text-red-500' : 'text-emerald-600'}>
                                        {li.description}
                                      </span>
                                      <span className={li.type === 'deduction' ? 'text-red-500' : 'text-emerald-600'}>
                                        {li.type === 'deduction' ? '-' : '+'}{new Intl.NumberFormat(undefined, { style: "currency", currency: payslip.currency || "EUR" }).format(li.amount)}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                                <div className="flex justify-between font-bold text-lg border-t pt-4">
                                  <span>Total Neto</span>
                                  <span className="text-emerald-600">{new Intl.NumberFormat(undefined, { style: "currency", currency: payslip.currency || "EUR" }).format(payslip.net_salary)}</span>
                                </div>
                              </div>
                            </DialogContent>
                          </Dialog>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
