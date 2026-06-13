// src/lib/api/rbac.ts — Role-Based Access Control API
import { fetchClient } from './client';

export interface Permission {
  id: string;
  module: string;
  action: string;
  description?: string;
}

export interface RolePermission {
  id: string;
  role_id: string;
  permission_id: string;
  permission: Permission;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  is_system_default: boolean;
  created_at: string;
  permissions: RolePermission[];
}

export const RBACAPI = {
  getPermissions: () => fetchClient("/rbac/permissions"),
  getRoles: () => fetchClient("/rbac/roles"),
  createRole: (data: { name: string, description?: string, permission_ids: string[] }) => fetchClient("/rbac/roles", { method: "POST", body: JSON.stringify(data) }),
  updateRole: (id: string, data: { name?: string, description?: string, permission_ids?: string[] }) => fetchClient(`/rbac/roles/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteRole: (id: string) => fetchClient(`/rbac/roles/${id}`, { method: "DELETE" }),
};
