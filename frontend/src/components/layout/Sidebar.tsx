"use client";

import { usePathname } from "@/i18n/routing";
import { Link } from "@/i18n/routing";
import { LayoutDashboard, Users, Upload, Settings, PieChart, CalendarClock, Calendar, Laptop, CreditCard, GraduationCap, Shield, Briefcase, Presentation, TrendingUp, Target, Building, LineChart, User, Award, Sparkles, Network, Terminal, TestTube2, Activity, MessageCircle, Mail, Code, Server, Plug, FileText, GitCompare, Puzzle, Zap, Star, Clock, Globe, ChevronDown, Bell, HelpCircle, LogOut, DollarSign, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useTenant } from "@/providers/tenant-provider";
import { useUser } from "@/hooks/use-user";
import { useTranslations } from "next-intl";
import { useState, useEffect } from "react";
import { NotificationAPI, type Notification } from "@/lib/api";
import { LocaleSwitcher } from "@/components/ui/LocaleSwitcher";

const NAV_ITEMS = [
  { key: "dashboard", href: "/dashboard", icon: LayoutDashboard },
  { key: "profile", href: "/dashboard/profile", icon: User },
  { key: "kudos", href: "/dashboard/kudos", icon: Award },
  { key: "people", href: "/dashboard/employees", icon: Users },
  { key: "chat", href: "/dashboard/chat", icon: MessageCircle },
  { key: "agent_studio", href: "/dashboard/agent-studio", icon: Sparkles },
  { key: "workflows", href: "/dashboard/workflows", icon: Network },
  { key: "crm", href: "/dashboard/crm", icon: TrendingUp },
  { key: "codelab", href: "/dashboard/codelab", icon: Terminal },
  { key: "harness", href: "/dashboard/harness", icon: TestTube2 },
  { key: "monitoring", href: "/dashboard/monitoring", icon: Activity },
  { key: "grow", href: "/dashboard/grow", icon: Target },
  { key: "hire", href: "/dashboard/hire", icon: Briefcase },
  { key: "it", href: "/dashboard/it", icon: Laptop },
  { key: "finance", href: "/dashboard/finance", icon: CreditCard },
  { key: "pay", href: "/dashboard/pay", icon: CreditCard },
  { key: "training", href: "/dashboard/training", icon: GraduationCap },
  { key: "work", href: "/dashboard/work", icon: Presentation },
  { key: "sales", href: "/dashboard/sales", icon: TrendingUp },
  { key: "imports", href: "/dashboard/imports", icon: Upload },
  { key: "reports", href: "/dashboard/reports", icon: PieChart },
  { key: "legal", href: "/dashboard/legal", icon: Shield },
  { key: "ops", href: "/dashboard/ops", icon: Building },
  { key: "intelligence", href: "/dashboard/intelligence", icon: LineChart },
  { key: "schedules", href: "/dashboard/schedules", icon: CalendarClock },
  { key: "calendar", href: "/dashboard/calendar", icon: Calendar },
  { key: "integrations", href: "/dashboard/settings/integrations", icon: Upload },
  { key: "settings", href: "/dashboard/settings", icon: Settings },
  { key: "reviews_360", href: "/dashboard/reviews", icon: Star },
  { key: "time_tracking", href: "/dashboard/time-tracking", icon: Clock },
  { key: "careers", href: "/careers", icon: Globe },
  { key: "billing", href: "/dashboard/settings/billing", icon: DollarSign },
];

export function Sidebar({ className, variant = "desktop" }: { className?: string; variant?: "desktop" | "mobile" }) {
  const pathname = usePathname();
  const { logoUrl, name, enabledModules } = useTenant();
  const { user } = useUser();
  const t = useTranslations("Navigation");
  const isMobile = variant === "mobile";

  const [adminExpanded, setAdminExpanded] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!isMobile) return;
    NotificationAPI.getMyNotifications()
      .then((notifs) => setUnreadCount(notifs.filter((n: Notification) => !n.is_read).length))
      .catch(() => {});
    const interval = setInterval(() => {
      NotificationAPI.getMyNotifications()
        .then((notifs) => setUnreadCount(notifs.filter((n: Notification) => !n.is_read).length))
        .catch(() => {});
    }, 60000);
    return () => clearInterval(interval);
  }, [isMobile]);

  const isHrAdmin = user?.role === "hr_admin";

  const activeNavItems = NAV_ITEMS.filter((item) => {
    if (item.href === "/dashboard/it" && enabledModules?.it === false) return false;
    if (item.href === "/dashboard/finance" && enabledModules?.finance === false) return false;
    if (item.href === "/dashboard/pay" && enabledModules?.finance === false) return false;
    if (item.href === "/dashboard/training" && enabledModules?.training === false) return false;
    if (item.href === "/dashboard/schedules" && enabledModules?.schedules === false) return false;
    if (item.href === "/dashboard/hire" && enabledModules?.hire === false) return false;
    if (item.href === "/dashboard/work" && enabledModules?.work === false) return false;
    if (item.href === "/dashboard/sales" && enabledModules?.sales === false) return false;
    if (item.href === "/dashboard/grow" && enabledModules?.grow === false) return false;
    if (item.href === "/dashboard/ops" && enabledModules?.ops === false) return false;
    if (item.href === "/dashboard/intelligence" && enabledModules?.intelligence === false) return false;
    if (item.href === "/dashboard/employees" && enabledModules?.people === false) return false;
    if (item.href === "/careers" && enabledModules?.careers === false) return false;
    if (item.href === "/dashboard/settings/billing" && enabledModules?.billing === false) return false;
    return true;
  });

  const adminKeys = new Set([
    "/dashboard/admin",
    "/dashboard/admin/developer-portal",
    "/dashboard/admin/infrastructure",
    "/dashboard/admin/connectors",
    "/dashboard/admin/email-templates",
    "/dashboard/admin/document-templates",
    "/dashboard/admin/runs/compare",
    "/dashboard/admin/plugin-store",
  ]);

  const regularItems = activeNavItems.filter((item) => !adminKeys.has(item.href));

  const adminNavItems = isHrAdmin
    ? [
        { key: "admin_panel", href: "/dashboard/admin", icon: Shield },
        { key: "developer_portal", href: "/dashboard/admin/developer-portal", icon: Code },
        { key: "infrastructure", href: "/dashboard/admin/infrastructure", icon: Server },
        { key: "connectors", href: "/dashboard/admin/connectors", icon: Plug },
        { key: "email_templates", href: "/dashboard/admin/email-templates", icon: Mail },
        { key: "document_templates", href: "/dashboard/admin/document-templates", icon: FileText },
        { key: "run_compare", href: "/dashboard/admin/runs/compare", icon: GitCompare },
        { key: "plugin_store", href: "/dashboard/admin/plugin-store", icon: Puzzle },
        { key: "power_automate", href: "/dashboard/admin/power-automate", icon: Zap },
      ]
    : [];

  const handleLogout = (e: React.MouseEvent) => {
    if (typeof window !== "undefined" && localStorage.getItem("local_access_token")) {
      e.preventDefault();
      localStorage.removeItem("local_access_token");
      localStorage.removeItem("local_user");
      window.location.href = "/login";
    }
  };

  const renderNavItem = (item: { key: string; href: string; icon: LucideIcon }) => {
    const cleanPathname = pathname.replace(/^\/[a-z]{2}(\/|$)/, '/');
    const isActive = item.href === "/dashboard"
      ? cleanPathname === "/dashboard" || cleanPathname === "/"
      : cleanPathname.startsWith(item.href);

    const itemName = t(item.key) || item.key;
    return (
      <Link
        key={item.href}
        href={item.href as any}
        className={cn(
          "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all duration-200 group",
          isActive
            ? "bg-primary/10 text-primary font-medium border-l-2 border-l-primary pl-[10px]"
            : "text-muted-foreground hover:bg-muted/80 hover:text-foreground border-l-2 border-l-transparent pl-[10px]"
        )}
      >
        <item.icon
          className={cn(
            "w-4 h-4 transition-colors",
            isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
          )}
        />
        {itemName}
      </Link>
    );
  };

  return (
    <aside className={cn("w-64 border-r border-border bg-card/50 backdrop-blur-xl h-screen flex flex-col sticky top-0", className)}>
      <div className="h-16 flex items-center px-6 border-b border-border/50">
        {logoUrl ? (
          <img src={logoUrl} alt={name || "Logo"} className="h-13 md:h-14 max-w-[200px] md:max-w-[215px] w-auto object-contain transition-all duration-300" />
        ) : (
          <div className="font-bold text-2xl md:text-3xl tracking-tight bg-gradient-to-r from-primary to-indigo-500 bg-clip-text text-transparent transition-all duration-300">
            {name || "SuccessCore"}
          </div>
        )}
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 px-2">
          {t("menu") || "Menú"}
        </div>
        {regularItems.map(renderNavItem)}

        {isHrAdmin && isMobile && (
          <div>
            <button
              onClick={() => setAdminExpanded((v) => !v)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm w-full text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-all duration-200 border-l-2 border-l-transparent pl-[10px]"
            >
              <Shield className="w-4 h-4" />
              <span className="flex-1 text-left">{t("admin_section") || "Admin"}</span>
              <ChevronDown className={cn("w-4 h-4 transition-transform", adminExpanded && "rotate-180")} />
            </button>
            {adminExpanded && (
              <div className="ml-2 space-y-0.5 mt-0.5">
                {adminNavItems.map(renderNavItem)}
              </div>
            )}
          </div>
        )}

        {isHrAdmin && !isMobile && adminNavItems.map(renderNavItem)}

        {isMobile && (
          <>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 px-2 pt-2">
              {t("notifications") || "Notifications"}
            </div>
            <Link
              href="/dashboard/profile"
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all duration-200 group",
                "text-muted-foreground hover:bg-muted/80 hover:text-foreground border-l-2 border-l-transparent pl-[10px]"
              )}
            >
              <Bell className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
              {t("notifications") || "Notifications"}
              {unreadCount > 0 && (
                <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[10px] font-bold text-primary-foreground">
                  {unreadCount}
                </span>
              )}
            </Link>
          </>
        )}
      </nav>

      {isMobile && (
        <div className="border-t border-border/50 p-4 space-y-1">
          <Link
            href="/help"
            className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-all duration-200 border-l-2 border-l-transparent pl-[10px]"
          >
            <HelpCircle className="w-4 h-4" />
            {t("help_support") || "Help & Support"}
          </Link>
          <Link
            href="/careers"
            className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-all duration-200 border-l-2 border-l-transparent pl-[10px]"
          >
            <Briefcase className="w-4 h-4" />
            {t("view_careers") || "View Careers"}
          </Link>
        </div>
      )}

      <div className="p-4 border-t border-border/50 flex flex-col gap-4">
        {isMobile && (
          <ThemeToggle />
        )}
        <div className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 transition-colors cursor-pointer">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-xs ring-1 ring-primary/30">
            {user?.full_name
              ? user.full_name.split(" ").map((n: string) => n[0]).slice(0, 2).join("").toUpperCase()
              : user?.email
                ? user.email.slice(0, 2).toUpperCase()
                : "??"}
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium leading-none mb-1">{user?.full_name || user?.email || "User"}</span>
            <span className="text-xs text-muted-foreground leading-none">{name || "SuccessCore"}</span>
          </div>
        </div>
        {isMobile && (
          // eslint-disable-next-line @next/next/no-html-link-for-pages
          <a
            href="/api/auth/logout"
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            {t("logout") || "Cerrar sesión"}
          </a>
        )}
        {!isMobile && (
          <>
            <ThemeToggle />
            <LocaleSwitcher />
          </>
        )}
      </div>
    </aside>
  );
}
