import { Bot, MessageSquare, GitMerge, Zap, Cpu, Activity, Clock, Terminal, Users, Play } from "lucide-react";

export interface NodeItem {
  v: string;
  l: string;
  desc: string;
  reqTier: "FREE" | "PRO" | "ENTERPRISE";
  icon: string;
}

export interface NodeCategory {
  name: string;
  icon: any;
  items: NodeItem[];
}

export const NODE_CATEGORIES: NodeCategory[] = [
  {
    name: "Triggers & Starts",
    icon: Play,
    items: [
      { v: "WELCOME", l: "Welcome message", desc: "Initial client WhatsApp/Web welcome message.", reqTier: "FREE", icon: "👋" },
      { v: "WEBHOOK_TRIGGER", l: "Webhook Trigger", desc: "Start execution when an HTTP API webhook payload is received.", reqTier: "ENTERPRISE", icon: "🔌" },
      { v: "SCHEDULE_TRIGGER", l: "Cron Trigger", desc: "Trigger workflow periodically based on a cron expression.", reqTier: "PRO", icon: "⏱️" },
    ]
  },
  {
    name: "AI & Decision",
    icon: Bot,
    items: [
      { v: "AI_DECISION", l: "AI Routing Decision", desc: "LLM parses text/state and routes flow along the matching branch.", reqTier: "PRO", icon: "🧠" },
      { v: "AI_RESPONDER", l: "RAG Q&A responder", desc: "Uses LLM + Vector Knowledge docs to answer user questions.", reqTier: "FREE", icon: "📚" },
      { v: "AUTONOMOUS_AGENT", l: "Autonomous Agent", desc: "An unscripted conversational LLM loop with dynamic tool calling.", reqTier: "PRO", icon: "🤖" },
      { v: "SUB_AGENT", l: "Invoke Sub-Agent", desc: "Delegate a task to a specialized agent (e.g., Code Gen, Translator).", reqTier: "PRO", icon: "👥" },
    ]
  },
  {
    name: "CRM & Data",
    icon: Users,
    items: [
      { v: "CRM_ACTION", l: "CRM Action", desc: "Create, update, or query contacts and deal records inside the CRM.", reqTier: "FREE", icon: "👤" },
      { v: "DATA_TRANSFORM", l: "Data Transform", desc: "Filter, map, or format data structures between workflow nodes.", reqTier: "FREE", icon: "🔄" },
      { v: "COLLECT_FIELD", l: "Collect text input", desc: "Prompt the user for a field and store the response in a variable.", reqTier: "FREE", icon: "📝" },
      { v: "BOOKING", l: "Calendar Booking", desc: "Allows users to book an appointment based on a calendar schedule.", reqTier: "PRO", icon: "📅" },
    ]
  },
  {
    name: "Code & DevOps",
    icon: Terminal,
    items: [
      { v: "CODE_GENERATE", l: "AI Code Generate", desc: "Ask LLM to scaffold code files or modules dynamically.", reqTier: "ENTERPRISE", icon: "💻" },
      { v: "GIT_COMMIT", l: "Git Commit & Push", desc: "Save code to a feature branch on GitHub, GitLab, or Bitbucket.", reqTier: "ENTERPRISE", icon: "🐙" },
    ]
  },
  {
    name: "Control Flow",
    icon: GitMerge,
    items: [
      { v: "CONDITION", l: "If / Else Condition", desc: "Branch the execution flow based on exact variables values.", reqTier: "FREE", icon: "🔀" },
      { v: "PARALLEL_SPLIT", l: "Parallel Split", desc: "Execute multiple workflow branches simultaneously.", reqTier: "PRO", icon: "⛓️" },
      { v: "MERGE", l: "Join & Merge", desc: "Wait for parallel split threads to complete and combine payloads.", reqTier: "PRO", icon: "🤝" },
      { v: "LOOP", l: "Loop Iterator", desc: "Iterate over arrays, lists, or items executing a sub-sequence.", reqTier: "PRO", icon: "🔁" },
      { v: "APPROVAL_GATE", l: "Human Approval Gate", desc: "Halt automation execution until a supervisor approves it.", reqTier: "PRO", icon: "🛡️" },
    ]
  },
  {
    name: "Communication",
    icon: MessageSquare,
    items: [
      { v: "CHOICE_LIST", l: "Buttons List Menu", desc: "Offer button choices menu to WhatsApp/Web users.", reqTier: "FREE", icon: "📋" },
      { v: "NOTIFICATION", l: "Send Notification", desc: "Send automated email, SMS, or Slack alerts.", reqTier: "FREE", icon: "📢" },
      { v: "HUMAN_TAKEOVER", l: "Supervisor Handoff", desc: "Stop execution and trigger a manual chat notification.", reqTier: "FREE", icon: "🎧" },
      { v: "COMPLETED", l: "End Workflow", desc: "Mark the absolute completion of the workflow execution run.", reqTier: "FREE", icon: "✅" },
    ]
  }
];

export const nodeIcons: Record<string, string> = {
  WELCOME: "👋", WEBHOOK_TRIGGER: "🔌", SCHEDULE_TRIGGER: "⏱️",
  AI_DECISION: "🧠", AI_RESPONDER: "📚", AUTONOMOUS_AGENT: "🤖", SUB_AGENT: "👥",
  CRM_ACTION: "👤", DATA_TRANSFORM: "🔄", COLLECT_FIELD: "📝",
  CODE_GENERATE: "💻", GIT_COMMIT: "🐙",
  CONDITION: "🔀", PARALLEL_SPLIT: "⛓️", MERGE: "🤝", LOOP: "🔁", APPROVAL_GATE: "🛡️",
  CHOICE_LIST: "📋", NOTIFICATION: "📢", HUMAN_TAKEOVER: "🎧", COMPLETED: "✅",
  BOOKING: "📅"
};
