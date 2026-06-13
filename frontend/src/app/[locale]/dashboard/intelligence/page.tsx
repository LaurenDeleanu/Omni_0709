"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { IntelAPI, Dashboard, DashboardWidget } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, LayoutGrid, BarChart2, Activity, X, PieChart as PieChartIcon } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { API_BASE } from "@/lib/api/client";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

export default function IntelligencePage() {
  const { user } = useUser();
  const queryClient = useQueryClient();
  const [activeDashboard, setActiveDashboard] = useState<Dashboard | null>(null);
  const [isNewDashboardModalOpen, setIsNewDashboardModalOpen] = useState(false);

  const { data: dashboards, isLoading: isLoadingDashboards } = useQuery({
    queryKey: ["intel_dashboards"],
    queryFn: () => IntelAPI.getDashboards(),
  });

  useEffect(() => {
    if (dashboards && dashboards.length > 0 && !activeDashboard) {
      setActiveDashboard(dashboards[0]);
    }
  }, [dashboards, activeDashboard]);

  const createDashboardMutation = useMutation({
    mutationFn: (data: any) => IntelAPI.createDashboard({ ...data, owner_id: user?.id }),
    onSuccess: (newDash) => {
      queryClient.invalidateQueries({ queryKey: ["intel_dashboards"] });
      setActiveDashboard(newDash);
      setIsNewDashboardModalOpen(false);
      toast.success("Dashboard creado");
    }
  });

  const handleCreateDashboard = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createDashboardMutation.mutate({
      name: formData.get("name"),
      description: formData.get("description")
    });
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header & Tabs */}
      <div className="border-b border-border bg-card/50 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4 overflow-x-auto custom-scrollbar pb-1">
          <div className="font-bold mr-4 text-lg flex items-center gap-2">
            <LayoutGrid className="w-5 h-5 text-primary" /> BI Center
          </div>
          {dashboards?.map((dash: Dashboard) => (
            <button
              key={dash.id}
              onClick={() => setActiveDashboard(dash)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
                activeDashboard?.id === dash.id 
                ? "bg-primary text-primary-foreground" 
                : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {dash.name}
            </button>
          ))}
          <Button 
            variant="ghost" 
            size="sm" 
            className="rounded-full px-3 text-muted-foreground"
            onClick={() => setIsNewDashboardModalOpen(true)}
          >
            <Plus className="w-4 h-4 mr-1" /> Nuevo
          </Button>
        </div>
      </div>

      <InlineCopilot
        moduleContext="intelligence"
        placeholder="Pregunta sobre análisis de datos y BI..."
        quickActions={[
          { label: "Analizar tendencias de plantilla", message: "Analizar tendencias de plantilla" },
          { label: "Dashboard de rotación", message: "Dashboard de rotación" },
          { label: "Comparativa salarial por depto.", message: "Comparativa salarial por depto." },
          { label: "Resumen ejecutivo mensual", message: "Resumen ejecutivo mensual" },
        ]}
      />

      {/* Main Board */}
      <div className="flex-1 overflow-auto p-6 bg-muted/10">
        {activeDashboard ? (
          <DashboardViewer dashboard={activeDashboard} />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <Activity className="w-12 h-12 mb-4 opacity-20" />
            <p>Crea tu primer Dashboard para comenzar</p>
          </div>
        )}
      </div>

      <Dialog open={isNewDashboardModalOpen} onOpenChange={setIsNewDashboardModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo Dashboard</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateDashboard} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Nombre del Dashboard</Label>
              <Input name="name" required placeholder="Ej: OKRs Q3" />
            </div>
            <div className="space-y-2">
              <Label>Descripción</Label>
              <Input name="description" placeholder="Métricas principales..." />
            </div>
            <DialogFooter>
              <Button type="submit" disabled={createDashboardMutation.isPending}>Crear Dashboard</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function DashboardViewer({ dashboard }: { dashboard: Dashboard }) {
  const queryClient = useQueryClient();
  const [isWidgetModalOpen, setIsWidgetModalOpen] = useState(false);

  const createWidgetMutation = useMutation({
    mutationFn: (data: any) => IntelAPI.createWidget({ ...data, dashboard_id: dashboard.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intel_dashboards"] });
      setIsWidgetModalOpen(false);
      toast.success("Widget añadido");
    }
  });

  const handleAddWidget = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const widgetType = formData.get("widget_type") as string;
    
    // Auto-size based on type
    let w = 1, h = 1;
    if (widgetType === "bar_chart" || widgetType === "line_chart") {
      w = 2; h = 2;
    } else if (widgetType === "pie_chart") {
      w = 1; h = 2;
    }

    createWidgetMutation.mutate({
      title: formData.get("title"),
      widget_type: widgetType,
      data_source: formData.get("data_source"),
      layout_w: w,
      layout_h: h
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">{dashboard.name}</h2>
          <p className="text-muted-foreground">{dashboard.description}</p>
        </div>
        <Button onClick={() => setIsWidgetModalOpen(true)}>
          <Plus className="w-4 h-4 mr-2" /> Añadir Widget
        </Button>
      </div>

      {dashboard.widgets?.length === 0 ? (
        <div className="border-2 border-dashed border-border rounded-xl h-64 flex flex-col items-center justify-center text-muted-foreground">
          <p>El dashboard está vacío. Añade widgets para visualizar datos.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 auto-rows-[140px]">
          {dashboard.widgets?.map((widget) => (
            <WidgetRenderer key={widget.id} widget={widget} />
          ))}
        </div>
      )}

      <Dialog open={isWidgetModalOpen} onOpenChange={setIsWidgetModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Añadir Widget</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddWidget} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Título del Widget</Label>
              <Input name="title" required placeholder="Ej: Ingresos Mensuales" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipo de Gráfico</Label>
                <select name="widget_type" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-ring">
                  <option value="stat_card">Tarjeta (KPI)</option>
                  <option value="bar_chart">Gráfico de Barras</option>
                  <option value="line_chart">Gráfico de Líneas</option>
                  <option value="pie_chart">Gráfico Circular</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Fuente de Datos</Label>
                <select name="data_source" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-ring">
                  {DATA_SOURCES.map(ds => (
                    <option key={ds.value} value={ds.value}>{ds.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={createWidgetMutation.isPending}>Guardar Widget</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function WidgetRenderer({ widget }: { widget: DashboardWidget }) {
  const queryClient = useQueryClient();
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["intel_data", widget.data_source],
    queryFn: () => IntelAPI.getWidgetData(widget.data_source),
  });

  const deleteMutation = useMutation({
    mutationFn: () => IntelAPI.deleteWidget(widget.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intel_dashboards"] });
      toast.success("Widget eliminado");
    }
  });

  const createAlertMutation = useMutation({
    mutationFn: async (data: any) => {
      const token = localStorage.getItem("local_access_token");
      const res = await fetch(`${API_BASE}/intel/widgets/${widget.id}/alerts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error("Fallo al crear alerta");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Alerta KPI configurada", { description: "Se enviará notificación Push al superar el umbral." });
      setIsAlertModalOpen(false);
    }
  });

  const handleCreateAlert = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createAlertMutation.mutate({
      condition: formData.get("condition"),
      threshold: parseInt(formData.get("threshold") as string, 10)
    });
  };

  // Calculate grid spans based on layout_w and layout_h
  const getColSpan = (w: number) => {
    switch (w) {
      case 2: return "md:col-span-2 xl:col-span-2";
      case 3: return "md:col-span-3 xl:col-span-3";
      case 4: return "md:col-span-4 xl:col-span-4";
      default: return "col-span-1";
    }
  };
  const getRowSpan = (h: number) => {
    switch (h) {
      case 2: return "row-span-2";
      case 3: return "row-span-3";
      default: return "row-span-1";
    }
  };

  return (
    <Card className={`relative group ${getColSpan(widget.layout_w || 1)} ${getRowSpan(widget.layout_h || 1)} overflow-hidden flex flex-col`}>
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 flex gap-1">
        <button 
          onClick={() => setIsAlertModalOpen(true)}
          title="Configurar Alerta KPI"
          className="p-1.5 bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20 rounded-md"
        >
          <BellRing className="w-3.5 h-3.5" />
        </button>
        <button 
          onClick={() => deleteMutation.mutate()}
          className="p-1.5 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-md"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <CardHeader className="pb-2 pt-4 px-4 shrink-0">
        <CardTitle className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
          {widget.widget_type === 'stat_card' && <Activity className="w-4 h-4" />}
          {widget.widget_type === 'bar_chart' && <BarChart2 className="w-4 h-4" />}
          {widget.widget_type === 'line_chart' && <Activity className="w-4 h-4" />}
          {widget.widget_type === 'pie_chart' && <PieChartIcon className="w-4 h-4" />}
          {widget.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 flex-1 flex flex-col justify-center">
        {isLoading ? (
          <div className="animate-pulse bg-muted rounded w-full h-full min-h-[60px]" />
        ) : (
          <WidgetChart type={widget.widget_type} data={data} />
        )}
      </CardContent>

      <Dialog open={isAlertModalOpen} onOpenChange={setIsAlertModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configurar Alerta de KPI</DialogTitle>
            <DialogDescription>
              Recibirás una notificación Push cuando el valor de <b>{widget.title}</b> cruce el umbral establecido.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateAlert} className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Condición</Label>
                <select name="condition" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-ring">
                  <option value=">">Mayor que {'>'}</option>
                  <option value="<">Menor que {'<'}</option>
                  <option value="==">Igual a {'=='}</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Umbral (Valor)</Label>
                <Input name="threshold" type="number" required placeholder="Ej: 1000" />
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={createAlertMutation.isPending}>Crear Alerta</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

import { 
  ResponsiveContainer, 
  BarChart, Bar, 
  LineChart, Line, 
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend 
} from "recharts";
import { BellRing } from "lucide-react";

// --- Form data for Widget Dialog ---
const DATA_SOURCES = [
  { value: "headcount_forecasting", label: "Headcount & Forecasting" },
  { value: "cost_per_hire", label: "Cost-per-Hire Analytics" },
  { value: "training_roi", label: "Training ROI" },
  { value: "department_pl", label: "Department P&L" },
  { value: "sales_revenue", label: "Sales Revenue" },
  { value: "employee_count", label: "Total Headcount (Stat)" },
  { value: "task_completion", label: "Task Status Distribution" }
];

function WidgetChart({ type, data }: { type: string, data: any }) {
  if (!data) return null;

  if (type === 'stat_card') {
    return (
      <div>
        <div className="text-3xl font-bold">{data.total || data.data?.[0] || 0}</div>
        {(data.growth || data.labels) && (
          <p className="text-xs text-emerald-500 mt-1 font-medium">{data.growth || "Último periodo"}</p>
        )}
      </div>
    );
  }

  // Format data for Recharts: [{ name: label, value: data }]
  const chartData = data.labels?.map((label: string, i: number) => ({
    name: label,
    value: data.data[i]
  })) || [];

  const COLORS = ["hsl(var(--primary))", "hsl(var(--primary) / 0.7)", "hsl(var(--primary) / 0.4)", "hsl(var(--primary) / 0.2)"];

  if (type === 'bar_chart') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} dy={10} />
          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} />
          <Tooltip 
            cursor={{ fill: "hsl(var(--muted))" }}
            contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "8px" }}
            itemStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  
  if (type === 'line_chart') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} dy={10} />
          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} />
          <Tooltip 
            contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "8px" }}
            itemStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ r: 4, fill: "hsl(var(--primary))" }} activeDot={{ r: 6 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (type === 'pie_chart') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={5}
            dataKey="value"
          >
            {chartData.map((entry: any, index: number) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "8px" }}
            itemStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return <div>Visualización no soportada</div>;
}
