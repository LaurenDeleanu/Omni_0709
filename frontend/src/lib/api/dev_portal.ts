// src/lib/api/dev_portal.ts — Developer Portal & Webhooks API
import { fetchClient } from './client';

export const DevPortalAPI = {
  createApiKey: (label: string, scopes: string[]) => fetchClient("/dev/api-keys", { method: "POST", body: JSON.stringify({ name: label, scopes }) }),
  getApiKeys: () => fetchClient("/dev/api-keys"),
  deleteApiKey: (keyId: string) => fetchClient(`/dev/api-keys/${keyId}`, { method: "DELETE" }),
  getUsageStats: () => fetchClient("/dev/usage"),
  
  createWebhook: (data: { url: string; events: string[]; description?: string }) => fetchClient("/webhooks", { method: "POST", body: JSON.stringify(data) }),
  getWebhooks: () => fetchClient("/webhooks"),
  deleteWebhook: (webhookId: string) => fetchClient(`/webhooks/${webhookId}`, { method: "DELETE" }),
  testWebhook: (webhookId: string, eventName: string, payload?: any) => fetchClient("/webhooks/test", { method: "POST", body: JSON.stringify({ webhook_id: webhookId, event_name: eventName, payload }) }),
};
