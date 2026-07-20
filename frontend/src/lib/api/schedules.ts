// src/lib/api/schedules.ts — Scheduled reports API
import { fetchClient } from './client';

export interface Schedule {
  id: string;
  email_to: string;
  frequency: string;
  is_active: boolean;
  last_run_at?: string;
  [key: string]: any;
}

export const ScheduleAPI = {
  list: () => fetchClient("/schedules/"),
  create: (data: any) => fetchClient("/schedules/", { method: "POST", body: JSON.stringify(data) }),
  remove: (id: string) => fetchClient(`/schedules/${id}`, { method: "DELETE" }),
  trigger: (id: string) => fetchClient(`/schedules/${id}/trigger`, { method: "POST" })
};
