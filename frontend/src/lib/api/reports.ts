// src/lib/api/reports.ts — Reports API
import { fetchClient, downloadBlob } from './client';

export interface ReportSummary {
  total_employees: number;
  active_employees: number;
  inactive_employees: number;
  departments: { name: string; count: number }[];
  roles_breakdown: { name: string; count: number; percentage: number }[];
}

export interface DashboardSummary {
  total_employees: number;
  active_employees: number;
  inactive_employees: number;
  unique_departments: number;
  departments: { name: string; count: number }[];
  recent_employees: { id: string; full_name: string; department: string; role: string; created_at: string | null }[];
}

export interface HeadcountData {
  total: number;
  active: number;
  inactive: number;
  by_department: { name: string; count: number }[];
  by_role: { name: string; count: number }[];
}

export interface DepartmentData {
  name: string;
  count: number;
  percentage: number;
}

export interface TurnoverData {
  rate: number;
  active: number;
  inactive: number;
}

export interface AttendanceDay {
  date: string;
  count: number;
  percentage: number;
}

export interface AttendanceData {
  rate: number;
  today_count: number;
  total: number;
  by_day: AttendanceDay[];
}

export interface CostCategory {
  category: string;
  amount: number;
}

export interface CostData {
  total: number;
  by_category: CostCategory[];
  currency: string;
}

export interface DashboardData {
  headcount?: HeadcountData;
  departments?: DepartmentData[];
  turnover?: TurnoverData;
  attendance?: AttendanceData;
  cost?: CostData;
}

export const ReportAPI = {
  getSummary: () => fetchClient("/reports/summary"),
  getDashboard: () => fetchClient("/reports/dashboard"),
  getDashboardData: (metrics: string[]) => {
    const q = metrics.join(",");
    return fetchClient(`/reports/dashboard/data?metrics=${encodeURIComponent(q)}`);
  },
  downloadPDF: () => downloadBlob("/reports/export/executive", "executive_report.pdf"),
  downloadExcel: () => downloadBlob("/reports/export/excel", "empleados.xlsx"),
  exportCustomReport: (format: string) =>
    downloadBlob(`/reports/export/custom?format=${encodeURIComponent(format)}`, `custom_report.${format}`),
};
