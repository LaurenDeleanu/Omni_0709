"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { OpsAPI, FacilityAsset, AssetBooking, VisitorLog, CalendarBooking, MaintenanceRequest, MaintenanceStats } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MapPin, Users, Plus, CheckCircle2, Monitor, Car, Briefcase, Calendar as CalendarIcon, Clock, ChevronLeft, ChevronRight, Wrench, LogOut, AlertTriangle, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { format, addHours, startOfWeek, addDays, parseISO, isSameDay } from "date-fns";
import { es } from "date-fns/locale";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

const ASSET_TYPES = ["all", "desk", "parking", "room", "equipment"] as const;
const ASSET_TYPE_LABELS: Record<string, string> = { all: "Todos", desk: "Escritorios", parking: "Parking", room: "Salas", equipment: "Equipos" };
const ASSET_TYPE_ICONS: Record<string, React.ReactNode> = {
  desk: <Monitor className="w-4 h-4" />,
  parking: <Car className="w-4 h-4" />,
  room: <Briefcase className="w-4 h-4" />,
  equipment: <Wrench className="w-4 h-4" />,
};
const ASSET_TYPE_COLORS: Record<string, string> = {
  desk: "bg-blue-500/20 border-blue-500/40 text-blue-300",
  parking: "bg-emerald-500/20 border-emerald-500/40 text-emerald-300",
  room: "bg-purple-500/20 border-purple-500/40 text-purple-300",
  equipment: "bg-amber-500/20 border-amber-500/40 text-amber-300",
};
const PRIORITY_COLORS: Record<string, string> = {
  low: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  medium: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  high: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
};
const STATUS_COLORS: Record<string, string> = {
  reported: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  in_progress: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  resolved: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  closed: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

const HOURS = Array.from({ length: 14 }, (_, i) => i + 7);

export default function OpsPage() {
  const [activeTab, setActiveTab] = useState("desks");
  const { user } = useUser();

  const tabs = [
    { key: "desks", icon: <MapPin className="w-4 h-4" />, label: "Hot-Desking & Reservas" },
    { key: "visitors", icon: <Users className="w-4 h-4" />, label: "Registro de Visitantes" },
    { key: "calendar", icon: <CalendarIcon className="w-4 h-4" />, label: "Calendario" },
    { key: "maintenance", icon: <Wrench className="w-4 h-4" />, label: "Mantenimiento" },
  ];

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Operaciones & Instalaciones</h1>
        <p className="text-muted-foreground mt-2">
          Gestiona reservas de puestos, recursos de la oficina y el registro de visitantes.
        </p>
      </div>

      <InlineCopilot
        moduleContext="ops"
        placeholder="Pregunta sobre operaciones o instalaciones..."
        quickActions={[
          { label: "Book a desk for today", message: "Book a desk for today" },
          { label: "Register a visitor", message: "Register a visitor" },
          { label: "Show today's scheduled visitors", message: "Show today's scheduled visitors" },
          { label: "Check room availability", message: "Check room availability" }
        ]}
      />

      <div className="flex border-b border-border/50 gap-6 overflow-x-auto pb-px">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 pb-4 px-1 text-sm font-semibold border-b-2 transition-all shrink-0 ${
              activeTab === tab.key ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground/80"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {activeTab === "desks" && <DesksTab userId={user?.id} />}
        {activeTab === "visitors" && <VisitorsTab userId={user?.id} />}
        {activeTab === "calendar" && <CalendarTab />}
        {activeTab === "maintenance" && <MaintenanceTab userId={user?.id} />}
      </div>
    </div>
  );
}

function DesksTab({ userId }: { userId?: string }) {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<FacilityAsset | null>(null);

  const { data: assets, isLoading: isLoadingAssets } = useQuery({
    queryKey: ["ops_assets"],
    queryFn: () => OpsAPI.getAssets(),
  });

  const { data: myBookings, isLoading: isLoadingBookings } = useQuery({
    queryKey: ["ops_bookings", userId],
    queryFn: () => OpsAPI.getBookings(userId),
    enabled: !!userId
  });

  const createBookingMutation = useMutation({
    mutationFn: (data: { asset_id: string, start_time: string, end_time: string }) => OpsAPI.createBooking({ ...data, employee_id: userId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops_bookings"] });
      toast.success("Reserva confirmada");
      setIsModalOpen(false);
      setSelectedAsset(null);
    },
    onError: (error: any) => {
      toast.error(error.message || "Error al realizar la reserva (posible solapamiento)");
    }
  });

  const handleBook = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedAsset) return;
    const formData = new FormData(e.currentTarget);
    const date = formData.get("date") as string;
    const startTimeStr = formData.get("start_time") as string;
    const hoursStr = formData.get("hours") as string;

    if (!date || !startTimeStr || !hoursStr) {
      toast.error("Rellena todos los campos");
      return;
    }

    const start = new Date(`${date}T${startTimeStr}:00`);
    const end = addHours(start, parseInt(hoursStr));

    createBookingMutation.mutate({
      asset_id: selectedAsset.id,
      start_time: start.toISOString(),
      end_time: end.toISOString()
    });
  };

  const getAssetIcon = (type: string) => {
    switch (type) {
      case 'desk': return <Monitor className="w-5 h-5 text-blue-500" />;
      case 'parking': return <Car className="w-5 h-5 text-emerald-500" />;
      case 'room': return <Briefcase className="w-5 h-5 text-purple-500" />;
      default: return <MapPin className="w-5 h-5 text-muted-foreground" />;
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h3 className="font-bold text-lg mb-4">Mis Reservas</h3>
        {isLoadingBookings ? (
          <div className="text-sm text-muted-foreground">Cargando reservas...</div>
        ) : myBookings?.length === 0 ? (
          <div className="p-4 rounded-xl border border-dashed border-border bg-card/30 text-center text-sm text-muted-foreground">
            No tienes reservas activas.
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {myBookings?.map((booking: AssetBooking) => {
              const asset = assets?.find((a: FacilityAsset) => a.id === booking.asset_id);
              return (
                <div key={booking.id} className="p-4 rounded-xl border border-border bg-card shadow-sm flex flex-col gap-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2">
                      {asset ? getAssetIcon(asset.type) : <MapPin className="w-4 h-4" />}
                      <span className="font-semibold">{asset?.name || "Recurso Desconocido"}</span>
                    </div>
                    <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-600 text-[10px] uppercase font-bold rounded">
                      {booking.status}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground flex flex-col gap-1.5">
                    <span className="flex items-center gap-1.5"><CalendarIcon className="w-3.5 h-3.5" /> {format(new Date(booking.start_time), "dd MMM yyyy")}</span>
                    <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> {format(new Date(booking.start_time), "HH:mm")} - {format(new Date(booking.end_time), "HH:mm")}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div>
        <h3 className="font-bold text-lg mb-4">Recursos Disponibles</h3>
        {isLoadingAssets ? (
          <div className="text-sm text-muted-foreground">Cargando recursos...</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-4">
            {assets?.map((asset: FacilityAsset) => (
              <Card key={asset.id} className="hover:shadow-md transition-shadow group">
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-center justify-between">
                    <div className="p-2 bg-muted rounded-lg group-hover:bg-primary/10 transition-colors">
                      {getAssetIcon(asset.type)}
                    </div>
                    {asset.status === 'available' ? (
                       <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    ) : (
                       <span className="w-2 h-2 rounded-full bg-red-500"></span>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-2">
                  <CardTitle className="text-base">{asset.name}</CardTitle>
                  <CardDescription className="text-xs mt-1">{asset.location || "Sin ubicación específica"}</CardDescription>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full mt-4"
                    disabled={asset.status !== 'available'}
                    onClick={() => {
                      setSelectedAsset(asset);
                      setIsModalOpen(true);
                    }}
                  >
                    Reservar
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reservar {selectedAsset?.name}</DialogTitle>
            <DialogDescription>Selecciona la fecha y hora para tu reserva.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleBook} className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Fecha</Label>
                <Input name="date" type="date" required />
              </div>
              <div className="space-y-2">
                <Label>Hora de Inicio</Label>
                <Input name="start_time" type="time" required />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Duración (Horas)</Label>
              <select name="hours" className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="1">1 Hora</option>
                <option value="2">2 Horas</option>
                <option value="4">Media Jornada (4h)</option>
                <option value="8">Jornada Completa (8h)</option>
              </select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={createBookingMutation.isPending}>Confirmar Reserva</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function VisitorsTab({ userId }: { userId?: string }) {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: visitors, isLoading } = useQuery({
    queryKey: ["ops_visitors"],
    queryFn: () => OpsAPI.getVisitors(),
  });

  const createVisitorMutation = useMutation({
    mutationFn: (data: any) => OpsAPI.createVisitor({ ...data, host_id: userId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops_visitors"] });
      toast.success("Visitante registrado");
      setIsModalOpen(false);
    }
  });

  const checkInMutation = useMutation({
    mutationFn: (id: string) => OpsAPI.updateVisitor(id, { status: "checked_in" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops_visitors"] });
      toast.success("Check-in realizado");
    }
  });

  const checkOutMutation = useMutation({
    mutationFn: (id: string) => OpsAPI.checkOutVisitor(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops_visitors"] });
      toast.success("Check-out realizado");
    }
  });

  const handleRegister = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createVisitorMutation.mutate({
      visitor_name: formData.get("name"),
      company: formData.get("company"),
      expected_arrival: new Date(`${formData.get("date")}T${formData.get("time")}:00`).toISOString()
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-card/40 p-4 rounded-xl border border-border/50">
        <div>
          <h3 className="font-bold text-lg text-foreground">Registro de Visitantes</h3>
          <p className="text-sm text-muted-foreground">Administra las visitas a las instalaciones.</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="bg-primary text-white">
          <Plus className="w-4 h-4 mr-2" /> Nuevo Visitante
        </Button>
      </div>

      <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted/50 text-muted-foreground text-xs uppercase font-semibold">
            <tr>
              <th className="px-6 py-4">Visitante</th>
              <th className="px-6 py-4">Empresa</th>
              <th className="px-6 py-4">Llegada Esperada</th>
              <th className="px-6 py-4">Estado</th>
              <th className="px-6 py-4 text-right">Acción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {isLoading ? (
              <tr><td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">Cargando...</td></tr>
            ) : visitors?.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">No hay visitantes esperados.</td></tr>
            ) : (
              visitors?.map((v: VisitorLog) => (
                <tr key={v.id} className="hover:bg-muted/20 transition-colors">
                  <td className="px-6 py-4 font-medium">{v.visitor_name}</td>
                  <td className="px-6 py-4 text-muted-foreground">{v.company || "-"}</td>
                  <td className="px-6 py-4">{format(new Date(v.expected_arrival), "dd/MM/yyyy HH:mm")}</td>
                  <td className="px-6 py-4">
                    {v.status === 'expected' && <span className="text-amber-600 bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400 px-2.5 py-1 rounded-full text-xs font-semibold">Esperado</span>}
                    {v.status === 'checked_in' && <span className="text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400 px-2.5 py-1 rounded-full text-xs font-semibold">En Oficina</span>}
                    {v.status === 'checked_out' && <span className="text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-400 px-2.5 py-1 rounded-full text-xs font-semibold">Salida</span>}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex gap-2 justify-end">
                      {v.status === 'expected' && (
                        <Button size="sm" variant="outline" onClick={() => checkInMutation.mutate(v.id)} disabled={checkInMutation.isPending}>
                          Check In
                        </Button>
                      )}
                      {v.status === 'checked_in' && (
                        <Button size="sm" variant="outline" onClick={() => checkOutMutation.mutate(v.id)} disabled={checkOutMutation.isPending}>
                          <LogOut className="w-3.5 h-3.5 mr-1" /> Check Out
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar Nuevo Visitante</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleRegister} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Nombre Completo</Label>
              <Input name="name" required placeholder="Ej: Maria Gonzalez" />
            </div>
            <div className="space-y-2">
              <Label>Empresa (Opcional)</Label>
              <Input name="company" placeholder="Ej: Acme Corp" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Fecha Esperada</Label>
                <Input name="date" type="date" required />
              </div>
              <div className="space-y-2">
                <Label>Hora Esperada</Label>
                <Input name="time" type="time" required />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={createVisitorMutation.isPending}>Registrar</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CalendarTab() {
  const queryClient = useQueryClient();
  const { user } = useUser();
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [assetFilter, setAssetFilter] = useState<string>("all");
  const [selectedSlot, setSelectedSlot] = useState<{ date: Date; hour: number } | null>(null);
  const [selectedBooking, setSelectedBooking] = useState<CalendarBooking | null>(null);

  const weekEnd = addDays(weekStart, 6);
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const startStr = format(weekStart, "yyyy-MM-dd");
  const endStr = format(weekEnd, "yyyy-MM-dd");

  const { data: bookings, isLoading } = useQuery({
    queryKey: ["ops_calendar_bookings", startStr, endStr, assetFilter],
    queryFn: () => OpsAPI.getCalendarBookings(startStr, endStr, assetFilter === "all" ? undefined : assetFilter),
  });

  const { data: assets } = useQuery({
    queryKey: ["ops_assets"],
    queryFn: () => OpsAPI.getAssets(),
  });

  const createBookingMutation = useMutation({
    mutationFn: (data: { asset_id: string; start_time: string; end_time: string }) =>
      OpsAPI.createBooking({ ...data, employee_id: user?.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops_calendar_bookings"] });
      queryClient.invalidateQueries({ queryKey: ["ops_bookings"] });
      toast.success("Reserva confirmada");
      setSelectedSlot(null);
    },
    onError: (error: any) => {
      toast.error(error.message || "Error al realizar la reserva");
    },
  });

  const goToPrevWeek = () => setWeekStart((prev) => addDays(prev, -7));
  const goToNextWeek = () => setWeekStart((prev) => addDays(prev, 7));

  const handleSlotClick = (date: Date, hour: number) => {
    setSelectedBooking(null);
    setSelectedSlot({ date, hour });
  };

  const handleBookingSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedSlot || !user?.id) return;
    const formData = new FormData(e.currentTarget);
    const assetId = formData.get("asset_id") as string;
    const hours = parseInt(formData.get("hours") as string) || 1;
    if (!assetId) {
      toast.error("Selecciona un recurso");
      return;
    }
    const start = new Date(selectedSlot.date);
    start.setHours(selectedSlot.hour, 0, 0, 0);
    const end = addHours(start, hours);
    createBookingMutation.mutate({
      asset_id: assetId,
      start_time: start.toISOString(),
      end_time: end.toISOString(),
    });
  };

  const bookingsForDay = (day: Date) => {
    if (!bookings) return [];
    return bookings.filter((b: CalendarBooking) => {
      const bStart = parseISO(b.start_time);
      return isSameDay(bStart, day);
    });
  };

  const getBookingStyle = (booking: CalendarBooking) => {
    const bStart = parseISO(booking.start_time);
    const bEnd = parseISO(booking.end_time);
    const startHour = bStart.getHours() + bStart.getMinutes() / 60;
    const endHour = bEnd.getHours() + bEnd.getMinutes() / 60;
    const top = ((startHour - 7) / 14) * 100;
    const height = ((endHour - startHour) / 14) * 100;
    return { top: `${top}%`, height: `calc(${height}% - 2px)` };
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={goToPrevWeek}>
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <span className="text-sm font-semibold min-w-[200px] text-center">
            {format(weekStart, "d MMM", { locale: es })} - {format(weekEnd, "d MMM yyyy", { locale: es })}
          </span>
          <Button variant="outline" size="sm" onClick={goToNextWeek}>
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex gap-1 flex-wrap">
          {ASSET_TYPES.map((t) => (
            <Button
              key={t}
              variant={assetFilter === t ? "default" : "outline"}
              size="sm"
              onClick={() => setAssetFilter(t)}
              className="text-xs h-8"
            >
              {ASSET_TYPE_LABELS[t]}
            </Button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-muted-foreground">Cargando reservas...</div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
          <div
            className="grid"
            style={{ gridTemplateColumns: "60px repeat(7, 1fr)" }}
          >
            <div className="border-b border-r border-border/50 p-2 bg-muted/30" />
            {weekDays.map((day) => (
              <div
                key={day.toISOString()}
                className={`border-b border-r border-border/50 p-2 text-center bg-muted/30 ${
                  isSameDay(day, new Date()) ? "bg-primary/10" : ""
                }`}
              >
                <div className="text-xs text-muted-foreground">
                  {format(day, "EEE", { locale: es })}
                </div>
                <div
                  className={`text-lg font-bold ${
                    isSameDay(day, new Date()) ? "text-primary" : ""
                  }`}
                >
                  {format(day, "d")}
                </div>
              </div>
            ))}

            {HOURS.map((hour) => (
              <div key={hour} className="contents">
                <div className="border-r border-b border-border/50 p-1.5 text-xs text-muted-foreground text-right pr-2 bg-muted/20">
                  {`${hour.toString().padStart(2, "0")}:00`}
                </div>
                {weekDays.map((day) => {
                  const dayBookings = bookingsForDay(day);
                  const hourBookings = dayBookings.filter((b: CalendarBooking) => {
                    const bStart = parseISO(b.start_time);
                    return bStart.getHours() === hour;
                  });
                  return (
                    <div
                      key={`${day.toISOString()}-${hour}`}
                      className="relative border-r border-b border-border/50 min-h-[48px] cursor-pointer hover:bg-muted/20 transition-colors"
                      onClick={() => handleSlotClick(day, hour)}
                    >
                      {hourBookings.map((booking: CalendarBooking) => (
                        <div
                          key={booking.id}
                          className={`absolute left-0.5 right-0.5 rounded px-1 py-0.5 border text-[10px] leading-tight overflow-hidden cursor-pointer z-10 hover:brightness-125 transition-all ${
                            ASSET_TYPE_COLORS[booking.asset_type || ""] || "bg-muted text-muted-foreground"
                          }`}
                          style={getBookingStyle(booking)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedBooking(booking);
                            setSelectedSlot(null);
                          }}
                        >
                          <div className="font-semibold truncate">{booking.asset_name}</div>
                          <div className="truncate opacity-80">
                            {format(parseISO(booking.start_time), "HH:mm")} - {format(parseISO(booking.end_time), "HH:mm")}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      <Dialog open={!!selectedSlot} onOpenChange={() => setSelectedSlot(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva Reserva</DialogTitle>
            <DialogDescription>
              {selectedSlot && format(selectedSlot.date, "EEEE d MMMM yyyy", { locale: es })} a las {selectedSlot?.hour}:00
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleBookingSubmit} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Recurso</Label>
              <select
                name="asset_id"
                required
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Seleccionar recurso...</option>
                {assets
                  ?.filter((a: FacilityAsset) => assetFilter === "all" || a.type === assetFilter)
                  .map((a: FacilityAsset) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.type})
                    </option>
                  ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Duración (Horas)</Label>
              <select
                name="hours"
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="1">1 Hora</option>
                <option value="2">2 Horas</option>
                <option value="4">Media Jornada (4h)</option>
                <option value="8">Jornada Completa (8h)</option>
              </select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setSelectedSlot(null)}>Cancelar</Button>
              <Button type="submit" disabled={createBookingMutation.isPending}>Reservar</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!selectedBooking} onOpenChange={() => setSelectedBooking(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Detalles de la Reserva</DialogTitle>
          </DialogHeader>
          {selectedBooking && (
            <div className="space-y-3 py-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="text-muted-foreground">Recurso:</div>
                <div className="font-medium">{selectedBooking.asset_name}</div>
                <div className="text-muted-foreground">Tipo:</div>
                <div>{ASSET_TYPE_LABELS[selectedBooking.asset_type || ""] || selectedBooking.asset_type}</div>
                <div className="text-muted-foreground">Empleado:</div>
                <div>{selectedBooking.employee_name}</div>
                <div className="text-muted-foreground">Fecha:</div>
                <div>{format(parseISO(selectedBooking.start_time), "dd/MM/yyyy")}</div>
                <div className="text-muted-foreground">Horario:</div>
                <div>{format(parseISO(selectedBooking.start_time), "HH:mm")} - {format(parseISO(selectedBooking.end_time), "HH:mm")}</div>
                <div className="text-muted-foreground">Estado:</div>
                <div>
                  <Badge variant="outline">{selectedBooking.status}</Badge>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedBooking(null)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function MaintenanceTab({ userId }: { userId?: string }) {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const { data: requests, isLoading } = useQuery({
    queryKey: ["ops_maintenance", statusFilter],
    queryFn: () => OpsAPI.getMaintenanceRequests(statusFilter || undefined),
  });

  const { data: stats } = useQuery({
    queryKey: ["ops_maintenance_stats"],
    queryFn: () => OpsAPI.getMaintenanceStats(),
  });

  const { data: assets } = useQuery({
    queryKey: ["ops_assets"],
    queryFn: () => OpsAPI.getAssets(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { title: string; description?: string; asset_id?: string; priority?: string }) =>
      OpsAPI.createMaintenanceRequest({ ...data, reported_by_id: userId || "" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops_maintenance"] });
      queryClient.invalidateQueries({ queryKey: ["ops_maintenance_stats"] });
      toast.success("Solicitud de mantenimiento creada");
      setIsModalOpen(false);
    },
    onError: (error: any) => {
      toast.error(error.message || "Error al crear la solicitud");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      OpsAPI.updateMaintenanceRequest(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ops_maintenance"] });
      queryClient.invalidateQueries({ queryKey: ["ops_maintenance_stats"] });
      toast.success("Solicitud actualizada");
    },
    onError: (error: any) => {
      toast.error(error.message || "Error al actualizar la solicitud");
    },
  });

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createMutation.mutate({
      title: formData.get("title") as string,
      description: (formData.get("description") as string) || "",
      asset_id: (formData.get("asset_id") as string) || undefined,
      priority: (formData.get("priority") as string) || "medium",
    });
  };

  const handleResolve = (id: string) => {
    const notes = prompt("Notas de resolución (opcional):");
    updateMutation.mutate({
      id,
      data: { status: "resolved", resolution_notes: notes || "" },
    });
  };

  const getAssetName = (assetId?: string) => {
    if (!assetId || !assets) return null;
    return assets.find((a: FacilityAsset) => a.id === assetId)?.name;
  };

  const statCards = [
    { label: "Total", value: stats?.total ?? 0, color: "text-foreground" },
    { label: "Reportadas", value: stats?.reported ?? 0, color: "text-slate-400" },
    { label: "En Progreso", value: stats?.in_progress ?? 0, color: "text-blue-400" },
    { label: "Resueltas", value: (stats?.resolved ?? 0) + (stats?.closed ?? 0), color: "text-emerald-400" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <Card key={card.label} size="sm">
            <CardContent className="p-4 text-center">
              <div className={`text-2xl font-extrabold ${card.color}`}>{card.value}</div>
              <div className="text-xs text-muted-foreground mt-1">{card.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-between items-center bg-card/40 p-4 rounded-xl border border-border/50">
        <div>
          <h3 className="font-bold text-lg text-foreground">Solicitudes de Mantenimiento</h3>
          <p className="text-sm text-muted-foreground">Gestiona incidencias y tareas de mantenimiento.</p>
        </div>
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">Todos los estados</option>
            <option value="reported">Reportado</option>
            <option value="in_progress">En Progreso</option>
            <option value="resolved">Resuelto</option>
            <option value="closed">Cerrado</option>
          </select>
          <Button onClick={() => setIsModalOpen(true)} disabled={!userId}>
            <Plus className="w-4 h-4 mr-2" /> Nueva Solicitud
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando solicitudes...</div>
        ) : requests?.length === 0 ? (
          <div className="p-8 rounded-xl border border-dashed border-border bg-card/30 text-center text-sm text-muted-foreground">
            No hay solicitudes de mantenimiento.
          </div>
        ) : (
          requests?.map((req: MaintenanceRequest) => {
            const isExpanded = expandedId === req.id;
            const assetName = getAssetName(req.asset_id);
            return (
              <div key={req.id} className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
                <div
                  className="p-4 flex items-start justify-between cursor-pointer hover:bg-muted/10 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : req.id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="font-semibold">{req.title}</span>
                      {assetName && (
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">{assetName}</span>
                      )}
                      <Badge variant="outline" className={PRIORITY_COLORS[req.priority] || ""}>
                        {req.priority === "critical" && <AlertTriangle className="w-3 h-3 mr-1" />}
                        {req.priority}
                      </Badge>
                      <Badge variant="outline" className={STATUS_COLORS[req.status] || ""}>
                        {req.status === "reported" && "Reportado"}
                        {req.status === "in_progress" && "En Progreso"}
                        {req.status === "resolved" && "Resuelto"}
                        {req.status === "closed" && "Cerrado"}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1.5">
                      {format(new Date(req.created_at), "dd/MM/yyyy HH:mm")}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-3 shrink-0">
                    {req.status === "in_progress" && (
                      <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); handleResolve(req.id); }}>
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Resolver
                      </Button>
                    )}
                    <span className="text-muted-foreground">
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </span>
                  </div>
                </div>
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-border/50 pt-3 space-y-2 text-sm">
                    {req.description && (
                      <div>
                        <span className="text-muted-foreground">Descripción:</span>
                        <p className="mt-1 text-foreground/80">{req.description}</p>
                      </div>
                    )}
                    {req.assigned_to_id && (
                      <div>
                        <span className="text-muted-foreground">Asignado a:</span>
                        <span className="ml-2">{req.assigned_to_id}</span>
                      </div>
                    )}
                    {req.resolution_notes && (
                      <div>
                        <span className="text-muted-foreground">Notas de resolución:</span>
                        <p className="mt-1 text-foreground/80">{req.resolution_notes}</p>
                      </div>
                    )}
                    {req.resolved_at && (
                      <div>
                        <span className="text-muted-foreground">Resuelto:</span>
                        <span className="ml-2">{format(new Date(req.resolved_at), "dd/MM/yyyy HH:mm")}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva Solicitud de Mantenimiento</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Título</Label>
              <Input name="title" required placeholder="Ej: Aire acondicionado no funciona" />
            </div>
            <div className="space-y-2">
              <Label>Descripción</Label>
              <textarea
                name="description"
                rows={3}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                placeholder="Describe el problema..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Recurso (opcional)</Label>
                <select
                  name="asset_id"
                  className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">Sin recurso específico</option>
                  {assets?.map((a: FacilityAsset) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Prioridad</Label>
                <select
                  name="priority"
                  defaultValue="medium"
                  className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="low">Baja</option>
                  <option value="medium">Media</option>
                  <option value="high">Alta</option>
                  <option value="critical">Crítica</option>
                </select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={createMutation.isPending}>Crear Solicitud</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
