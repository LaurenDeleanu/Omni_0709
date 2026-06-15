// src/lib/api/admin.ts — Administration API
import { fetchClient } from './client';

export interface AdminDashboardSummary {
  generated_at: string;
  people: {
    total_employees: number;
    active_employees: number;
    new_hires_7d: number;
    headcount_by_department: { department: string; count: number }[];
  };
  ai_agents: {
    total_runs: number;
    runs_this_month: number;
    success_rate: number;
    cost_this_month: number;
  };
  finance: {
    pending_expenses: number;
    pending_expense_amount: number;
    payroll_summary: { month: string; currency: string; total_gross: number; total_net: number; payslip_count: number }[];
  };
  hiring: {
    active_candidates: number;
    funnel_by_stage: Record<string, number>;
  };
  training: {
    active_enrollments: number;
    completion_rates: { course_id: string; completion_rate: number }[];
  };
  engagement: {
    kudos_7d: number;
    unread_notifications: number;
  };
}

export const AdminAPI = {
  getDashboardSummary: () => fetchClient("/admin/dashboard-summary"),
  getAuditLogs: () => fetchClient("/admin/audit-logs"),
  getModules: () => fetchClient("/admin/modules"),
  toggleModules: (data: { enabled_modules: Record<string, boolean> }) => fetchClient("/admin/modules/toggle", { method: "POST", body: JSON.stringify(data) }),
  assignCourse: (data: { user_ids: string[]; course_id: string }) => fetchClient("/admin/assignments/courses", { method: "POST", body: JSON.stringify(data) }),
  assignTask: (data: { user_ids: string[]; title: string; description?: string; due_date?: string; priority?: string }) => fetchClient("/admin/assignments/tasks", { method: "POST", body: JSON.stringify(data) }),
  getAssignmentsStatus: () => fetchClient("/admin/assignments/status"),
  getUsers: () => fetchClient("/admin/users"),
  updateUserRole: (userId: string, data: { role: string }) => fetchClient(`/admin/users/${userId}/role`, { method: "POST", body: JSON.stringify(data) }),
  getRoles: () => fetchClient("/admin/roles"),
  createRole: (data: { name: string; description?: string; permissions: string[] }) => fetchClient("/admin/roles", { method: "POST", body: JSON.stringify(data) }),
  getPermissions: () => fetchClient("/admin/permissions"),
  updateRole: (roleId: string, data: { name: string; description?: string; permissions: string[] }) => fetchClient(`/admin/roles/${roleId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteRole: (roleId: string) => fetchClient(`/admin/roles/${roleId}`, { method: "DELETE" })
};
