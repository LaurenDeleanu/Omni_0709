"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PayAPI, PayrollCycle, TaxRule, EmployeeCompensation, Bonus } from "@/lib/api";
import { API_BASE, fetchClient } from "@/lib/api/client";
import { Plus, DollarSign, Users, ChevronRight, FileText, CheckCircle2, CircleDashed, Server, Briefcase, MapPin, Percent, Edit, Award, Trash2 } from "lucide-react";
import { Link } from "@/i18n/routing";
import { useState } from "react";
import { toast } from "sonner";
import { useUser } from "@/hooks/use-user";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function PayrollHub() {
  const queryClient = useQueryClient();
  const { user } = useUser();
  const isAdmin = user?.role === "hr_admin" || user?.role === "super_admin";

  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: cycles, isLoading } = useQuery({
    queryKey: ["payCycles"],
    queryFn: PayAPI.getCycles,
  });

  const createCycleMutation = useMutation({
    mutationFn: PayAPI.createCycle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payCycles"] });
      setIsModalOpen(false);
      toast.success("Ciclo de pago creado.");
    },
  });

  const seedTaxesMutation = useMutation({
    mutationFn: async () => {
      return await fetchClient("/pay/cycles/seed_taxes", {
        method: "POST"
      });
    },
    onSuccess: (data) => {
      toast.success(data.message || "Impuestos configurados correctamente.");
      queryClient.invalidateQueries({ queryKey: ["taxRules"] });
    },
    onError: () => {
      toast.error("Error al configurar impuestos.");
    }
  });

  const handleCreateCycle = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const date = new Date(formData.get("month") as string);
    
    // Get first and last day of the selected month
    const start_date = new Date(date.getFullYear(), date.getMonth(), 1).toISOString();
    const end_date = new Date(date.getFullYear(), date.getMonth() + 1, 0).toISOString();
    
    const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    const period_name = `${monthNames[date.getMonth()]} ${date.getFullYear()}`;

    createCycleMutation.mutate({
      period_name,
      start_date,
      end_date
    });
  };

  const getStatusBadge = (status: string) => {
    switch(status) {
      case 'processing': return <span className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5"><CircleDashed className="w-3.5 h-3.5 animate-spin-slow" /> Procesando</span>;
      case 'paid': return <span className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5" /> Pagado</span>;
      default: return <span className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5">Borrador</span>;
    }
  };

  const totalAnnualPayroll = cycles?.reduce((acc: number, cycle: PayrollCycle) => acc + cycle.total_gross, 0) || 0;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Nóminas & Finanzas</h1>
          <p className="text-muted-foreground mt-1">
            Gestiona los ciclos de pago y configura las reglas fiscales.
          </p>
        </div>

        <InlineCopilot
          moduleContext="payroll"
          placeholder="Pregunta sobre nóminas, impuestos o compensación..."
          quickActions={[
            { label: "Calcular nómina de este mes", message: "Calcular nómina de este mes" },
            { label: "Ver impuestos configurados", message: "Ver impuestos configurados" },
            { label: "Comparar costes salariales", message: "Comparar costes salariales" },
            { label: "Generar informe de costes", message: "Generar informe de costes" },
          ]}
        />

        <div className="flex gap-2">
          {isAdmin && (
            <Button 
              variant="outline" 
              onClick={() => seedTaxesMutation.mutate()}
              disabled={seedTaxesMutation.isPending}
              className="gap-2"
            >
              <Server className="h-4 w-4" />
              {seedTaxesMutation.isPending ? "Cargando..." : "Cargar Impuestos (2026)"}
            </Button>
          )}

          <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
            <DialogTrigger render={<Button className="gap-2" />}>
                <Plus className="h-4 w-4" />
                Nuevo Ciclo de Pago
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Generar Ciclo de Pago</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateCycle} className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="month">Mes a Procesar</Label>
                  <Input id="month" name="month" type="month" required />
                  <p className="text-xs text-muted-foreground pt-1">
                    Se generará un borrador del ciclo para este mes. Podrás revisar los montos antes de aprobar.
                  </p>
                </div>
                <div className="pt-4 flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                  <Button type="submit" disabled={createCycleMutation.isPending}>
                    {createCycleMutation.isPending ? "Generando..." : "Crear Borrador"}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Tabs defaultValue="cycles" className="space-y-6">
        <TabsList>
          <TabsTrigger value="cycles">Ciclos de Pago</TabsTrigger>
          {isAdmin && <TabsTrigger value="rules">Reglas Fiscales (Admin)</TabsTrigger>}
          {isAdmin && <TabsTrigger value="employees">Compensación (Admin)</TabsTrigger>}
        </TabsList>

        <TabsContent value="cycles" className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 flex items-center justify-center">
                  <DollarSign className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Nómina Pagada</p>
                  <h3 className="text-2xl font-bold">
                    {new Intl.NumberFormat(undefined, { style: "currency", currency: (user as any)?.currency || "EUR" }).format(totalAnnualPayroll)}
                  </h3>
                </div>
              </div>
            </div>
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/30 flex items-center justify-center">
                  <Users className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Ciclos Procesados</p>
                  <h3 className="text-2xl font-bold">{cycles?.filter((c: PayrollCycle) => c.status === 'paid').length || 0}</h3>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h2 className="text-xl font-bold mb-4">Historial de Ciclos</h2>
            <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
                    <tr>
                      <th className="px-6 py-4 font-medium">Período</th>
                      <th className="px-6 py-4 font-medium">Estado</th>
                      <th className="px-6 py-4 font-medium text-right">Sueldo Bruto Total</th>
                      <th className="px-6 py-4 font-medium text-right">Sueldo Neto Total</th>
                      <th className="px-6 py-4 font-medium text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {isLoading ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">
                          Cargando ciclos...
                        </td>
                      </tr>
                    ) : cycles?.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-12 text-center">
                          <div className="flex flex-col items-center justify-center text-muted-foreground">
                            <FileText className="w-12 h-12 mb-4 opacity-20" />
                            <p className="text-lg font-medium text-foreground">No hay nóminas procesadas</p>
                            <p className="text-sm mt-1">Haz clic en &quot;Nuevo Ciclo de Pago&quot; para comenzar.</p>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      cycles?.map((cycle: PayrollCycle) => (
                        <tr key={cycle.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors group">
                          <td className="px-6 py-4 font-semibold text-foreground">
                            {cycle.period_name}
                          </td>
                          <td className="px-6 py-4">
                            {getStatusBadge(cycle.status)}
                          </td>
                          <td className="px-6 py-4 text-right font-medium">
                            {new Intl.NumberFormat(undefined, { style: "currency", currency: cycle.currency || "EUR" }).format(cycle.total_gross)}
                          </td>
                          <td className="px-6 py-4 text-right font-bold text-emerald-600 dark:text-emerald-400">
                            {new Intl.NumberFormat(undefined, { style: "currency", currency: cycle.currency || "EUR" }).format(cycle.total_net)}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <Link href={`/dashboard/pay/${cycle.id}`}>
                              <Button variant="ghost" size="sm" className="gap-2 group-hover:bg-primary group-hover:text-primary-foreground transition-all">
                                Ver Detalles <ChevronRight className="w-4 h-4" />
                              </Button>
                            </Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </TabsContent>

        {isAdmin && (
          <>
            <TabsContent value="rules">
              <TaxRulesAdminTab />
            </TabsContent>
            <TabsContent value="employees">
              <EmployeeCompAdminTab />
            </TabsContent>
          </>
        )}
      </Tabs>
    </div>
  );
}

// Subcomponent for Tax Rules Admin
function TaxRulesAdminTab() {
  const queryClient = useQueryClient();
  const [editingRule, setEditingRule] = useState<TaxRule | null>(null);

  const { data: rules, isLoading } = useQuery({
    queryKey: ["taxRules"],
    queryFn: PayAPI.getTaxRules,
  });

  const updateRuleMutation = useMutation({
    mutationFn: (data: Partial<TaxRule> & { id: string }) => PayAPI.updateTaxRule(data.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["taxRules"] });
      setEditingRule(null);
      toast.success("Regla fiscal actualizada.");
    },
  });

  const handleUpdate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingRule) return;
    const formData = new FormData(e.currentTarget);
    const rate = parseFloat(formData.get("rate") as string);
    const min_salary = formData.get("min_salary") ? parseFloat(formData.get("min_salary") as string) : undefined;
    const max_salary = formData.get("max_salary") ? parseFloat(formData.get("max_salary") as string) : undefined;

    updateRuleMutation.mutate({
      id: editingRule.id,
      rate,
      min_salary,
      max_salary
    });
  };

  return (
    <div className="bg-card border border-border rounded-xl shadow-sm p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2"><Percent className="w-5 h-5 text-indigo-500"/> Reglas Fiscales & Tramos</h2>
          <p className="text-muted-foreground text-sm">Administra los tramos de IRPF y deducciones impositivas por país.</p>
        </div>
      </div>
      
      {isLoading ? (
        <div className="py-8 text-center text-muted-foreground">Cargando reglas...</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
              <tr>
                <th className="px-4 py-3 font-medium">País</th>
                <th className="px-4 py-3 font-medium">Nombre de Regla</th>
                <th className="px-4 py-3 font-medium text-right">Rango Salarial</th>
                <th className="px-4 py-3 font-medium text-right">Tasa (%)</th>
                <th className="px-4 py-3 font-medium text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rules?.map((rule: TaxRule) => (
                <tr key={rule.id} className="border-b border-border/50 hover:bg-muted/30">
                  <td className="px-4 py-3 font-bold">{rule.country_code}</td>
                  <td className="px-4 py-3">{rule.name}</td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    ${rule.min_salary?.toLocaleString() || '0'} - {rule.max_salary ? `$${rule.max_salary.toLocaleString()}` : '∞'}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-red-500">
                    {(rule.rate * 100).toFixed(2)}%
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Dialog open={editingRule?.id === rule.id} onOpenChange={(open) => !open && setEditingRule(null)}>
                      <DialogTrigger render={<Button variant="ghost" size="sm" onClick={() => setEditingRule(rule)} />}>
                          <Edit className="w-4 h-4 mr-1" /> Editar
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-[425px]">
                        <DialogHeader>
                          <DialogTitle>Editar Regla: {rule.name}</DialogTitle>
                        </DialogHeader>
                        <form onSubmit={handleUpdate} className="space-y-4 py-4">
                          <div className="space-y-2">
                            <Label>Tasa (%)</Label>
                            <Input 
                              name="rate" 
                              type="number" 
                              step="0.001" 
                              defaultValue={rule.rate} 
                              required 
                            />
                            <p className="text-xs text-muted-foreground">Ejemplo: 0.19 para 19%</p>
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Salario Mínimo</Label>
                              <Input name="min_salary" type="number" defaultValue={rule.min_salary} />
                            </div>
                            <div className="space-y-2">
                              <Label>Salario Máximo</Label>
                              <Input name="max_salary" type="number" defaultValue={rule.max_salary || ''} />
                            </div>
                          </div>
                          <div className="pt-4 flex justify-end gap-2">
                            <Button type="button" variant="outline" onClick={() => setEditingRule(null)}>Cancelar</Button>
                            <Button type="submit" disabled={updateRuleMutation.isPending}>
                              {updateRuleMutation.isPending ? "Guardando..." : "Guardar Cambios"}
                            </Button>
                          </div>
                        </form>
                      </DialogContent>
                    </Dialog>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Subcomponent for Bonus/KPI Admin
function BonusAdminDialog({ employeeId, employeeName }: { employeeId: string; employeeName: string }) {
  const queryClient = useQueryClient();
  const { data: bonuses, isLoading } = useQuery({
    queryKey: ["bonuses", employeeId],
    queryFn: () => PayAPI.getBonuses(employeeId),
  });

  const createBonusMutation = useMutation({
    mutationFn: (data: { amount: number, description: string, type: string }) => PayAPI.createBonus(employeeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bonuses", employeeId] });
      toast.success("Bono añadido.");
    },
  });

  const deleteBonusMutation = useMutation({
    mutationFn: PayAPI.deleteBonus,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bonuses", employeeId] });
      toast.success("Bono eliminado.");
    },
    onError: () => toast.error("No se puede eliminar un bono ya pagado.")
  });

  const handleAdd = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createBonusMutation.mutate({
      amount: parseFloat(formData.get("amount") as string),
      description: formData.get("description") as string,
      type: formData.get("type") as string,
    });
    e.currentTarget.reset();
  };

  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm" className="ml-2 border-emerald-200 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-800 dark:text-emerald-400 dark:hover:bg-emerald-950/50">
            <Award className="w-4 h-4 mr-1" /> Bonos & KPIs
          </Button>
        }
      />
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Bonos: {employeeName}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <form onSubmit={handleAdd} className="flex flex-col gap-3 p-4 bg-muted/50 rounded-lg border border-border">
            <h4 className="font-semibold text-sm">Añadir Nuevo Bono (Pendiente)</h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Monto ($)</Label>
                <Input name="amount" type="number" step="0.01" required />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Tipo</Label>
                <Select name="type" defaultValue="standard">
                  <SelectTrigger><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Estándar</SelectItem>
                    <SelectItem value="kpi">KPI / Rendimiento</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Descripción</Label>
              <Input name="description" placeholder="Ej. Cumplimiento de metas Q2" required />
            </div>
            <Button type="submit" disabled={createBonusMutation.isPending} size="sm" className="self-end mt-2">
              {createBonusMutation.isPending ? "Añadiendo..." : "Añadir Bono"}
            </Button>
          </form>

          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
            <h4 className="font-semibold text-sm">Historial de Bonos</h4>
            {isLoading ? <p className="text-xs text-muted-foreground">Cargando...</p> : null}
            {!isLoading && bonuses?.length === 0 ? <p className="text-xs text-muted-foreground">No hay bonos registrados.</p> : null}
            {bonuses?.map((bonus: Bonus) => (
              <div key={bonus.id} className="flex items-center justify-between p-3 border border-border rounded-md text-sm">
                <div>
                  <div className="font-medium flex items-center gap-2">
                    ${bonus.amount.toLocaleString()} <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{bonus.type.toUpperCase()}</span>
                  </div>
                  <div className="text-muted-foreground text-xs mt-1">{bonus.description}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-1 rounded-full ${bonus.status === 'paid' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}`}>
                    {bonus.status === 'paid' ? 'Pagado' : 'Pendiente'}
                  </span>
                  {bonus.status === 'pending' && (
                    <Button variant="ghost" size="icon" onClick={() => deleteBonusMutation.mutate(bonus.id)} className="h-7 w-7 text-destructive hover:bg-destructive/10">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Subcomponent for Employee Compensation Admin
function EmployeeCompAdminTab() {
  const queryClient = useQueryClient();
  const [editingComp, setEditingComp] = useState<EmployeeCompensation | null>(null);

  const { data: compensations, isLoading } = useQuery({
    queryKey: ["employeeComps"],
    queryFn: PayAPI.getEmployeeCompensations,
  });

  const updateCompMutation = useMutation({
    mutationFn: (data: Partial<EmployeeCompensation> & { id: string }) => PayAPI.updateEmployeeCompensation(data.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employeeComps"] });
      setEditingComp(null);
      toast.success("Compensación actualizada.");
    },
  });

  const handleUpdate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingComp) return;
    const formData = new FormData(e.currentTarget);
    const base_salary = parseFloat(formData.get("base_salary") as string);
    const country = formData.get("country") as string;

    updateCompMutation.mutate({
      id: editingComp.id,
      base_salary,
      country
    });
  };

  return (
    <div className="bg-card border border-border rounded-xl shadow-sm p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2"><Briefcase className="w-5 h-5 text-emerald-500"/> Compensación de Empleados</h2>
          <p className="text-muted-foreground text-sm">Gestiona el salario base y el país de residencia fiscal de tu plantilla.</p>
        </div>
      </div>
      
      {isLoading ? (
        <div className="py-8 text-center text-muted-foreground">Cargando compensaciones...</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
              <tr>
                <th className="px-4 py-3 font-medium">Empleado</th>
                <th className="px-4 py-3 font-medium">País Fiscal</th>
                <th className="px-4 py-3 font-medium text-right">Salario Base (Anual)</th>
                <th className="px-4 py-3 font-medium text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {compensations?.map((comp: EmployeeCompensation) => (
                <tr key={comp.id} className="border-b border-border/50 hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div className="font-semibold">{comp.full_name}</div>
                    <div className="text-xs text-muted-foreground">{comp.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-muted-foreground" /> {comp.country}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-emerald-600 dark:text-emerald-400">
                    ${comp.base_salary.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Button variant="ghost" size="sm" onClick={() => setEditingComp(comp)}>
                      <Edit className="w-4 h-4 mr-1" /> Editar
                    </Button>
                    <BonusAdminDialog employeeId={comp.id} employeeName={comp.full_name || comp.email} />
                    <Dialog open={editingComp?.id === comp.id} onOpenChange={(open) => !open && setEditingComp(null)}>
                      <DialogContent className="sm:max-w-[425px]">
                        <DialogHeader>
                          <DialogTitle>Editar: {comp.full_name}</DialogTitle>
                        </DialogHeader>
                        <form onSubmit={handleUpdate} className="space-y-4 py-4">
                          <div className="space-y-2">
                            <Label>Salario Base (Anual)</Label>
                            <Input 
                              name="base_salary" 
                              type="number" 
                              defaultValue={comp.base_salary} 
                              required 
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>País de Residencia Fiscal</Label>
                            <Select name="country" defaultValue={comp.country}>
                              <SelectTrigger>
                                <SelectValue placeholder="Selecciona un país" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="ES">España (ES)</SelectItem>
                                <SelectItem value="UK">Reino Unido (UK)</SelectItem>
                                <SelectItem value="FR">Francia (FR)</SelectItem>
                                <SelectItem value="DE">Alemania (DE)</SelectItem>
                                <SelectItem value="IT">Italia (IT)</SelectItem>
                                <SelectItem value="NL">Países Bajos (NL)</SelectItem>
                                <SelectItem value="PT">Portugal (PT)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="pt-4 flex justify-end gap-2">
                            <Button type="button" variant="outline" onClick={() => setEditingComp(null)}>Cancelar</Button>
                            <Button type="submit" disabled={updateCompMutation.isPending}>
                              {updateCompMutation.isPending ? "Guardando..." : "Guardar Cambios"}
                            </Button>
                          </div>
                        </form>
                      </DialogContent>
                    </Dialog>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
