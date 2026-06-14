"use client";

import { useEffect, useState, useRef } from "react";
import { Bell, Check, Trash2, Calendar, DollarSign, Award, Info, ClipboardList } from "lucide-react";
import { NotificationAPI, Notification } from "@/lib/api";
import { usePathname, useRouter } from "@/i18n/routing";
import { Link } from "@/i18n/routing";

export function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const router = useRouter();

  const fetchNotifications = () => {
    NotificationAPI.getMyNotifications()
      .then(setNotifications)
      .catch((err) => console.error("Error fetching notifications:", err));
  };

  // Poll notifications on route change + check every 60s
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, [pathname]);

  // Handle outside clicks to close dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleNotificationClick = async (n: Notification) => {
    if (!n.is_read) {
      try {
        const updated = await NotificationAPI.readNotification(n.id);
        setNotifications((prev) => prev.map((item) => (item.id === n.id ? updated : item)));
      } catch (err) {
        console.error("Error marking notification as read:", err);
      }
    }
    if (n.link) {
      router.push(n.link);
      setOpen(false);
    }
  };

  const handleReadAll = async () => {
    try {
      await NotificationAPI.readAll();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error("Error marking all as read:", err);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "vacation":
        return <Calendar className="h-4 w-4 text-emerald-500" />;
      case "payroll":
        return <DollarSign className="h-4 w-4 text-indigo-500" />;
      case "kudos":
        return <Award className="h-4 w-4 text-amber-500" />;
      case "task":
        return <ClipboardList className="h-4 w-4 text-cyan-500" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getTypeBg = (type: string) => {
    switch (type) {
      case "vacation":
        return "bg-emerald-500/10 border-emerald-500/20";
      case "payroll":
        return "bg-indigo-500/10 border-indigo-500/20";
      case "kudos":
        return "bg-amber-500/10 border-amber-500/20";
      case "task":
        return "bg-cyan-500/10 border-cyan-500/20";
      default:
        return "bg-blue-500/10 border-blue-500/20";
    }
  };

  return (
    <div ref={dropdownRef} className="relative">
      {/* Bell Trigger */}
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="relative p-2 rounded-full hover:bg-muted/60 transition-all active:scale-95 group focus:outline-none focus:ring-2 focus:ring-primary/20"
        aria-label="Notificaciones"
      >
        <Bell className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground ring-2 ring-background animate-pulse">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Glassmorphism Dropdown */}
      {open && (
        <div className="absolute right-0 mt-3 w-80 sm:w-96 rounded-2xl border border-border/60 bg-background/95 backdrop-blur-md shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-3 duration-200">
          {/* Header */}
          <div className="px-5 py-4 border-b border-border/40 flex items-center justify-between bg-muted/20">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Notificaciones</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {unreadCount === 0 ? "Al día" : `Tienes ${unreadCount} sin leer`}
              </p>
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleReadAll}
                className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 font-medium transition-colors focus:outline-none"
              >
                <Check className="h-3 w-3" />
                Marcar leídas
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-border/40">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
                <div className="p-3 bg-muted/40 rounded-full mb-3">
                  <Bell className="h-6 w-6 text-muted-foreground/60" />
                </div>
                <p className="text-sm text-foreground font-medium">Bandeja de entrada vacía</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-[200px]">
                  Te avisaremos cuando tengas tareas, novedades o nóminas listas.
                </p>
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleNotificationClick(n)}
                  className={`p-4 transition-all duration-200 flex items-start gap-3.5 cursor-pointer relative hover:bg-muted/40 ${
                    !n.is_read ? "bg-indigo-500/[0.02]" : ""
                  }`}
                >
                  {/* Status Indicator */}
                  {!n.is_read && (
                    <span className="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-indigo-500" />
                  )}

                  {/* Icon */}
                  <div className={`p-2 rounded-xl border flex-shrink-0 ${getTypeBg(n.type)}`}>
                    {getTypeIcon(n.type)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-xs font-semibold text-foreground leading-tight truncate">
                        {n.title}
                      </p>
                      <span className="text-[9px] text-muted-foreground flex-shrink-0">
                        {new Date(n.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 font-normal leading-relaxed break-words">
                      {n.message}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-2.5 border-t border-border/40 text-center bg-muted/20">
              <Link
                href="/dashboard/profile"
                onClick={() => setOpen(false)}
                className="text-[11px] text-muted-foreground hover:text-foreground transition-colors font-medium inline-block"
              >
                Ver todo en mi portal self-service
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
