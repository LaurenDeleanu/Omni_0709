'use client';

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import { Auth0Provider } from '@auth0/nextjs-auth0/client';
import React, { useEffect, useState } from 'react';
import { TenantAPI } from '@/lib/api';

function TenantThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    TenantAPI.getSettings().then(settings => {
      if (settings.primary_color) {
        document.documentElement.style.setProperty("--color-primary", settings.primary_color);
      }
    }).catch((err) => {
      console.warn('No se pudo cargar la configuración del tenant', err);
    });
  }, []);
  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
            retry: (failureCount, error: any) => {
              if (error?.status === 401) return false;
              return failureCount < 3;
            },
          },
        },
      })
  );

  const isAuth0Configured = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID && process.env.NEXT_PUBLIC_AUTH0_DOMAIN;

  const content = (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      themes={["light", "dark", "blue"]}
      enableSystem={false}
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        <TenantThemeProvider>
          {children}
        </TenantThemeProvider>
      </QueryClientProvider>
    </NextThemesProvider>
  );

  if (isAuth0Configured) {
    return <Auth0Provider>{content}</Auth0Provider>;
  }

  return content;
}
