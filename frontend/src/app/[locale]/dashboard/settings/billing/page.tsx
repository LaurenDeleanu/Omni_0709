"use client";

import { BillingDashboard } from "@/components/admin/BillingDashboard";
import { Button } from "@/components/ui/button";
import { ArrowLeft, CreditCard } from "lucide-react";
import { Link } from "@/i18n/routing";

export default function BillingPage() {
  return (
    <div className="p-6 md:p-10 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/settings">
          <Button variant="outline" size="xs" className="gap-1.5">
            <ArrowLeft className="h-4 w-4" /> Ajustes
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-2">
            <CreditCard className="h-7 w-7 text-primary" /> Facturación & Uso
          </h1>
          <p className="text-muted-foreground mt-1">Gestiona tu plan, API keys y consumo de agentes IA.</p>
        </div>
      </div>
      <BillingDashboard />
    </div>
  );
}
