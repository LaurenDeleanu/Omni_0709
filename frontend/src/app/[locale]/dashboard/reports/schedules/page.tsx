"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ScheduleAPI, Schedule } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Plus, Loader2, Trash2, CalendarClock, Send, Clock, ArrowLeft } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Link } from "@/i18n/routing";

const EMPTY_FORM = {
  email_to: "", frequency: "weekly",
};

export default function ScheduledReportsPage() {
  const queryClient = useQueryClient();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const { data: schedules, isLoading, isError } = useQuery<Schedule[]>({
    queryKey: ["schedules"],
    queryFn: ScheduleAPI.list,
  });

  const createMutation = useMutation({
    mutationFn: ScheduleAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
      setSheetOpen(false);
      setForm(EMPTY_FORM);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: ScheduleAPI.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["schedules"] }),
  });

  const triggerMutation = useMutation({
    mutationFn: ScheduleAPI.trigger,
    onSuccess: (data) => {
        toast.success(data.message);
    },
    onError: () => {
        toast.error("Error al ejecutar el reporte");
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form as Partial<Schedule>);
  };

  const isMutating = createMutation.isPending;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/reports" className="p-2 hover:bg-muted rounded-full transition-colors text-muted-foreground hover:text-foreground">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Programación de Informes</h2>
            <p className="text-sm text-muted-foreground">
              Agenda envíos automáticos de reportes ejecutivos por correo.
            </p>
          </div>
        </div>
        <Button id="add-schedule-btn" onClick={() => setSheetOpen(true)} className="gap-2">
          <Plus className="w-4 h-4" /> Nuevo Envío
        </Button>
      </div>

      {/* Cards */}
      <div className="grid gap-4 md:grid-cols-3">
         <Card className="glass shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Programaciones Activas
              </CardTitle>
              <CalendarClock className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{schedules?.filter(s => s.is_active).length || 0}</div>
            </CardContent>
          </Card>
      </div>

      {/* Table */}
      <div className="rounded-md border bg-card/50 backdrop-blur-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              <TableHead>Email Destino</TableHead>
              <TableHead>Frecuencia</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="hidden md:table-cell">Último Envío</TableHead>
              <TableHead className="w-[60px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center">
                  <div className="flex items-center justify-center gap-2 text-muted-foreground">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Cargando programaciones...
                  </div>
                </TableCell>
              </TableRow>
            )}
            {schedules?.length === 0 && !isLoading && (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  No hay reportes programados aún.
                </TableCell>
              </TableRow>
            )}
            {schedules?.map((schedule) => (
              <TableRow key={schedule.id} className="group">
                <TableCell>
                  <div className="font-medium text-sm">{schedule.email_to}</div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground capitalize">
                      <Clock className="w-3 h-3"/> {schedule.frequency}
                  </div>
                </TableCell>
                <TableCell>
                  {schedule.is_active ? (
                    <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 text-xs">
                      Activo
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-xs">Inactivo</Badge>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground hidden md:table-cell text-xs">
                  {schedule.last_run_at ? new Date(schedule.last_run_at).toLocaleString("es-ES") : "Nunca"}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      id={`actions-${schedule.id}`}
                      className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity inline-flex items-center justify-center rounded-md text-sm hover:bg-accent hover:text-accent-foreground"
                    >
                      <span className="sr-only">Abrir menú</span>
                      <MoreHorizontal className="h-4 w-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                      
                      <DropdownMenuItem onClick={() => triggerMutation.mutate(schedule.id)}>
                        <Send className="w-4 h-4 mr-2" /> Forzar envío ahora
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      
                      <DropdownMenuItem
                        className="text-destructive focus:bg-destructive/10"
                        onClick={() => {
                          if (confirm("¿Eliminar esta programación?")) {
                            deleteMutation.mutate(schedule.id);
                          }
                        }}
                      >
                        <Trash2 className="w-4 h-4 mr-2" /> Eliminar
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Create Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-full sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Nueva Programación</SheetTitle>
            <SheetDescription>
              Configura un nuevo envío automático de reporte ejecutivo.
            </SheetDescription>
          </SheetHeader>

          <form id="schedule-form" onSubmit={handleSubmit} className="space-y-4 py-6">
            <div className="space-y-2">
              <Label htmlFor="s-email">Email Destinatario *</Label>
              <Input
                id="s-email"
                type="email"
                required
                placeholder="manager@empresa.com"
                value={form.email_to}
                onChange={(e) => setForm({ ...form, email_to: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="s-freq">Frecuencia</Label>
              <Select
                value={form.frequency}
                onValueChange={(val) => setForm({ ...form, frequency: val || "" })}
              >
                <SelectTrigger id="s-freq">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Diario</SelectItem>
                  <SelectItem value="weekly">Semanal</SelectItem>
                  <SelectItem value="monthly">Mensual</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <p className="text-xs text-muted-foreground pt-4">
                * El reporte se enviará por correo con la frecuencia indicada utilizando Celery Beat.
            </p>
          </form>

          <SheetFooter>
            <Button
              id="submit-schedule"
              type="submit"
              form="schedule-form"
              disabled={isMutating}
              className="w-full"
            >
              {isMutating && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Guardar Programación
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
