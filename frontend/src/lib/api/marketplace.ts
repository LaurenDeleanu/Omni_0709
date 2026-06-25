// src/lib/api/marketplace.ts — Agent Marketplace API
import { fetchClient } from './client';

export const MarketplaceAPI = {
  getAgents: (category?: string) => {
    const url = category ? `/marketplace/agents?category=${category}` : "/marketplace/agents";
    return fetchClient(url);
  },
  getAgent: (agentId: string) => fetchClient(`/marketplace/agents/${agentId}`),
  publishAgent: (agentId: string, data: any) => fetchClient(`/marketplace/agents/${agentId}/publish`, { method: "POST", body: JSON.stringify(data) }),
  installAgent: (agentId: string) => fetchClient(`/marketplace/agents/${agentId}/install`, { method: "POST" }),
  getCategories: () => fetchClient("/marketplace/categories"),
};
