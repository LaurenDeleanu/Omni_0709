// src/lib/api/billing.ts — Billing & API Keys API
import { fetchClient } from './client';

export interface BillingSettings {
  tier: string;
  currentDebt: number;
  customOpenAiKey?: string;
  customGeminiKey?: string;
  customOpenRouterKey?: string;
  customAnthropicKey?: string;
  customGrokKey?: string;
  customGroqKey?: string;
}

export const BillingAPI = {
  getSettings: () => fetchClient("/billing/settings"),
  updateSettings: (data: Partial<BillingSettings>) => fetchClient("/billing/settings", { method: "PATCH", body: JSON.stringify(data) }),
  checkout: (action: string, tier?: string, amountToPay?: number) => fetchClient("/billing/checkout", { method: "POST", body: JSON.stringify({ action, tier, amountToPay }) }),
  getQuotas: () => fetchClient("/billing/quotas"),
  getUsage: (days: number = 30) => fetchClient(`/billing/usage?days=${days}`),
  getMonthlyBill: (month?: string) => {
    const url = month ? `/billing/bill?month=${month}` : "/billing/bill";
    return fetchClient(url);
  },
  
  createApiKey: (label: string, scopes: string[]) => fetchClient("/billing/api-keys", { method: "POST", body: JSON.stringify({ label, scopes }) }),
  getApiKeys: () => fetchClient("/billing/api-keys"),
  revokeApiKey: (keyHash: string) => fetchClient(`/billing/api-keys/${keyHash}/revoke`, { method: "POST" }),
  rotateApiKey: (keyHash: string) => fetchClient(`/billing/api-keys/${keyHash}/rotate`, { method: "POST" }),
};
