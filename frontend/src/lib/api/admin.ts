// src/lib/api/admin.ts — Administration API
import { fetchClient } from './client';

export const AdminAPI = {
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
