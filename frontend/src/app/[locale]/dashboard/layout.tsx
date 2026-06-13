import { Sidebar } from "@/components/layout/Sidebar";
import { MobileSidebar } from "@/components/layout/MobileSidebar";
import { OfflineIndicator } from "@/components/layout/OfflineIndicator";
import { TenantProvider } from "@/providers/tenant-provider";
import { PluginProvider } from "@/providers/plugin-provider";
import { AuthGuard } from "@/components/auth/auth-guard";
import { UserAvatar } from "@/components/auth/user-avatar";
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import { UniversalSearch } from "@/components/layout/UniversalSearch";
import { ErrorBoundary, LoadingSkeleton } from "@/components/ui/error-boundary";
import { Suspense } from "react";
import { LazyAiChatWidget } from "@/components/ai/LazyAiChatWidget";

function DashboardHeader({ title }: { title: string }) {
  return (
    <header className="h-16 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex items-center justify-between px-4 md:px-8 z-10">
      <div className="flex items-center gap-4">
        <MobileSidebar />
        <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        <UniversalSearch />
      </div>
      <div className="flex items-center gap-3">
        <NotificationCenter />
        <UserAvatar />
      </div>
    </header>
  );
}

function DashboardContent({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSkeleton rows={5} />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}

export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  let title = "Dashboard";
  try {
    const { getTranslations } = await import("next-intl/server");
    const t = await getTranslations({ locale, namespace: "Navigation" });
    title = t("dashboard") || "Dashboard";
  } catch {}

  return (
      <AuthGuard>
        <TenantProvider>
          <PluginProvider>
            <OfflineIndicator />
            <div className="flex min-h-screen bg-background">
              <Sidebar className="hidden md:flex" />
              <div className="flex-1 flex flex-col">
                <DashboardHeader title={title} />
                <div className="flex-1 overflow-auto p-8 relative">
                  <DashboardContent>
                    {children}
                  </DashboardContent>
                </div>
              </div>
              <LazyAiChatWidget />
            </div>
          </PluginProvider>
        </TenantProvider>
      </AuthGuard>
  );
}
