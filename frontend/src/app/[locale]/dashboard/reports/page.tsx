"use client";

import { useQuery } from "@tanstack/react-query";
import { ReportAPI, DashboardData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Plus, X, ChevronUp, ChevronDown, RefreshCw, Download, FileText,
  FileSpreadsheet, Users, Building2, TrendingUp, Clock, Receipt,
  UserPlus, Loader2, LayoutGrid, BarChart3, CalendarClock,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "@/i18n/routing";
import { InlineCopilot } from "@/components/ai/InlineCopilot";

const STORAGE_KEY = "sas_reports_widgets";

interface WidgetConfig {
  id: string;
  type: WidgetType;
  order: number;
  autoRefresh: boolean;
}

type WidgetType =
  | "headcount"
  | "departments"
  | "turnover"
  | "attendance"
  | "cost"
  | "recent_hires"
  | "export";

const WIDGET_META: Record<WidgetType, { title: string; icon: React.ReactNode; metrics: string[] }> = {
  headcount: { title: "Headcount Overview", icon: <Users className="w-4 h-4" />, metrics: ["headcount"] },
  departments: { title: "Department Distribution", icon: <Building2 className="w-4 h-4" />, metrics: ["departments"] },
  turnover: { title: "Turnover Trend", icon: <TrendingUp className="w-4 h-4" />, metrics: ["turnover"] },
  attendance: { title: "Attendance", icon: <Clock className="w-4 h-4" />, metrics: ["attendance"] },
  cost: { title: "Cost Overview", icon: <Receipt className="w-4 h-4" />, metrics: ["cost"] },
  recent_hires: { title: "Recent Hires", icon: <UserPlus className="w-4 h-4" />, metrics: ["headcount"] },
  export: { title: "Quick Export", icon: <Download className="w-4 h-4" />, metrics: [] },
};

function saveWidgets(widgets: WidgetConfig[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(widgets));
}

function getDefaultWidgets(): WidgetConfig[] {
  return [
    { id: "w1", type: "headcount", order: 0, autoRefresh: false },
    { id: "w2", type: "departments", order: 1, autoRefresh: false },
    { id: "w3", type: "turnover", order: 2, autoRefresh: false },
    { id: "w4", type: "attendance", order: 3, autoRefresh: false },
    { id: "w5", type: "cost", order: 4, autoRefresh: false },
    { id: "w6", type: "recent_hires", order: 5, autoRefresh: false },
    { id: "w7", type: "export", order: 6, autoRefresh: false },
  ];
}

function getAvailableTypes(active: WidgetConfig[]): WidgetType[] {
  const activeTypes = new Set(active.map((w) => w.type));
  return (Object.keys(WIDGET_META) as WidgetType[]).filter((t) => !activeTypes.has(t));
}

const BAR_COLORS = [
  "from-indigo-500 to-blue-600",
  "from-emerald-500 to-teal-600",
  "from-amber-500 to-orange-600",
  "from-rose-500 to-pink-600",
  "from-violet-500 to-purple-600",
  "from-cyan-500 to-sky-600",
  "from-lime-500 to-green-600",
  "from-fuchsia-500 to-pink-600",
];

export default function ReportsPage() {
  const [widgets, setWidgets] = useState<WidgetConfig[]>(() => {
    if (typeof window === "undefined") return getDefaultWidgets();
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {}
    return getDefaultWidgets();
  });
  const [showPanel, setShowPanel] = useState(false);

  useEffect(() => {
    saveWidgets(widgets);
  }, [widgets]);

  const activeMetrics = [...new Set(widgets.flatMap((w) => WIDGET_META[w.type]?.metrics || []))];

  const {
    data: dashData,
    isLoading,
    refetch,
  } = useQuery<DashboardData>({
    queryKey: ["reports-dashboard-data", activeMetrics.sort().join(",")],
    queryFn: () => ReportAPI.getDashboardData(activeMetrics),
    enabled: activeMetrics.length > 0,
    refetchInterval: 60000,
  });

  const moveWidget = useCallback((id: string, direction: -1 | 1) => {
    setWidgets((prev) => {
      const sorted = [...prev].sort((a, b) => a.order - b.order);
      const idx = sorted.findIndex((w) => w.id === id);
      if (idx === -1) return prev;
      const target = idx + direction;
      if (target < 0 || target >= sorted.length) return prev;
      [sorted[idx], sorted[target]] = [sorted[target], sorted[idx]];
      return sorted.map((w, i) => ({ ...w, order: i }));
    });
  }, []);

  const removeWidget = useCallback((id: string) => {
    setWidgets((prev) => {
      const filtered = prev.filter((w) => w.id !== id);
      return filtered.map((w, i) => ({ ...w, order: i }));
    });
  }, []);

  const addWidget = useCallback((type: WidgetType) => {
    setWidgets((prev) => {
      const maxOrder = prev.reduce((max, w) => Math.max(max, w.order), -1);
      const id = `w${Date.now()}`;
      return [...prev, { id, type, order: maxOrder + 1, autoRefresh: false }];
    });
    setShowPanel(false);
  }, []);

  const toggleAutoRefresh = useCallback((id: string) => {
    setWidgets((prev) => prev.map((w) => (w.id === id ? { ...w, autoRefresh: !w.autoRefresh } : w)));
  }, []);

  const sortedWidgets = [...widgets].sort((a, b) => a.order - b.order);
  const available = getAvailableTypes(widgets);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Informes</h2>
          <p className="text-sm text-muted-foreground mt-1">Dashboard builder — add, reorder, and customize report widgets.</p>
        </div>
        <div className="flex items-center gap-2">
          {available.length > 0 && (
            <Button variant="outline" className="gap-2" onClick={() => setShowPanel(!showPanel)}>
              <Plus className="w-4 h-4" />
              Add Widget
            </Button>
          )}
          <Link href="/dashboard/reports/schedules">
            <Button variant="ghost" className="gap-2">
              <CalendarClock className="w-4 h-4" />
              Programados
            </Button>
          </Link>
        </div>
      </div>

      <InlineCopilot
        moduleContext="reports"
        placeholder="Pregunta sobre informes o reportes..."
        quickActions={[
          { label: "Generate executive summary", message: "Generate executive summary" },
          { label: "Show headcount by department", message: "Show headcount by department" },
          { label: "Export employee list", message: "Export employee list" },
          { label: "Compare turnover rates", message: "Compare turnover rates" },
        ]}
      />

      {showPanel && available.length > 0 && (
        <div className="bg-slate-950 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <LayoutGrid className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Available Widgets</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {available.map((type) => (
              <Button
                key={type}
                variant="outline"
                size="sm"
                className="gap-2 border-zinc-700 hover:border-zinc-500 hover:bg-slate-800"
                onClick={() => addWidget(type)}
              >
                {WIDGET_META[type].icon}
                {WIDGET_META[type].title}
              </Button>
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading widgets...
        </div>
      )}

      {!isLoading && (
        <div className="grid gap-4 md:grid-cols-2">
          {sortedWidgets.map((widget, idx) => (
            <WidgetCard
              key={widget.id}
              config={widget}
              data={dashData}
              isLoading={isLoading}
              isFirst={idx === 0}
              isLast={idx === sortedWidgets.length - 1}
              onMoveUp={() => moveWidget(widget.id, -1)}
              onMoveDown={() => moveWidget(widget.id, 1)}
              onRemove={() => removeWidget(widget.id)}
              onRefresh={() => refetch()}
              onToggleAutoRefresh={() => toggleAutoRefresh(widget.id)}
            />
          ))}
        </div>
      )}

      {!isLoading && sortedWidgets.length === 0 && (
        <div className="text-center py-16 border border-dashed border-zinc-800 rounded-xl">
          <BarChart3 className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
          <p className="text-muted-foreground text-sm mb-3">No widgets active</p>
          <Button variant="outline" className="gap-2" onClick={() => setShowPanel(true)}>
            <Plus className="w-4 h-4" />
            Add Widget
          </Button>
        </div>
      )}
    </div>
  );
}

function WidgetCard({
  config,
  data,
  isLoading,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
  onRemove,
  onRefresh,
  onToggleAutoRefresh,
}: {
  config: WidgetConfig;
  data: DashboardData | undefined;
  isLoading: boolean;
  isFirst: boolean;
  isLast: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onRemove: () => void;
  onRefresh: () => void;
  onToggleAutoRefresh: () => void;
}) {
  const meta = WIDGET_META[config.type];

  return (
    <div className="border border-zinc-800 bg-slate-900 rounded-xl flex flex-col">
      <div className="flex items-center gap-1 px-4 py-3 border-b border-zinc-800">
        <span className="w-4 h-4 text-zinc-500">{meta.icon}</span>
        <span className="text-sm font-medium flex-1">{meta.title}</span>
        <button
          onClick={onToggleAutoRefresh}
          className={`p-1 rounded transition-colors ${config.autoRefresh ? "text-emerald-400 bg-emerald-500/10" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"}`}
          title={config.autoRefresh ? "Auto-refresh: ON" : "Auto-refresh: OFF"}
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
        <button onClick={onRefresh} className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800" title="Refresh widget">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
        {!isFirst && (
          <button onClick={onMoveUp} className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800" title="Move up">
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
        )}
        {!isLast && (
          <button onClick={onMoveDown} className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800" title="Move down">
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
        )}
        <button onClick={onRemove} className="p-1 rounded text-zinc-500 hover:text-red-400 hover:bg-red-500/10" title="Remove widget">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="p-4 flex-1 min-h-[180px]">
        <WidgetContent type={config.type} data={data} isLoading={isLoading} />
      </div>
    </div>
  );
}

function WidgetContent({
  type,
  data,
  isLoading,
}: {
  type: WidgetType;
  data: DashboardData | undefined;
  isLoading: boolean;
}) {
  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center h-full min-h-[140px] text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  switch (type) {
    case "headcount":
      return <HeadcountContent data={data} />;
    case "departments":
      return <DepartmentsContent data={data} />;
    case "turnover":
      return <TurnoverContent data={data} />;
    case "attendance":
      return <AttendanceContent data={data} />;
    case "cost":
      return <CostContent data={data} />;
    case "recent_hires":
      return <RecentHiresContent data={data} />;
    case "export":
      return <ExportContent />;
    default:
      return <p className="text-muted-foreground text-sm">No data available</p>;
  }
}

function HeadcountContent({ data }: { data: DashboardData }) {
  const hc = data.headcount;
  if (!hc) return <p className="text-muted-foreground text-sm">No headcount data</p>;

  const depts = (hc.by_department || []).slice(0, 5);
  const maxDept = Math.max(...depts.map((d) => d.count), 1);

  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold text-white">{hc.total}</span>
        <span className="text-sm text-muted-foreground">total employees</span>
      </div>
      <div className="flex gap-4 text-sm">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-muted-foreground">Active:</span>
          <span className="font-medium text-white">{hc.active}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span className="text-muted-foreground">Inactive:</span>
          <span className="font-medium text-white">{hc.inactive}</span>
        </span>
      </div>
      {depts.length > 0 && (
        <div className="space-y-2 pt-2">
          {depts.map((d, i) => (
            <div key={d.name} className="flex items-center gap-2">
              <span className="text-xs text-zinc-400 w-24 truncate" title={d.name}>{d.name}</span>
              <div className="flex-1 bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${BAR_COLORS[i % BAR_COLORS.length]}`}
                  style={{ width: `${(d.count / maxDept) * 100}%` }}
                />
              </div>
              <span className="text-xs text-zinc-500 w-8 text-right">{d.count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DepartmentsContent({ data }: { data: DashboardData }) {
  const depts = data.departments || [];
  if (depts.length === 0) return <p className="text-muted-foreground text-sm">No department data</p>;

  const maxCount = Math.max(...depts.map((d) => d.count), 1);

  return (
    <div className="space-y-2.5">
      {depts.slice(0, 6).map((d, i) => (
        <div key={d.name} className="flex items-center gap-2.5">
          <span className="text-xs text-zinc-400 w-28 truncate" title={d.name}>{d.name}</span>
          <div className="flex-1 bg-zinc-800 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${BAR_COLORS[i % BAR_COLORS.length]}`}
              style={{ width: `${(d.count / maxCount) * 100}%` }}
            />
          </div>
          <span className="text-xs text-zinc-500 w-14 text-right">{d.count} ({d.percentage}%)</span>
        </div>
      ))}
    </div>
  );
}

function TurnoverContent({ data }: { data: DashboardData }) {
  const to = data.turnover;
  if (!to) return <p className="text-muted-foreground text-sm">No turnover data</p>;

  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold text-amber-400">{to.rate}%</span>
        <span className="text-sm text-muted-foreground">inactive rate</span>
      </div>
      <div className="flex gap-6 text-sm">
        <div className="flex flex-col">
          <span className="text-emerald-400 font-bold text-lg">{to.active}</span>
          <span className="text-xs text-zinc-500">Active</span>
        </div>
        <div className="flex flex-col">
          <span className="text-amber-400 font-bold text-lg">{to.inactive}</span>
          <span className="text-xs text-zinc-500">Archived</span>
        </div>
      </div>
      <div className="flex gap-1 items-end h-10 mt-1">
        <div
          className="bg-gradient-to-t from-emerald-500 to-emerald-400 rounded-t-sm w-full"
          style={{ height: `${Math.max((to.active / (to.active + to.inactive || 1)) * 100, 2)}%` }}
        />
        <div
          className="bg-gradient-to-t from-amber-500 to-amber-400 rounded-t-sm w-8"
          style={{ height: `${Math.max((to.inactive / (to.active + to.inactive || 1)) * 100, 2)}%` }}
        />
      </div>
    </div>
  );
}

function AttendanceContent({ data }: { data: DashboardData }) {
  const att = data.attendance;
  if (!att) return <p className="text-muted-foreground text-sm">No attendance data</p>;

  const trend = att.by_day || [];
  const maxPercent = Math.max(...trend.map((d) => d.percentage), 1);

  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold text-cyan-400">{att.rate}%</span>
        <span className="text-sm text-muted-foreground">today</span>
      </div>
      <p className="text-xs text-zinc-500">
        {att.today_count} of {att.total} employees clocked in
      </p>
      {trend.length > 0 && (
        <div className="flex items-end gap-1.5 h-14 pt-1">
          {trend.map((day) => (
            <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-[10px] text-zinc-500">{day.percentage}%</span>
              <div
                className="w-full bg-gradient-to-t from-cyan-500 to-cyan-400 rounded-t-sm"
                style={{ height: `${Math.max((day.percentage / maxPercent) * 100, 4)}%` }}
              />
              <span className="text-[9px] text-zinc-600">
                {new Date(day.date).toLocaleDateString("es", { weekday: "short" }).slice(0, 2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CostContent({ data }: { data: DashboardData }) {
  const cost = data.cost;
  if (!cost) return <p className="text-muted-foreground text-sm">No cost data</p>;

  const cats = cost.by_category || [];
  const maxAmount = Math.max(...cats.map((c) => c.amount), 1);

  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-sm text-muted-foreground">{cost.currency}</span>
        <span className="text-4xl font-bold text-rose-400">{cost.total.toLocaleString("es-ES", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
        <span className="text-sm text-muted-foreground">this month</span>
      </div>
      {cats.length > 0 && (
        <div className="space-y-1.5">
          {cats.map((c, i) => (
            <div key={c.category} className="flex items-center gap-2">
              <span className="text-xs text-zinc-500 w-20 capitalize truncate">{c.category}</span>
              <div className="flex-1 bg-zinc-800 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${BAR_COLORS[i % BAR_COLORS.length]}`}
                  style={{ width: `${(c.amount / maxAmount) * 100}%` }}
                />
              </div>
              <span className="text-xs text-zinc-500 w-16 text-right">
                {c.amount.toLocaleString("es-ES", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecentHiresContent({ data }: { data: DashboardData }) {
  const hc = data.headcount;
  if (!hc) return <p className="text-muted-foreground text-sm">No data</p>;

  if (!hc.by_department || hc.by_department.length === 0) {
    return <p className="text-muted-foreground text-sm">No employees found</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold text-indigo-400">{hc.total}</span>
        <span className="text-sm text-muted-foreground">total employees</span>
      </div>
      <div className="space-y-2">
        {hc.by_department.slice(0, 5).map((d) => (
          <div key={d.name} className="flex items-center justify-between text-sm border-b border-zinc-800/50 pb-1.5 last:border-0">
            <span className="text-zinc-300 truncate max-w-[140px]" title={d.name}>{d.name}</span>
            <span className="text-zinc-500">{d.count} employees</span>
          </div>
        ))}
      </div>
      {hc.by_role && hc.by_role.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {hc.by_role.slice(0, 4).map((r) => (
            <Badge key={r.name} variant="outline" className="text-[10px] border-zinc-700 text-zinc-400">
              {r.name}: {r.count}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function ExportContent() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleExport = async (format: string) => {
    setDownloading(format);
    try {
      if (format === "pdf") await ReportAPI.downloadPDF();
      else if (format === "excel") await ReportAPI.downloadExcel();
      else await ReportAPI.exportCustomReport(format);
    } catch (e) {
      console.error(`Export ${format} failed:`, e);
    } finally {
      setDownloading(null);
    }
  };

  const formats = [
    { key: "pdf", icon: <FileText className="w-4 h-4" />, label: "PDF Report", color: "text-red-400" },
    { key: "excel", icon: <FileSpreadsheet className="w-4 h-4" />, label: "Excel Spreadsheet", color: "text-emerald-400" },
    { key: "csv", icon: <FileText className="w-4 h-4" />, label: "CSV Export", color: "text-blue-400" },
  ];

  return (
    <div className="space-y-2">
      {formats.map((f) => (
        <Button
          key={f.key}
          variant="outline"
          className="w-full justify-start gap-3 border-zinc-800 hover:bg-slate-800"
          onClick={() => handleExport(f.key)}
          disabled={downloading !== null}
        >
          {downloading === f.key ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <span className={f.color}>{f.icon}</span>
          )}
          <span className="text-sm">{f.label}</span>
        </Button>
      ))}
    </div>
  );
}
