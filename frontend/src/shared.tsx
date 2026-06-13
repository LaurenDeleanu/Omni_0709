import React from 'react';

export interface Bot {
  id: string;
  name: string;
  avatar: string | null;
  primaryColor: string;
  platform: string;
  aiModel?: string;
  aiSystemPrompt?: string;
  aiTemperature?: number | string;
  aiTone?: string;
  aiKnowledgeBase?: string;
  aiGuardrails?: string;
  aiTools?: string;
  _count?: { clients: number; steps: number };
}
export interface Client {
  id: string;
  name: string | null;
  phone: string | null;
  whatsappNumber?: string;
  email: string | null;
  status: string;
  createdAt: string;
  updatedAt?: string;
  leadStage?: string;
  messages?: Msg[];
}
export interface Msg {
  id: string;
  content: string;
  role: "USER" | "BOT" | "SYSTEM" | "ASSISTANT";
  direction?: "INBOUND" | "OUTBOUND" | "incoming" | "outgoing";
  sender?: string;
  mediaUrl?: string;
  createdAt: string;
}
export interface Step {
  id: string;
  name: string;
  type: string;
  order: number;
  label?: string;
  config: any;
  nextStepId: string | null;
}
export function Portal({ children }: { children: React.ReactNode }) {
  if (typeof window === "undefined") return null;
  const portalRoot = document.getElementById("portal-root");
  if (!portalRoot) return <>{children}</>;
  const { createPortal } = require("react-dom");
  return createPortal(children, portalRoot);
}
