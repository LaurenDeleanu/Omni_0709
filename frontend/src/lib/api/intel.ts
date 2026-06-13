// src/lib/api/intel.ts — Intelligence & analytics API
import { fetchClient } from './client';

export interface DashboardWidget {
  id: string;
  dashboard_id: string;
  title: string;
  widget_type: string;
  data_source: string;
  config?: Record<string, any>;
  layout_x?: number;
  layout_y?: number;
  layout_w?: number;
  layout_h?: number;
}

export interface Dashboard {
  id: string;
  name: string;
  description?: string;
  owner_id?: string;
  is_public: boolean;
  created_at: string;
  widgets: DashboardWidget[];
}

export const IntelAPI = {
  getDashboards: () => fetchClient("/intel/dashboards"),
  createDashboard: (data: Partial<Dashboard>) => fetchClient("/intel/dashboards", { method: "POST", body: JSON.stringify(data) }),
  deleteDashboard: (id: string) => fetchClient(`/intel/dashboards/${id}`, { method: "DELETE" }),
  createWidget: (data: Partial<DashboardWidget>) => fetchClient("/intel/widgets", { method: "POST", body: JSON.stringify(data) }),
  deleteWidget: (id: string) => fetchClient(`/intel/widgets/${id}`, { method: "DELETE" }),
  getWidgetData: (source: string) => fetchClient(`/intel/data/${source}`),
};
