// src/lib/api/agents.ts — AI Agents API
import { fetchClient } from './client';

export interface Agent {
  id: string;
  name: string;
  avatar?: string;
  agentType?: string;
  aiModel?: string;
  aiSystemPrompt?: string;
  aiTemperature?: number;
  aiTone?: string;
  aiGuardrails?: string;
  aiTools?: string;
  aiFallbackModels?: string;
  aiKnowledgeBase?: string;
  aiVisionModel?: string;
  is_active: boolean;
  [key: string]: any;
}

export const AgentsAPI = {
  getAgents: () => fetchClient("/agents"),
  createAgent: (data: Partial<Agent>) => fetchClient("/agents", { method: "POST", body: JSON.stringify(data) }),
  getAgent: (agentId: string) => fetchClient(`/agents/${agentId}`),
  updateAgent: (agentId: string, data: Partial<Agent>) => fetchClient(`/agents/${agentId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteAgent: (agentId: string) => fetchClient(`/agents/${agentId}`, { method: "DELETE" }),
  
  runAgent: (agentId: string, data: any) => fetchClient(`/agents/${agentId}/run`, { method: "POST", body: JSON.stringify(data) }),
  getExecutionRuns: (agentId: string) => fetchClient(`/agents/${agentId}/execution-runs`),
  
  uploadKnowledge: (agentId: string, formData: FormData) => fetchClient(`/agents/${agentId}/knowledge/upload`, { method: "POST", body: formData }),
  getKnowledge: (agentId: string) => fetchClient(`/agents/${agentId}/knowledge`),
  deleteKnowledge: (agentId: string, docId: string) => fetchClient(`/agents/${agentId}/knowledge/${docId}`, { method: "DELETE" }),
  
  getPromptVersions: (agentId: string) => fetchClient(`/agents/${agentId}/prompt-versions`),
  rollbackPrompt: (agentId: string, data: any) => fetchClient(`/agents/${agentId}/prompt-versions/rollback`, { method: "POST", body: JSON.stringify(data) }),
  
  getTriggers: (agentId: string) => fetchClient(`/agents/${agentId}/triggers`),
  createTrigger: (agentId: string, data: any) => fetchClient(`/agents/${agentId}/triggers`, { method: "POST", body: JSON.stringify(data) }),
  deleteTrigger: (agentId: string, triggerId: string) => fetchClient(`/agents/${agentId}/triggers/${triggerId}`, { method: "DELETE" }),
  
  getBudgets: () => fetchClient("/agents/budgets"),
  getSettings: () => fetchClient("/agents/settings"),
};
