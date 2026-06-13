"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SalesAPI, Lead } from "@/lib/api";
import { Plus, DollarSign, Building, MoreHorizontal, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Link } from "@/i18n/routing";
import { useState, useMemo } from "react";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

const SALES_STAGES = [
  { id: "inbound", name: "Leads / Inbound", color: "bg-slate-50 dark:bg-slate-800/50", border: "border-slate-200 dark:border-slate-700" },
  { id: "discovery", name: "Discovery", color: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-200 dark:border-blue-800" },
  { id: "proposal", name: "Propuesta Enviada", color: "bg-amber-50 dark:bg-amber-900/20", border: "border-amber-200 dark:border-amber-800" },
  { id: "negotiation", name: "Negociación", color: "bg-purple-50 dark:bg-purple-900/20", border: "border-purple-200 dark:border-purple-800" },
  { id: "won", name: "Closed Won", color: "bg-emerald-50 dark:bg-emerald-900/20", border: "border-emerald-200 dark:border-emerald-800" },
  { id: "lost", name: "Closed Lost", color: "bg-red-50 dark:bg-red-900/20", border: "border-red-200 dark:border-red-800" },
];

export default function SalesDashboard() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedLeadForEdit, setSelectedLeadForEdit] = useState<Lead | null>(null);

  const { data: leads, isLoading } = useQuery<Lead[]>({
    queryKey: ["salesLeads"],
    queryFn: SalesAPI.getLeads,
  });

  const createLeadMutation = useMutation<Lead, Error, Partial<Lead>>({
    mutationFn: SalesAPI.createLead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salesLeads"] });
      setIsModalOpen(false);
      toast.success("Deal creado con éxito");
    },
  });

  const updateStageMutation = useMutation<any, Error, { id: string; stage: string }>({
    mutationFn: ({ id, stage }) => SalesAPI.updateLeadStage(id, stage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salesLeads"] });
    },
  });

  const updateLeadMutation = useMutation<Lead, Error, { id: string; data: Partial<Lead> }>({
    mutationFn: ({ id, data }) => SalesAPI.updateLead(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salesLeads"] });
      setIsEditModalOpen(false);
      toast.success("Deal actualizado con éxito");
    },
  });

  const deleteLeadMutation = useMutation<any, Error, string>({
    mutationFn: (id: string) => SalesAPI.deleteLead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salesLeads"] });
      setIsEditModalOpen(false);
      toast.success("Deal eliminado");
    },
  });

  const handleCreateLead = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createLeadMutation.mutate({
      title: formData.get("title") as string,
      contact_name: formData.get("contact_name") as string,
      company_name: formData.get("company_name") as string,
      email: formData.get("email") as string,
      phone: formData.get("phone") as string,
      estimated_value: parseFloat(formData.get("estimated_value") as string) || 0,
      probability: parseInt(formData.get("probability") as string) || 10,
      stage: "inbound",
    });
  };

  const handleEditLead = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedLeadForEdit) return;
    const formData = new FormData(e.currentTarget);
    updateLeadMutation.mutate({
      id: selectedLeadForEdit.id,
      data: {
        title: formData.get("title") as string,
        company_name: formData.get("company_name") as string,
        contact_name: formData.get("contact_name") as string,
        estimated_value: parseFloat(formData.get("estimated_value") as string) || 0,
        probability: parseInt(formData.get("probability") as string) || 0,
      }
    });
  };

  const handleDeleteLead = (id: string) => {
    if (confirm("¿Estás seguro de que deseas eliminar este Deal?")) {
      deleteLeadMutation.mutate(id);
    }
  };

  const onDragStart = (e: React.DragEvent, leadId: string) => {
    e.dataTransfer.setData("leadId", leadId);
  };

  const onDragOver = (e: React.DragEvent) => e.preventDefault();

  const onDrop = (e: React.DragEvent, stageId: string) => {
    const leadId = e.dataTransfer.getData("leadId");
    if (leadId) {
      updateStageMutation.mutate({ id: leadId, stage: stageId });
    }
  };

  // KPI Calculations
  const activePipelineValue = useMemo(() => {
    if (!leads) return 0;
    return leads
      .filter((l: Lead) => l.stage !== 'lost' && l.stage !== 'won')
      .reduce((sum: number, l: Lead) => sum + (l.estimated_value || 0), 0);
  }, [leads]);

  const expectedRevenue = useMemo(() => {
    if (!leads) return 0;
    return leads
      .filter((l: Lead) => l.stage !== 'lost' && l.stage !== 'won')
      .reduce((sum: number, l: Lead) => sum + ((l.estimated_value || 0) * ((l.probability || 0) / 100)), 0);
  }, [leads]);

  const closedWonRevenue = useMemo(() => {
    if (!leads) return 0;
    return leads
      .filter((l: Lead) => l.stage === 'won')
      .reduce((sum: number, l: Lead) => sum + (l.estimated_value || 0), 0);
  }, [leads]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-xl px-6 py-4 flex flex-col md:flex-row md:items-center justify-between shrink-0 gap-4">
        <div>
          <h1 className="text-2xl font-bold">CRM & Ventas</h1>
          <div className="flex items-center gap-6 mt-2">
            <Link href="/dashboard/sales" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
              Pipeline (Deals)
            </Link>
            <Link href="/dashboard/sales/clients" className="text-sm font-medium text-muted-foreground hover:text-foreground pb-1">
              Directorio de Clientes
            </Link>
          </div>
        </div>

        <InlineCopilot
          moduleContext="sales"
          placeholder="Pregunta sobre el pipeline de ventas..."
          quickActions={[
            { label: "Analizar pipeline activo", message: "Analizar pipeline activo" },
            { label: "Identificar deals en riesgo", message: "Identificar deals en riesgo" },
            { label: "Previsión de cierre mensual", message: "Previsión de cierre mensual" },
            { label: "Sugerir próximas acciones", message: "Sugerir próximas acciones" },
          ]}
        />

        <div className="flex items-center gap-4">
          <div className="flex gap-4 mr-4 bg-muted/40 p-2 rounded-lg border border-border">
            <div className="flex flex-col px-3 border-r border-border">
              <span className="text-[10px] uppercase font-bold text-muted-foreground">Pipeline Activo</span>
              <span className="text-sm font-bold">${activePipelineValue.toLocaleString()}</span>
            </div>
            <div className="flex flex-col px-3 border-r border-border">
              <span className="text-[10px] uppercase font-bold text-amber-600">Ingreso Esperado</span>
              <span className="text-sm font-bold text-amber-600">${expectedRevenue.toLocaleString()}</span>
            </div>
            <div className="flex flex-col px-3">
              <span className="text-[10px] uppercase font-bold text-emerald-600">Closed Won</span>
              <span className="text-sm font-bold text-emerald-600">${closedWonRevenue.toLocaleString()}</span>
            </div>
          </div>

          <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
            <DialogTrigger render={<Button className="gap-2" />}>
                <Plus className="h-4 w-4" />
                Nuevo Deal
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Crear Oportunidad (Lead)</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateLead} className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Nombre de la Oportunidad</Label>
                  <Input id="title" name="title" required placeholder="Ej: Implementación ERP para Acme" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="company_name">Empresa</Label>
                    <Input id="company_name" name="company_name" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact_name">Contacto Principal</Label>
                    <Input id="contact_name" name="contact_name" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="estimated_value">Valor Estimado ($)</Label>
                    <Input id="estimated_value" name="estimated_value" type="number" min="0" defaultValue="0" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="probability">Probabilidad (%)</Label>
                    <Input id="probability" name="probability" type="number" min="0" max="100" defaultValue="10" />
                  </div>
                </div>
                <div className="pt-4 flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                  <Button type="submit" disabled={createLeadMutation.isPending}>
                    {createLeadMutation.isPending ? "Creando..." : "Crear Lead"}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Kanban Board Area */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6 bg-muted/10">
        <div className="flex gap-4 h-full items-start w-max min-w-full">
          {SALES_STAGES.map((stage) => {
            const stageLeads = leads?.filter((l: Lead) => l.stage === stage.id) || [];
            const stageTotal = stageLeads.reduce((sum: number, l: Lead) => sum + (l.estimated_value || 0), 0);
            
            return (
              <div 
                key={stage.id} 
                className={`flex flex-col w-[320px] h-full max-h-full rounded-xl border ${stage.border} ${stage.color} p-3 shrink-0 transition-colors`}
                onDragOver={onDragOver}
                onDrop={(e) => onDrop(e, stage.id)}
              >
                <div className="flex items-center justify-between mb-3 px-1">
                  <div>
                    <h3 className="font-bold text-sm text-foreground/80">{stage.name}</h3>
                    <p className="text-xs font-semibold text-muted-foreground mt-0.5">${stageTotal.toLocaleString()}</p>
                  </div>
                  <span className="bg-background text-muted-foreground text-xs font-medium py-1 px-2.5 rounded-full border border-border shadow-sm">
                    {stageLeads.length}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto space-y-3 pb-2 custom-scrollbar pr-1">
                  {stageLeads.map((lead: Lead) => (
                    <div 
                      key={lead.id} 
                      draggable
                      onDragStart={(e) => onDragStart(e, lead.id)}
                      className="bg-card border border-border/80 rounded-lg p-4 shadow-sm hover:border-primary/40 hover:shadow-md transition-all cursor-grab active:cursor-grabbing group"
                    >
                      <div className="flex justify-between items-start mb-1.5">
                        <h4 className="font-semibold text-sm text-foreground leading-tight">{lead.title}</h4>
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLeadForEdit(lead);
                            setIsEditModalOpen(true);
                          }}
                          className="text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </div>
                      
                      {lead.company_name && (
                        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-3">
                          <Building className="w-3.5 h-3.5" />
                          <span className="truncate">{lead.company_name}</span>
                        </div>
                      )}

                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/50">
                        <div className="flex items-center gap-1 text-sm font-bold text-foreground">
                          <DollarSign className="w-3.5 h-3.5 text-emerald-500" />
                          {lead.estimated_value.toLocaleString()}
                        </div>
                        <div className={`text-xs font-bold px-2 py-0.5 rounded flex items-center gap-1 ${
                          lead.probability >= 70 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' :
                          lead.probability >= 30 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                          'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400'
                        }`}>
                          {lead.probability}% 
                          {lead.probability >= 50 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {stageLeads.length === 0 && !isLoading && (
                    <div className="h-24 rounded-lg border-2 border-dashed border-border/60 flex items-center justify-center text-xs text-muted-foreground/60">
                      Arrastra deals aquí
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* DIALOG: EDIT/DELETE LEAD */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Editar Oportunidad (Lead)</DialogTitle>
          </DialogHeader>
          {selectedLeadForEdit && (
            <form onSubmit={handleEditLead} className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-title">Nombre de la Oportunidad</Label>
                <Input id="edit-title" name="title" defaultValue={selectedLeadForEdit.title} required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-company_name">Empresa</Label>
                  <Input id="edit-company_name" name="company_name" defaultValue={selectedLeadForEdit.company_name} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-contact_name">Contacto Principal</Label>
                  <Input id="edit-contact_name" name="contact_name" defaultValue={selectedLeadForEdit.contact_name} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-estimated_value">Valor Estimado ($)</Label>
                  <Input id="edit-estimated_value" name="estimated_value" type="number" min="0" defaultValue={selectedLeadForEdit.estimated_value} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-probability">Probabilidad (%)</Label>
                  <Input id="edit-probability" name="probability" type="number" min="0" max="100" defaultValue={selectedLeadForEdit.probability} />
                </div>
              </div>
              
              <div className="pt-4 flex justify-between gap-2 border-t border-border mt-4">
                <Button type="button" variant="destructive" onClick={() => handleDeleteLead(selectedLeadForEdit.id)} disabled={deleteLeadMutation.isPending}>
                  Eliminar Deal
                </Button>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsEditModalOpen(false)}>Cancelar</Button>
                  <Button type="submit" disabled={updateLeadMutation.isPending}>
                    {updateLeadMutation.isPending ? "Guardando..." : "Guardar Cambios"}
                  </Button>
                </div>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
      
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(156, 163, 175, 0.3); border-radius: 20px; }
      `}} />
    </div>
  );
}
