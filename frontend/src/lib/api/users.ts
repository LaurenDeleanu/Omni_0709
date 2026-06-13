// src/lib/api/users.ts — User & employee API
import { fetchClient } from './client';

export interface Employee {
  id: string;
  email: string;
  full_name: string;
  department: string;
  role: string;
  is_active: boolean;
  created_at: string;
  [key: string]: any;
}

export const UserAPI = {
  getMe: () => fetchClient("/users/me"),
  getEmployees: async () => {
    const res = await fetchClient("/users");
    return res.items ?? res;
  },
  getEmployee: (id: string) => fetchClient(`/users/${id}`),
  createEmployee: (data: Partial<Employee>) => fetchClient("/users", { method: "POST", body: JSON.stringify(data) }),
  updateEmployee: (id: string, data: Partial<Employee>) => fetchClient(`/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  archiveEmployee: (id: string) => fetchClient(`/users/${id}/archive`, { method: "PATCH" }),
  deleteEmployee: (id: string) => fetchClient(`/users/${id}`, { method: "DELETE" }),
  updateProfile: (data: any) => fetchClient("/users/profile", { method: "PATCH", body: JSON.stringify(data) }),
  getProfileRequests: () => fetchClient("/users/profile-requests"),
  reviewProfileRequest: (id: string, approved: boolean) => fetchClient(`/users/profile-requests/${id}/review`, { method: "POST", body: JSON.stringify({ approved }) })
};

export interface HistoryEntry {
  id: string;
  position: string;
  department: string;
  salary: number;
  currency: string;
  start_date: string;
  end_date?: string;
  notes?: string;
  [key: string]: any;
}

export const HistoryAPI = {
  getHistory: (userId: string) => fetchClient(`/employees/${userId}/history`),
  addEntry: (userId: string, data: any) => fetchClient(`/employees/${userId}/history`, { method: "POST", body: JSON.stringify(data) }),
  updateEntry: (userId: string, entryId: string, data: any) => fetchClient(`/employees/${userId}/history/${entryId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteEntry: (userId: string, entryId: string) => fetchClient(`/employees/${userId}/history/${entryId}`, { method: "DELETE" }),
};
