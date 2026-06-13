// src/lib/api/legal.ts — Legal & compliance API
import { fetchClient } from './client';

export interface Contract {
  id: string;
  title: string;
  description?: string;
  party_name: string;
  status: string;
  valid_from?: string;
  valid_until?: string;
  document_url?: string;
  created_at: string;
}

export interface WhistleblowerReport {
  id: string;
  tracking_code: string;
  title: string;
  description: string;
  category: string;
  status: string;
  resolution_message?: string;
  is_anonymous: boolean;
  created_at: string;
}

export interface DSARTicket {
  id: string;
  employee_name: string;
  request_type: string;
  status: string;
  details?: string;
  created_at: string;
}

export const LegalAPI = {
  getContracts: () => fetchClient("/legal/contracts"),
  createContract: (data: Partial<Contract>) => fetchClient("/legal/contracts", { method: "POST", body: JSON.stringify(data) }),
  getReports: () => fetchClient("/legal/whistleblower"),
  createReport: (data: Partial<WhistleblowerReport>) => fetchClient("/legal/whistleblower", { method: "POST", body: JSON.stringify(data) }),
  updateReportStatus: (reportId: string, status: string, resolution_message?: string) => fetchClient(`/legal/whistleblower/${reportId}/status`, { method: "PUT", body: JSON.stringify({ status, resolution_message }) }),
  trackReport: (trackingCode: string) => fetchClient(`/legal/whistleblower/track/${trackingCode}`),
  createDsarTicket: (data: { request_type: string, details?: string }) => fetchClient("/legal/dsar", { method: "POST", body: JSON.stringify(data) }),
  getDsarTickets: () => fetchClient("/legal/dsar"),
  updateDsarStatus: (ticketId: string, status: string) => fetchClient(`/legal/dsar/${ticketId}/status`, { method: "PUT", body: JSON.stringify({ status }) }),
};
