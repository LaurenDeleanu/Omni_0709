"use client";

import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Menu } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { useState, useEffect, useCallback } from "react";
import { usePathname } from "@/i18n/routing";

export function MobileSidebar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Escape") setOpen(false);
  }, []);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        className="md:hidden p-2 -ml-2 mr-2 text-muted-foreground hover:bg-muted/50 rounded-md"
        aria-label="Abrir menú de navegación"
        aria-expanded={open}
        onKeyDown={handleKeyDown}
      >
        <Menu className="w-6 h-6" aria-hidden="true" />
      </SheetTrigger>
      <SheetContent
        side="left"
        className="p-0 w-64 border-r-0"
        role="navigation"
        aria-label="Navegación principal"
      >
        <Sidebar className="w-full flex" variant="mobile" />
      </SheetContent>
    </Sheet>
  );
}
