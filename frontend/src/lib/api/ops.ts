// src/lib/api/ops.ts — Operations & facilities API
import { fetchClient } from './client';

export interface FacilityAsset {
  id: string;
  name: string;
  type: string;
  location?: string;
  status: string;
  created_at: string;
}

export interface AssetBooking {
  id: string;
  asset_id: string;
  employee_id: string;
  start_time: string;
  end_time: string;
  status: string;
  created_at: string;
}

export interface CalendarBooking {
  id: string;
  asset_id: string;
  asset_name?: string;
  asset_type?: string;
  employee_name?: string;
  start_time: string;
  end_time: string;
  status: string;
}

export interface VisitorLog {
  id: string;
  visitor_name: string;
  company?: string;
  host_id: string;
  expected_arrival: string;
  check_in_time?: string;
  check_out_time?: string;
  status: string;
  created_at: string;
}

export interface MaintenanceRequest {
  id: string;
  asset_id?: string;
  title: string;
  description?: string;
  priority: string;
  status: string;
  reported_by_id: string;
  assigned_to_id?: string;
  resolution_notes?: string;
  created_at: string;
  resolved_at?: string;
}

export interface MaintenanceStats {
  total: number;
  reported: number;
  in_progress: number;
  resolved: number;
  closed: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export const OpsAPI = {
  getAssets: (type?: string) => fetchClient(`/ops/assets${type ? `?type=${type}` : ""}`),
  createAsset: (data: Partial<FacilityAsset>) => fetchClient("/ops/assets", { method: "POST", body: JSON.stringify(data) }),
  getBookings: (employeeId?: string) => fetchClient(`/ops/bookings${employeeId ? `?employee_id=${employeeId}` : ""}`),
  createBooking: (data: Partial<AssetBooking>) => fetchClient("/ops/bookings", { method: "POST", body: JSON.stringify(data) }),
  getVisitors: (hostId?: string) => fetchClient(`/ops/visitors${hostId ? `?host_id=${hostId}` : ""}`),
  createVisitor: (data: Partial<VisitorLog>) => fetchClient("/ops/visitors", { method: "POST", body: JSON.stringify(data) }),
  updateVisitor: (visitorId: string, data: Partial<VisitorLog>) => fetchClient(`/ops/visitors/${visitorId}`, { method: "PUT", body: JSON.stringify(data) }),
  checkOutVisitor: (visitorId: string) => fetchClient(`/ops/visitors/${visitorId}/check-out`, { method: "PUT" }),
  getCalendarBookings: (start: string, end: string, assetType?: string) =>
    fetchClient(`/ops/bookings/calendar?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}${assetType ? `&asset_type=${encodeURIComponent(assetType)}` : ""}`),
  getMaintenanceRequests: (status?: string, priority?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (priority) params.set("priority", priority);
    const qs = params.toString();
    return fetchClient(`/ops/maintenance${qs ? `?${qs}` : ""}`);
  },
  createMaintenanceRequest: (data: { title: string; description?: string; asset_id?: string; priority?: string; reported_by_id: string }) =>
    fetchClient("/ops/maintenance", { method: "POST", body: JSON.stringify(data) }),
  updateMaintenanceRequest: (requestId: string, data: Record<string, unknown>) =>
    fetchClient(`/ops/maintenance/${requestId}`, { method: "PUT", body: JSON.stringify(data) }),
  getMaintenanceStats: () => fetchClient("/ops/maintenance/stats"),
};
