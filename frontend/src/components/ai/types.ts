export interface TraceStep {
  step: number;
  tool: string;
  thought: string;
  latencyMs?: number;
}

export interface ToolTraceStep {
  type: "tool_call";
  tool: string;
  args?: Record<string, unknown>;
  status: "running" | "completed";
  result?: string;
}

export interface RunLog {
  runId: string;
  status: string;
  latencyMs: number;
  tokenUsage: number;
  costUsd: number;
  model?: string;
  trace?: TraceStep[];
  toolTrace?: ToolTraceStep[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: "copilot" | "omni";
  trace?: TraceStep[];
  toolTrace?: ToolTraceStep[];
  tokensUsed?: number;
  costUsd?: number;
  feedbackMessageId?: string;
  feedback?: "none" | "up" | "down";
  feedbackComment?: string;
  showFeedbackInput?: boolean;
  approvalRequestId?: string;
  approvalStatus?: "pending" | "approved" | "rejected";
  runLog?: RunLog;
}
