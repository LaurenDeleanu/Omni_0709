// src/lib/api/time_tracking.ts — Time Clock & Time Tracking API
import { fetchClient } from './client';

export const TimeTrackingAPI = {
  clockIn: (notes: string = "", projectId: string = "", taskId: string = "") => fetchClient("/time-tracking/in", { method: "POST", body: JSON.stringify({ notes, project_id: projectId, task_id: taskId }) }),
  clockOut: (notes: string = "") => fetchClient("/time-tracking/out", { method: "POST", body: JSON.stringify({ notes }) }),
  getActiveSession: () => fetchClient("/time-tracking/active"),
  getLogs: (startDate: string = "", endDate: string = "", limit: number = 50) => fetchClient(`/time-tracking/logs?start_date=${startDate}&end_date=${endDate}&limit=${limit}`),
  getSummary: (startDate: string = "", endDate: string = "") => fetchClient(`/time-tracking/summary?start_date=${startDate}&end_date=${endDate}`),
};
