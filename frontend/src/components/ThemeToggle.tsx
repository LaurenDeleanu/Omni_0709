"use client";

import * as React from "react";
import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  // Evita la discrepancia de hidratación entre servidor y cliente.
  // useTheme() devuelve `undefined` en SSR, pero tiene valor real en el cliente.
  // Renderizamos el placeholder hasta que el componente esté montado.
  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Placeholder con las mismas dimensiones para evitar layout shift (CLS)
    return (
      <div className="flex items-center gap-2 p-1 border rounded-lg bg-card text-muted-foreground w-fit">
        <div className="w-8 h-8 rounded-md" />
        <div className="w-8 h-8 rounded-md" />
        <div className="w-8 h-8 rounded-md" />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 p-1 border rounded-lg bg-card text-muted-foreground w-fit">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setTheme("light")}
        className={`w-8 h-8 rounded-md ${theme === "light" ? "bg-primary/20 text-primary hover:bg-primary/30" : ""}`}
        aria-label="Light theme"
      >
        <Sun className="w-4 h-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setTheme("dark")}
        className={`w-8 h-8 rounded-md ${theme === "dark" ? "bg-primary/20 text-primary hover:bg-primary/30" : ""}`}
        aria-label="Dark theme"
      >
        <Moon className="w-4 h-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setTheme("blue")}
        className={`w-8 h-8 rounded-md ${theme === "blue" ? "bg-primary/20 text-primary hover:bg-primary/30" : ""}`}
        aria-label="Blue theme"
      >
        <Monitor className="w-4 h-4" />
      </Button>
    </div>
  );
}
