"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, Check, X, GitBranch } from "lucide-react";

interface TraceStep {
  step: number;
  thought: string;
  tool: string;
  arguments: any;
  timestamp: string;
  latencyMs: number;
}

interface Proposal {
  id: string;
  title: string;
  description: string;
  branchName: string;
  status: string;
  fileCount: number;
}

interface AgentPanelProps {
  executing: boolean;
  onExecute: (prompt: string) => void;
  traces: TraceStep[];
  proposals: Proposal[];
  onApplyProposal: (id: string) => void;
  onRejectProposal: (id: string) => void;
  onApplyAllProposals: () => void;
}

export default function AgentPanel({
  executing,
  onExecute,
  traces,
  proposals,
  onApplyProposal,
  onRejectProposal,
  onApplyAllProposals,
}: AgentPanelProps) {
  const [activeTab, setActiveTab] = useState<"chat" | "traces" | "proposals">("chat");
  const [prompt, setPrompt] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "assistant"; content: string }[]>([
    {
      role: "assistant",
      content: "I'm the Omni Master Agent. Describe what you'd like me to do in the codebase.",
    },
  ]);

  const tabs = [
    { id: "chat" as const, label: "Chat" },
    { id: "traces" as const, label: "Traces" },
    { id: "proposals" as const, label: "Proposals" },
  ];

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || executing) return;
    const msg = prompt.trim();
    setPrompt("");
    setChatHistory((prev) => [...prev, { role: "user", content: msg }]);
    onExecute(msg);
  };

  return (
    <div className="w-[300px] bg-[#1e1e1e] border-l border-[#333333] flex flex-col shrink-0">
      <div className="flex items-center bg-[#252526] border-b border-[#333333]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors ${
              activeTab === tab.id
                ? "text-white border-b-2 border-b-[#007acc]"
                : "text-[#858585] hover:text-[#cccccc]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {activeTab === "chat" && (
          <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {chatHistory.map((msg, i) => (
                <div
                  key={i}
                  className={`rounded-lg p-2.5 text-[13px] leading-relaxed border ${
                    msg.role === "user"
                      ? "bg-[#0e639c]/20 border-[#0e639c]/30 text-[#cccccc] ml-4"
                      : "bg-[#2d2d2d] border-[#333333] text-[#cccccc] mr-4"
                  }`}
                >
                  <div className="text-[10px] text-[#858585] uppercase tracking-wider mb-1 font-semibold">
                    {msg.role === "user" ? "You" : "Omni Agent"}
                  </div>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
              ))}
              {executing && (
                <div className="flex items-center gap-2 text-[13px] text-[#858585] bg-[#2d2d2d] border border-[#333333] rounded-lg p-3 mr-4">
                  <Loader2 size={14} className="animate-spin" />
                  Executing directive...
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div>
        )}

        {activeTab === "traces" && (
          <div className="p-3">
            {traces.length === 0 ? (
              <div className="text-[13px] text-[#858585] text-center py-6">
                No execution traces yet.
                <br />
                Send a directive to begin.
              </div>
            ) : (
              <div className="relative border-l border-[#333333] ml-3 pl-4 space-y-4">
                {traces.map((step, idx) => (
                  <div key={idx} className="relative">
                    <div className="absolute -left-[21px] top-1 w-2 h-2 rounded-full border border-[#007acc] bg-[#1e1e1e]" />
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] text-[#858585]">
                        <span className="font-semibold text-[#cccccc] uppercase tracking-wider">
                          Step {step.step}: {step.tool}
                        </span>
                        <span>{step.latencyMs}ms</span>
                      </div>
                      <p className="text-[12px] text-[#858585] italic bg-[#2d2d2d]/50 p-2 rounded border border-[#333333]/30">
                        &ldquo;{(step.thought as string) || ""}&rdquo;
                      </p>
                      {step.tool === "codebase_write_file" && step.arguments?.path && (
                        <div className="bg-[#007acc]/10 border border-[#007acc]/20 rounded px-2 py-1">
                          <span className="text-[11px] text-[#569cd6]">
                            Wrote: {(step.arguments.path as string).split("/").pop()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "proposals" && (
          <div className="p-3">
            {proposals.length === 0 ? (
              <div className="text-[13px] text-[#858585] text-center py-6">
                No pending proposals.
              </div>
            ) : (
              <div className="space-y-3">
                {proposals.length > 1 && (
                  <button
                    onClick={onApplyAllProposals}
                    className="w-full flex items-center justify-center gap-1 text-[12px] bg-[#0e639c] hover:bg-[#1177bb] text-white rounded py-1.5 font-semibold mb-2"
                  >
                    <Check size={14} />
                    Apply All Proposals
                  </button>
                )}
                {proposals.map((p) => (
                  <div
                    key={p.id}
                    className="bg-[#2d2d2d] border border-[#333333] rounded-lg p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[13px] font-semibold text-[#cccccc] truncate">
                        {p.title}
                      </span>
                      <span className="text-[10px] text-[#858585] bg-[#333333] px-1.5 py-0.5 rounded">
                        {p.status.toUpperCase()}
                      </span>
                    </div>
                    {p.description && (
                      <p className="text-[12px] text-[#858585] line-clamp-2">{p.description}</p>
                    )}
                    <div className="flex items-center gap-1 text-[11px] text-[#858585]">
                      <GitBranch size={12} />
                      {p.branchName}
                      <span className="ml-auto">{p.fileCount} files</span>
                    </div>
                    <div className="flex gap-1.5 pt-1">
                      <button
                        onClick={() => onApplyProposal(p.id)}
                        className="flex-1 flex items-center justify-center gap-1 text-[11px] bg-green-700/50 hover:bg-green-700 text-green-300 rounded py-1 font-semibold"
                      >
                        <Check size={12} />
                        Apply
                      </button>
                      <button
                        onClick={() => onRejectProposal(p.id)}
                        className="flex-1 flex items-center justify-center gap-1 text-[11px] bg-red-700/50 hover:bg-red-700 text-red-300 rounded py-1 font-semibold"
                      >
                        <X size={12} />
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-2 border-t border-[#333333] bg-[#252526]">
        <div className="flex gap-1.5">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            disabled={executing}
            placeholder="Type a directive..."
            className="flex-1 h-14 bg-[#3c3c3c] border border-[#454545] focus:border-[#007acc] rounded px-2.5 py-1.5 text-[13px] text-[#cccccc] placeholder-[#858585] outline-none resize-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={executing || !prompt.trim()}
            className="self-end p-2 bg-[#0e639c] hover:bg-[#1177bb] disabled:bg-[#3c3c3c] disabled:text-[#858585] text-white rounded transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </div>
  );
}
