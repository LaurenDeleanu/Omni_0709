// src/lib/api/it.ts — IT management API
import { fetchClient } from './client';

export const ITAPI = {
  getAssets: (category?: string, status?: string) => {
    let query = "";
    const params = [];
    if (category) params.push(`category=${category}`);
    if (status) params.push(`status=${status}`);
    if (params.length) query = `?${params.join("&")}`;
    return fetchClient(`/it/assets${query}`);
  },
  createAsset: (data: any) => fetchClient("/it/assets", { method: "POST", body: JSON.stringify(data) }),
  updateAsset: (id: string, data: any) => fetchClient(`/it/assets/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAsset: (id: string) => fetchClient(`/it/assets/${id}`, { method: "DELETE" }),
  getTickets: (status?: string, requesterId?: string) => {
    let query = "";
    const params = [];
    if (status) params.push(`status=${status}`);
    if (requesterId) params.push(`requester_id=${requesterId}`);
    if (params.length) query = `?${params.join("&")}`;
    return fetchClient(`/it/tickets${query}`);
  },
  createTicket: (data: any) => fetchClient("/it/tickets", { method: "POST", body: JSON.stringify(data) }),
  updateTicket: (id: string, data: any) => fetchClient(`/it/tickets/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  getLicenses: (assignedToId?: string) => {
    const query = assignedToId ? `?assigned_to_id=${assignedToId}` : "";
    return fetchClient(`/it/licenses${query}`);
  },
  createLicense: (data: any) => fetchClient("/it/licenses", { method: "POST", body: JSON.stringify(data) }),
  updateLicense: (id: string, data: any) => fetchClient(`/it/licenses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteLicense: (id: string) => fetchClient(`/it/licenses/${id}`, { method: "DELETE" }),
  getAnalyticsOData: () => fetchClient("/it/analytics/odata"),
  getRequisitions: () => fetchClient("/it/requisitions"),
  createRequisition: (data: any) => fetchClient("/it/requisitions", { method: "POST", body: JSON.stringify(data) }),
  updateRequisitionStatus: (id: string, status: string) => fetchClient(`/it/requisitions/${id}/status`, { method: "PUT", body: JSON.stringify({ status }) }),

  searchKB: (query: string, topK: number = 5) => fetchClient(`/it/kb/search?query=${encodeURIComponent(query)}&top_k=${topK}`),
  listKBArticles: (page: number = 1, pageSize: number = 20, category?: string) => {
    let qs = `page=${page}&page_size=${pageSize}`;
    if (category) qs += `&category=${encodeURIComponent(category)}`;
    return fetchClient(`/it/kb/articles?${qs}`);
  },
  indexKBTickets: () => fetchClient("/it/kb/index-tickets", { method: "POST" }),
  generateKBArticle: (ticketId: string) => fetchClient(`/it/kb/generate-article/${ticketId}`, { method: "POST" }),
  getRecurringIssues: () => fetchClient("/it/kb/recurring-issues"),
  getPreventiveActions: (category?: string) => {
    const qs = category ? `?category=${encodeURIComponent(category)}` : "";
    return fetchClient(`/it/kb/preventive-actions${qs}`);
  },
  getSlaSummary: () => fetchClient("/it/sla/summary"),
};
