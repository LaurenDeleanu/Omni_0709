"use client";

import { useState, useEffect } from "react";
import { fetchClient } from "@/lib/api/client";
import { Bell, BellOff, Mail, Smartphone, Clock } from "lucide-react";
import { toast } from "sonner";

export default function NotificationPreferences() {
  const [prefs, setPrefs] = useState({
    email_notifications: true, push_notifications: true,
    in_app_notifications: true, digest_frequency: "daily", muted_until: "",
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchClient("/notification-prefs/preferences").then(d => setPrefs({...prefs, ...d})).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const save = async () => {
    try {
      await fetchClient("/notification-prefs/preferences", { method: "PUT", body: JSON.stringify(prefs) });
      toast.success("Preferences saved");
    } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div className="p-8 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Notification Preferences</h1>
      <p className="text-sm text-muted-foreground mb-8">Control how and when you receive notifications</p>

      <div className="space-y-4">
        <ToggleRow icon={<Mail size={16} />} label="Email Notifications" checked={prefs.email_notifications} onChange={v => setPrefs({...prefs, email_notifications: v})} />
        <ToggleRow icon={<Smartphone size={16} />} label="Push Notifications" checked={prefs.push_notifications} onChange={v => setPrefs({...prefs, push_notifications: v})} />
        <ToggleRow icon={<Bell size={16} />} label="In-App Notifications" checked={prefs.in_app_notifications} onChange={v => setPrefs({...prefs, in_app_notifications: v})} />

        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2 mb-3"><Clock size={16} className="text-muted-foreground" /><span className="font-medium text-sm">Digest Frequency</span></div>
          <select value={prefs.digest_frequency} onChange={e => setPrefs({...prefs, digest_frequency: e.target.value})} className="w-full bg-background border rounded-lg px-3 py-2 text-sm">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="never">Never</option>
          </select>
        </div>

        <button onClick={save} className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium">Save Preferences</button>
      </div>
    </div>
  );
}

function ToggleRow({ icon, label, checked, onChange }: { icon: any; label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="rounded-lg border bg-card p-4 flex items-center justify-between">
      <div className="flex items-center gap-3"><span className="text-muted-foreground">{icon}</span><span className="text-sm font-medium">{label}</span></div>
      <button onClick={() => onChange(!checked)} className={`w-10 h-6 rounded-full transition-colors relative ${checked ? "bg-primary" : "bg-muted"}`}>
        <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${checked ? "translate-x-4" : "translate-x-0.5"}`} />
      </button>
    </div>
  );
}
