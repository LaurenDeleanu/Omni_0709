"use client";

import { useQuery } from "@tanstack/react-query";
import { TenantAPI } from "@/lib/api";
import React, { createContext, useContext, useEffect } from "react";

// Convert hex to HSL for Tailwind
function hexToHSL(hex: string) {
  let r = 0, g = 0, b = 0;
  if (hex.length === 4) {
    r = parseInt(hex[1] + hex[1], 16);
    g = parseInt(hex[2] + hex[2], 16);
    b = parseInt(hex[3] + hex[3], 16);
  } else if (hex.length === 7) {
    r = parseInt(hex.substring(1, 3), 16);
    g = parseInt(hex.substring(3, 5), 16);
    b = parseInt(hex.substring(5, 7), 16);
  }
  
  r /= 255;
  g /= 255;
  b /= 255;
  
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0, l = (max + min) / 2;
  
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  
  return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

interface TenantContextType {
  logoUrl?: string | null;
  name?: string;
  enabledModules?: Record<string, boolean>;
}

const TenantContext = createContext<TenantContextType>({});

export const useTenant = () => useContext(TenantContext);

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const { data: settings } = useQuery({
    queryKey: ["tenantSettings"],
    queryFn: () => TenantAPI.getSettings(),
  });

  // Inyectar el color primario si existe
  useEffect(() => {
    if (settings?.primary_color) {
      const root = document.documentElement;
      const hsl = hexToHSL(settings.primary_color);
      root.style.setProperty("--primary", hsl);
    }
  }, [settings?.primary_color]);

  return (
    <TenantContext.Provider value={{ 
      logoUrl: settings?.logo_url, 
      name: settings?.name,
      enabledModules: settings?.enabled_modules
    }}>
      {children}
    </TenantContext.Provider>
  );
}

