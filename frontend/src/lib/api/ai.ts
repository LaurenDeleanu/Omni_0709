// src/lib/api/ai.ts — AI orchestration API
import { fetchClient } from './client';

export const AiAPI = {
  generateModule: (prompt: string) => fetchClient("/ai/generate", { method: "POST", body: JSON.stringify({ prompt }) })
};

export const CopilotAPI = {
  sendFeedback: (messageId: string, rating: "up" | "down", comment?: string) =>
    fetchClient("/ai/copilot/feedback", { method: "POST", body: JSON.stringify({ message_id: messageId, rating, comment }) }),
  getSessions: () => fetchClient("/ai/copilot/sessions"),
  getSession: (sessionId: string) => fetchClient(`/ai/copilot/sessions/${sessionId}`),
};
