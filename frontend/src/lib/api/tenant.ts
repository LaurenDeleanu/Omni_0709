// src/lib/api/tenant.ts — Tenant settings API
import { fetchClient } from './client';

export interface TenantSettings {
  primary_color?: string;
  [key: string]: any;
}

export const TenantAPI = {
  getSettings: () => fetchClient("/tenant/settings"),
  updateSettings: (data: Partial<TenantSettings>) => fetchClient("/tenant/settings", { method: "PUT", body: JSON.stringify(data) }),
  uploadLogo: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchClient("/tenant/logo", { method: "POST", body: formData });
  }
};
