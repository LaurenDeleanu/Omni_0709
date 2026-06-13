"use client";

import { ITKBBrowser } from "@/components/it/ITKBBrowser";
import { Button } from "@/components/ui/button";
import { ArrowLeft, BookOpen } from "lucide-react";
import { Link } from "@/i18n/routing";

export default function ITKBPage() {
  return (
    <div className="p-6 md:p-10 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/it">
          <Button variant="outline" size="xs" className="gap-1.5">
            <ArrowLeft className="h-4 w-4" /> Volver a IT
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Base de Conocimiento IT</h1>
          <p className="text-muted-foreground mt-1">Explora, busca y contribuye a la base de conocimiento del departamento IT.</p>
        </div>
      </div>
      <ITKBBrowser />
    </div>
  );
}
