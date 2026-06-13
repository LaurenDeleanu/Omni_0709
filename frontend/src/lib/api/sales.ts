// src/lib/api/sales.ts — CRM & Sales API
import { fetchClient } from './client';

export interface Client {
  id: string;
  company_name: string;
  industry?: string;
  website?: string;
  primary_contact_name?: string;
  primary_contact_email?: string;
  primary_contact_phone?: string;
  created_at: string;
}

export interface Lead {
  id: string;
  title: string;
  client_id?: string;
  contact_name?: string;
  company_name?: string;
  email?: string;
  phone?: string;
  estimated_value: number;
  probability: number;
  stage: string;
  expected_close_date?: string;
  created_at: string;
}

export const SalesAPI = {
  getLeads: () => fetchClient("/sales/leads"),
  createLead: (data: Partial<Lead>) => fetchClient("/sales/leads", { method: "POST", body: JSON.stringify(data) }),
  updateLead: (leadId: string, data: Partial<Lead>) => fetchClient(`/sales/leads/${leadId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteLead: (leadId: string) => fetchClient(`/sales/leads/${leadId}`, { method: "DELETE" }),
  updateLeadStage: (leadId: string, stage: string) => fetchClient(`/sales/leads/${leadId}/stage`, { method: "PATCH", body: JSON.stringify({ stage }) }),
  getClients: () => fetchClient("/sales/clients"),
  createClient: (data: Partial<Client>) => fetchClient("/sales/clients", { method: "POST", body: JSON.stringify(data) }),
  updateClient: (clientId: string, data: Partial<Client>) => fetchClient(`/sales/clients/${clientId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteClient: (clientId: string) => fetchClient(`/sales/clients/${clientId}`, { method: "DELETE" }),
};
