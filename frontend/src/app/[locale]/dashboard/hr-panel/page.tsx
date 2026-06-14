"use client";

import { useEffect, useState, useCallback } from "react";
import { HRPanelAPI, type HROverview, type HREmployeeRequest, type HRTicket, type RecruitingOverview, type ComplianceOverview } from "@/lib/api/hr_panel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users, UserPlus, ClipboardList, ShieldCheck,
  Clock, Briefcase, CheckCircle2, XCircle,
  ArrowUpRight, AlertTriangle, UserCheck, UserX,
  Building2, Timer, TrendingUp,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from "recharts";

const CHART_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
  "var(--color-chart-6)",
  "var(--color-chart-7)",
  "var(--color-chart-8)",
];

const STAGE_COLORS: Record<string, string> = {
  applied: CHART_COLORS[1],
  screening: CHART_COLORS[2],
  interview: CHART_COLORS[3],
  offer: CHART_COLORS[4],
  hired: CHART_COLORS[0],
  rejected: "var(--muted-foreground)",
  open: CHART_COLORS[2],
  closed: "var(--muted-foreground)",
  draft: "var(--muted)",
};

function getStatusBadge(status: string) {
  const map: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" | "ghost" }> = {
    open: { label: "Open", variant: "default" },
    in_progress: { label: "In Progress", variant: "secondary" },
    resolved: { label: "Resolved", variant: "outline" },
    closed: { label: "Closed", variant: "ghost" },
    pending: { label: "Pending", variant: "secondary" },
    approved: { label: "Approved", variant: "default" },
    rejected: { label: "Rejected", variant: "destructive" },
    scheduled: { label: "Scheduled", variant: "outline" },
    completed: { label: "Completed", variant: "default" },
    failed: { label: "Failed", variant: "destructive" },
    Draft: { label: "Draft", variant: "ghost" },
  };
  const entry = map[status];
  if (!entry) return <Badge variant="outline">{status}</Badge>;
  return <Badge variant={entry.variant}>{entry.label}</Badge>;
}

function getPriorityBadge(priority: string) {
  const map: Record<string, string> = {
    low: "outline",
    medium: "secondary",
    high: "default",
    critical: "destructive",
  };
  return <Badge variant={(map[priority] || "outline") as any}>{priority}</Badge>;
}

function formatRelativeTime(isoDate: string | null): string {
  if (!isoDate) return "—";
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function KpiCard({ title, value, icon: Icon, desc, trend }: {
  title: string;
  value: string;
  icon: React.ComponentType<any>;
  desc: string;
  trend: "up" | "down" | "neutral" | "warning";
}) {
  return (
    <Card className="glass shadow-sm hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${
          trend === "up" ? "text-primary" :
          trend === "down" ? "text-destructive" :
          trend === "warning" ? "text-amber-500" :
          "text-muted-foreground"
        }`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{desc}</p>
      </CardContent>
    </Card>
  );
}

export default function HRPanelPage() {
  const [overview, setOverview] = useState<HROverview | null>(null);
  const [requests, setRequests] = useState<HREmployeeRequest[]>([]);
  const [tickets, setTickets] = useState<HRTicket[]>([]);
  const [recruiting, setRecruiting] = useState<RecruitingOverview | null>(null);
  const [compliance, setCompliance] = useState<ComplianceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, req, tix, rec, comp] = await Promise.all([
        HRPanelAPI.getOverview(),
        HRPanelAPI.getRequests({ limit: 50 }),
        HRPanelAPI.getTickets({ limit: 30 }),
        HRPanelAPI.getRecruiting(),
        HRPanelAPI.getCompliance(),
      ]);
      setOverview(ov);
      setRequests(req.requests || []);
      setTickets(tix.tickets || []);
      setRecruiting(rec);
      setCompliance(comp);
    } catch (e: any) {
      setError(e?.message || "Failed to load HR panel data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleApprove = async (requestId: string) => {
    setActionLoading(requestId);
    try {
      await HRPanelAPI.approveRequest(requestId);
      await loadData();
    } catch (e: any) {
      setError(e?.message || "Failed to approve request.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (requestId: string) => {
    setActionLoading(requestId);
    try {
      await HRPanelAPI.rejectRequest(requestId);
      await loadData();
    } catch (e: any) {
      setError(e?.message || "Failed to reject request.");
    } finally {
      setActionLoading(null);
    }
  };

  const pipelineData = recruiting ? [
    { name: "Applied", value: recruiting.candidates_by_stage.applied || 0 },
    { name: "Screening", value: recruiting.candidates_by_stage.screening || 0 },
    { name: "Interview", value: recruiting.candidates_by_stage.interview || 0 },
    { name: "Offer", value: recruiting.candidates_by_stage.offer || 0 },
    { name: "Hired", value: recruiting.candidates_by_stage.hired || 0 },
  ] : [];

  const sourceData = recruiting ? recruiting.sources.slice(0, 6) : [];

  const pendingRequests = requests.filter(r => r.status === "pending");

  if (loading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col gap-1">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72 mt-1" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array(8).fill(0).map((_, i) => (
            <Card key={i} className="glass animate-pulse">
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-3 w-28" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="glass animate-pulse">
            <CardHeader><Skeleton className="h-5 w-40" /></CardHeader>
            <CardContent className="space-y-3">
              {Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </CardContent>
          </Card>
          <Card className="glass animate-pulse">
            <CardHeader><Skeleton className="h-5 w-40" /></CardHeader>
            <CardContent className="h-[200px] flex items-center justify-center">
              <Skeleton className="h-32 w-32 rounded-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col gap-1 items-start">
        <h2 className="text-2xl font-bold tracking-tight">HR Central Panel</h2>
        <p className="text-muted-foreground text-sm">
          Unified dashboard for all people operations.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" /> {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Total Employees" value={overview?.total_employees.toLocaleString() ?? "0"} icon={Users} desc={`${overview?.active_employees ?? 0} active`} trend="up" />
        <KpiCard title="New Hires (MTD)" value={overview?.new_hires_month.toLocaleString() ?? "0"} icon={UserPlus} desc="This month" trend="up" />
        <KpiCard title="Open Tickets" value={overview?.open_it_tickets.toLocaleString() ?? "0"} icon={ClipboardList} desc="IT tickets pending" trend={overview && overview.open_it_tickets > 5 ? "warning" : "neutral"} />
        <KpiCard title="Training Compliance" value={`${compliance?.training_completion_rate ?? 0}%`} icon={ShieldCheck} desc={`${compliance?.completed_enrollments ?? 0}/${compliance?.total_enrollments ?? 0} completed`} trend={compliance && compliance.training_completion_rate >= 75 ? "up" : "warning"} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Open Positions" value={overview?.open_jobs.toLocaleString() ?? "0"} icon={Briefcase} desc={`${overview?.pipeline_candidates ?? 0} candidates`} trend="neutral" />
        <KpiCard title="Pending Requests" value={overview?.pending_time_off.toLocaleString() ?? "0"} icon={Clock} desc="Time-off awaiting approval" trend={overview && overview.pending_time_off > 3 ? "warning" : "neutral"} />
        <KpiCard title="Upcoming Reviews" value={overview?.upcoming_reviews.toLocaleString() ?? "0"} icon={Timer} desc="Review cycles in progress" trend="neutral" />
        <KpiCard title="Avg Time-to-Hire" value={`${recruiting?.avg_time_to_hire_days ?? 0}d`} icon={TrendingUp} desc={`${recruiting?.hires_this_month ?? 0} hired this month`} trend="neutral" />
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start overflow-x-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="requests">Requests ({pendingRequests.length})</TabsTrigger>
          <TabsTrigger value="tickets">Tickets</TabsTrigger>
          <TabsTrigger value="recruiting">Recruiting</TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Recent Activity */}
            <Card className="glass">
              <CardHeader>
                <CardTitle>Recent Employee Activity</CardTitle>
                <CardDescription>New hires, departures, and role changes.</CardDescription>
              </CardHeader>
              <CardContent>
                {overview?.recent_activity && overview.recent_activity.length > 0 ? (
                  <div className="space-y-3">
                    {overview.recent_activity.slice(0, 8).map((act) => (
                      <div key={act.id} className="flex items-center gap-3 border-b border-border/40 pb-3 last:border-0 last:pb-0">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                          <span className="text-xs font-semibold text-primary">
                            {(act.full_name || act.email).charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium leading-none truncate">{act.full_name || act.email}</p>
                          <p className="text-xs text-muted-foreground mt-0.5 truncate">
                            {act.department} · {act.role}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                          <Clock className="w-3 h-3" />
                          {formatRelativeTime(act.created_at)}
                        </div>
                        <Badge variant={act.is_active ? "default" : "secondary"}>
                          {act.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">No recent activity.</p>
                )}
              </CardContent>
            </Card>

            {/* Pipeline Funnel */}
            <Card className="glass">
              <CardHeader>
                <CardTitle>Recruitment Pipeline</CardTitle>
                <CardDescription>Candidate funnel by stage.</CardDescription>
              </CardHeader>
              <CardContent className="h-[280px]">
                {pipelineData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                    <BarChart data={pipelineData} layout="vertical" margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} width={70} />
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        formatter={(v: any) => [v, "Candidates"]}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {pipelineData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                    No recruitment data available.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Recent Change Logs */}
          <Card className="glass">
            <CardHeader>
              <CardTitle>Recent Change Log</CardTitle>
              <CardDescription>Record history events for employees.</CardDescription>
            </CardHeader>
            <CardContent>
              {overview?.history_events && overview.history_events.length > 0 ? (
                <div className="space-y-2">
                  {overview.history_events.slice(0, 5).map((ev) => (
                    <div key={ev.id} className="flex items-center gap-3 text-sm border-b border-border/30 pb-2 last:border-0">
                      <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="font-medium">{ev.field_name}</span>
                      <span className="text-muted-foreground">
                        {ev.old_value || "—"} → {ev.new_value || "—"}
                      </span>
                      {ev.change_reason && (
                        <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                          ({ev.change_reason})
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground ml-auto shrink-0">
                        {formatRelativeTime(ev.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No change history.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="requests" className="space-y-4 mt-4">
          <Card className="glass">
            <CardHeader>
              <CardTitle>Employee Requests</CardTitle>
              <CardDescription>Time-off requests requiring approval.</CardDescription>
            </CardHeader>
            <CardContent>
              {requests.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Dates</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {requests.map((req) => (
                      <TableRow key={req.id}>
                        <TableCell className="font-medium">{req.employee_name || req.employee_id}</TableCell>
                        <TableCell className="capitalize">{req.subtype || req.type}</TableCell>
                        <TableCell>
                          {req.start_date?.split("T")[0]} — {req.end_date?.split("T")[0]}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">{req.reason || "—"}</TableCell>
                        <TableCell>{getStatusBadge(req.status)}</TableCell>
                        <TableCell>
                          {req.status === "pending" ? (
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="default"
                                className="h-7 text-xs"
                                disabled={actionLoading === req.id}
                                onClick={() => handleApprove(req.id)}
                              >
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                {actionLoading === req.id ? "..." : "Approve"}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs"
                                disabled={actionLoading === req.id}
                                onClick={() => handleReject(req.id)}
                              >
                                <XCircle className="h-3 w-3 mr-1" />
                                Reject
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No requests found.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tickets" className="space-y-4 mt-4">
          <Card className="glass">
            <CardHeader>
              <CardTitle>IT Tickets</CardTitle>
              <CardDescription>All IT/HR tickets across employees.</CardDescription>
            </CardHeader>
            <CardContent>
              {tickets.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Requester</TableHead>
                      <TableHead>Assignee</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tickets.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell className="font-medium max-w-[200px] truncate">{t.title}</TableCell>
                        <TableCell>{t.requester_name || t.requester_id}</TableCell>
                        <TableCell>{t.assignee_name || "Unassigned"}</TableCell>
                        <TableCell className="capitalize">{t.category}</TableCell>
                        <TableCell>{getPriorityBadge(t.priority)}</TableCell>
                        <TableCell>{getStatusBadge(t.status)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatRelativeTime(t.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No tickets found.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recruiting" className="space-y-4 mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="glass">
              <CardHeader>
                <CardTitle>Pipeline Breakdown</CardTitle>
                <CardDescription>Jobs and candidates by stage.</CardDescription>
              </CardHeader>
              <CardContent className="h-[250px]">
                {recruiting && Object.keys(recruiting.candidates_by_stage).length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                    <PieChart>
                      <Pie
                        data={Object.entries(recruiting.candidates_by_stage).map(([stage, count]) => ({
                          name: stage.charAt(0).toUpperCase() + stage.slice(1),
                          value: count,
                        }))}
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value}`}
                        labelLine={{ stroke: "hsl(var(--muted-foreground))" }}
                      >
                        {Object.keys(recruiting.candidates_by_stage).map((stage, i) => (
                          <Cell key={stage} fill={STAGE_COLORS[stage] || CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                      />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                    No pipeline data.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="glass">
              <CardHeader>
                <CardTitle>Candidate Sources</CardTitle>
                <CardDescription>Where candidates are coming from.</CardDescription>
              </CardHeader>
              <CardContent className="h-[250px]">
                {sourceData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                    <BarChart data={sourceData} layout="vertical" margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis type="category" dataKey="source" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} width={80} />
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        formatter={(v: any) => [v, "Candidates"]}
                      />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                        {sourceData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                    No source data.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {recruiting?.open_positions && recruiting.open_positions.length > 0 && (
            <Card className="glass">
              <CardHeader>
                <CardTitle>Open Positions</CardTitle>
                <CardDescription>Active job postings with candidate counts.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Department</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Candidates</TableHead>
                      <TableHead>Posted</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recruiting.open_positions.map((pos) => (
                      <TableRow key={pos.id}>
                        <TableCell className="font-medium">{pos.title}</TableCell>
                        <TableCell>{pos.department || "—"}</TableCell>
                        <TableCell>{pos.location || "—"}</TableCell>
                        <TableCell>{pos.employment_type || "—"}</TableCell>
                        <TableCell>{pos.candidate_count}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatRelativeTime(pos.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="compliance" className="space-y-4 mt-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card className="glass">
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">Training Completion</CardTitle>
                <ShieldCheck className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{compliance?.training_completion_rate ?? 0}%</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {compliance?.completed_enrollments ?? 0} completed / {compliance?.total_enrollments ?? 0} total enrollments
                </p>
              </CardContent>
            </Card>
            <Card className="glass">
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">Users Without Training</CardTitle>
                <UserX className="h-4 w-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{compliance?.users_without_training ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Out of {compliance?.total_employees ?? 0} total employees
                </p>
              </CardContent>
            </Card>
            <Card className="glass">
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">Missing Department</CardTitle>
                <AlertTriangle className="h-4 w-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{compliance?.missing_department ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Without department assignment
                </p>
              </CardContent>
            </Card>
          </div>

          {compliance?.upcoming_audits && compliance.upcoming_audits.length > 0 && (
            <Card className="glass">
              <CardHeader>
                <CardTitle>Upcoming Compliance Audits</CardTitle>
                <CardDescription>Scheduled compliance reviews and inspections.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Frequency</TableHead>
                      <TableHead>Scheduled</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {compliance.upcoming_audits.map((audit) => (
                      <TableRow key={audit.id}>
                        <TableCell className="font-medium">{audit.title}</TableCell>
                        <TableCell className="capitalize">{audit.audit_type?.replace(/_/g, " ")}</TableCell>
                        <TableCell>{getStatusBadge(audit.status)}</TableCell>
                        <TableCell className="capitalize">{audit.frequency}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {audit.scheduled_at ? new Date(audit.scheduled_at).toLocaleDateString() : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
