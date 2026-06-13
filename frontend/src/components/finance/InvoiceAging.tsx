"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import {
  Receipt, Clock, AlertTriangle, DollarSign, TrendingUp, TrendingDown,
  CheckCircle2, ExternalLink, ChevronRight
} from "lucide-react";

const AGING_DATA = {
  total_outstanding: 142800,
  total_payable: 89000,
  total_receivable: 53800,
  aging_buckets: {
    current: { label: "Al día", count: 24, amount: 45000, color: "bg-emerald-500" },
    "1-30": { label: "1-30 días", count: 12, amount: 32000, color: "bg-blue-500" },
    "31-60": { label: "31-60 días", count: 8, amount: 28000, color: "bg-amber-500" },
    "61-90": { label: "61-90 días", count: 5, amount: 18500, color: "bg-orange-500" },
    ">90": { label: "Más de 90 días", count: 3, amount: 19300, color: "bg-rose-500" },
  },
  recent_payables: [
    { vendor: "AWS Europe", amount: 12450, due: "2026-06-20", status: "pending", days_left: 7 },
    { vendor: "Google Workspace", amount: 2340, due: "2026-06-10", status: "overdue", days_overdue: 3 },
    { vendor: "HubSpot", amount: 1890, due: "2026-06-15", status: "pending", days_left: 2 },
    { vendor: "Notion", amount: 960, due: "2026-06-01", status: "overdue", days_overdue: 12 },
    { vendor: "Slack", amount: 1560, due: "2026-06-25", status: "pending", days_left: 12 },
  ],
  recent_receivables: [
    { client: "Acme Corp", amount: 15000, due: "2026-05-15", status: "overdue", days_overdue: 29 },
    { client: "TechStart SL", amount: 8900, due: "2026-06-01", status: "overdue", days_overdue: 12 },
    { client: "DataFlow GmbH", amount: 12000, due: "2026-06-20", status: "pending", days_left: 7 },
  ],
};

export function InvoiceAging() {
  const maxBucketAmount = Math.max(...Object.values(AGING_DATA.aging_buckets).map(b => b.amount));

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Pendiente</CardTitle>
            <Receipt className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">€{(AGING_DATA.total_outstanding / 1000).toFixed(0)}K</div>
            <p className="text-[10px] text-muted-foreground mt-1">Pagable + Cobrable</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Cuentas a Pagar</CardTitle>
            <TrendingDown className="h-4 w-4 text-rose-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">€{(AGING_DATA.total_payable / 1000).toFixed(0)}K</div>
            <p className="text-[10px] text-muted-foreground mt-1">{AGING_DATA.recent_payables.filter(p => p.status === "overdue").length} vencidas</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Cuentas a Cobrar</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">€{(AGING_DATA.total_receivable / 1000).toFixed(0)}K</div>
            <p className="text-[10px] text-muted-foreground mt-1">{AGING_DATA.recent_receivables.filter(r => r.status === "overdue").length} vencidas</p>
          </CardContent>
        </Card>
        <Card className="glass shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Facturas Vencidas</CardTitle>
            <AlertTriangle className="h-4 w-4 text-rose-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(AGING_DATA.aging_buckets[">90"].amount + AGING_DATA.aging_buckets["61-90"].amount + AGING_DATA.aging_buckets["31-60"].amount).toLocaleString()}€</div>
            <p className="text-[10px] text-muted-foreground mt-1">{AGING_DATA.aging_buckets["61-90"].count + AGING_DATA.aging_buckets[">90"].count} facturas &gt;60d</p>
          </CardContent>
        </Card>
      </div>

      {/* Aging Buckets */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Clock className="h-5 w-5 text-amber-500" />
            Aging de Facturas
          </CardTitle>
          <CardDescription>Distribución de facturas por antigüedad (pagables + cobrables)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-5">
            {Object.entries(AGING_DATA.aging_buckets).map(([key, bucket]) => (
              <div key={key} className="p-4 rounded-xl bg-muted/10 border border-border/30 text-center">
                <p className="text-xs text-muted-foreground mb-1">{bucket.label}</p>
                <div className={`w-full h-2 rounded-full ${bucket.color} mb-2`}
                  style={{ opacity: bucket.amount / maxBucketAmount * 0.8 + 0.2 }}
                />
                <p className="text-xl font-extrabold">€{(bucket.amount / 1000).toFixed(0)}K</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">{bucket.count} facturas</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Payables & Receivables */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-rose-500" />
              Cuentas a Pagar
            </CardTitle>
            <CardDescription>Próximos vencimientos y facturas vencidas</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {AGING_DATA.recent_payables.map((item, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-border/30 hover:bg-muted/10 transition-colors">
                <div>
                  <p className="text-sm font-semibold">{item.vendor}</p>
                  <p className="text-[10px] text-muted-foreground">
                    Vence: {new Date(item.due).toLocaleDateString("es-ES")}
                    {item.status === "overdue" && (
                      <span className="text-rose-500 ml-1">({item.days_overdue}d tarde)</span>
                    )}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold">€{item.amount.toLocaleString()}</p>
                  <Badge className={item.status === "overdue" ? "bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] font-bold" : "bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px] font-bold"}>
                    {item.status === "overdue" ? "Vencida" : "Pendiente"}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-500" />
              Cuentas a Cobrar
            </CardTitle>
            <CardDescription>Clientes con facturas pendientes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {AGING_DATA.recent_receivables.map((item, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-border/30 hover:bg-muted/10 transition-colors">
                <div>
                  <p className="text-sm font-semibold">{item.client}</p>
                  <p className="text-[10px] text-muted-foreground">
                    Vence: {new Date(item.due).toLocaleDateString("es-ES")}
                    {item.status === "overdue" && (
                      <span className="text-rose-500 ml-1">({item.days_overdue}d tarde)</span>
                    )}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold">€{item.amount.toLocaleString()}</p>
                  <Badge className={item.status === "overdue" ? "bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] font-bold" : "bg-blue-500/10 text-blue-500 border-blue-500/20 text-[10px] font-bold"}>
                    {item.status === "overdue" ? "Vencida" : "Pendiente"}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
