"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Bot, User, Play, RefreshCw, Cpu, Activity, Clock, Zap, Brain, Wrench, Eye, ListTodo, CheckCircle2 } from "lucide-react";
import { fetchClient } from "@/lib/api";
import { API_BASE, getCsrfToken } from "@/lib/api/client";

interface Message {
  sender: "user" | "agent";
  content: string;
  timestamp: Date;
  tokens?: number;
  latency?: number;
  tools?: string[];
}

interface TraceStep {
  type: "thought" | "action" | "observation" | "plan" | "step_start" | "step_complete" | "plan_updated" | "status";
  content: string;
  timestamp: Date;
  details?: any;
}

interface AgentTestBenchProps {
  botId: string;
  agentModel: string;
}

export default function AgentTestBench({ botId, agentModel }: AgentTestBenchProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "agent",
      content: "Hello! I am initialized and ready to test. Type any message to simulate a conversation.",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sessionToken, setSessionToken] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Stats panel values
  const [latestLatency, setLatestLatency] = useState<number | null>(null);
  const [latestTokens, setLatestTokens] = useState<number | null>(null);
  const [triggeredTools, setTriggeredTools] = useState<string[]>([]);
  const [traceSteps, setTraceSteps] = useState<TraceStep[]>([]);

  useEffect(() => {
    // Generate a random session token for the test run
    setSessionToken(Math.random().toString(36).substring(2, 15));
  }, [botId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isSending) return;

    const userMessageText = inputValue.trim();
    setInputValue("");
    setIsSending(true);
    setTraceSteps([]);
    setTriggeredTools([]);

    const newMsg: Message = {
      sender: "user",
      content: userMessageText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMsg]);

    const startTime = Date.now();

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      const csrfToken = await getCsrfToken();
      if (csrfToken) {
        headers["X-CSRF-Token"] = csrfToken;
      }

      const response = await fetch(`${API_BASE}/agents/${botId}/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          message: userMessageText,
          collected_data: {
            sender: `test-user-${sessionToken}`,
            sessionToken,
          }
        }),
        credentials: "include",
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response stream body received from backend.");
      }

      // Pre-add a placeholder agent message to append tokens to
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          content: "",
          timestamp: new Date(),
        }
      ]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let currentAgentReply = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("event: ")) {
            currentEvent = trimmed.substring(7).trim();
          } else if (trimmed.startsWith("data: ")) {
            const dataStr = trimmed.substring(6).trim();
            let parsedData: any = null;
            try {
              parsedData = JSON.parse(dataStr);
            } catch (err) {
              console.error("JSON parse error on stream chunk:", dataStr, err);
              continue;
            }

            if (currentEvent === "token") {
              const text = typeof parsedData === "object" && parsedData !== null && "text" in parsedData
                ? parsedData.text
                : String(parsedData);
              currentAgentReply += text;
              setMessages((prev) => {
                const next = [...prev];
                if (next.length > 0 && next[next.length - 1].sender === "agent") {
                  next[next.length - 1].content = currentAgentReply;
                }
                return next;
              });
            } else if (currentEvent === "react_thought") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "thought", content: parsedData, timestamp: new Date() }
              ]);
            } else if (currentEvent === "react_action") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "action", content: `Tool Invoked: ${parsedData.name}`, details: parsedData.args, timestamp: new Date() }
              ]);
              if (parsedData.name) {
                setTriggeredTools((prev) => [...prev, parsedData.name]);
              }
            } else if (currentEvent === "react_observation") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "observation", content: String(parsedData), timestamp: new Date() }
              ]);
            } else if (currentEvent === "plan_created") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "plan", content: "Plan Initialized", details: parsedData, timestamp: new Date() }
              ]);
            } else if (currentEvent === "step_start") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "step_start", content: `Executing step ${parsedData.step_number}: ${parsedData.description}`, timestamp: new Date() }
              ]);
            } else if (currentEvent === "step_complete") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "step_complete", content: `Step ${parsedData.step_number} Completed`, details: parsedData.result, timestamp: new Date() }
              ]);
            } else if (currentEvent === "plan_updated") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "plan_updated", content: "Execution Plan Adjusted", details: parsedData, timestamp: new Date() }
              ]);
            } else if (currentEvent === "status") {
              const statusVal = typeof parsedData === "object" && parsedData !== null && "status" in parsedData
                ? parsedData.status
                : String(parsedData);
              setTraceSteps((prev) => [
                ...prev,
                { type: "status", content: `Status: ${statusVal}`, timestamp: new Date() }
              ]);
            } else if (currentEvent === "paused") {
              setTraceSteps((prev) => [
                ...prev,
                { type: "status", content: "Execution Suspended — Pending HR Gate Approval", details: parsedData, timestamp: new Date() }
              ]);
            } else if (currentEvent === "done") {
              const elapsed = Date.now() - startTime;
              setLatestLatency(parsedData.latency_ms || elapsed);
              setLatestTokens(parsedData.token_usage || null);
              if (parsedData.reply) {
                currentAgentReply = parsedData.reply;
                setMessages((prev) => {
                  const next = [...prev];
                  if (next.length > 0 && next[next.length - 1].sender === "agent") {
                    next[next.length - 1].content = currentAgentReply;
                    next[next.length - 1].latency = parsedData.latency_ms || elapsed;
                    next[next.length - 1].tokens = parsedData.token_usage || null;
                  }
                  return next;
                });
              }
            } else if (currentEvent === "error") {
              throw new Error(parsedData.error || "Execution streaming failed");
            }
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) => {
        // If we added a placeholder, replace/update it; otherwise append
        const next = [...prev];
        if (next.length > 0 && next[next.length - 1].sender === "agent" && next[next.length - 1].content === "") {
          next[next.length - 1].content = `Execution Error: ${err.message || "Failed to execute."}`;
        } else {
          next.push({
            sender: "agent",
            content: `Execution Error: ${err.message || "Failed to execute."}`,
            timestamp: new Date(),
          });
        }
        return next;
      });
    } finally {
      setIsSending(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        sender: "agent",
        content: "Simulator cleared. Ready to start fresh.",
        timestamp: new Date(),
      },
    ]);
    setLatestLatency(null);
    setLatestTokens(null);
    setTriggeredTools([]);
    setTraceSteps([]);
    setSessionToken(Math.random().toString(36).substring(2, 15));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[650px]">
      {/* Messages Panel */}
      <div className="lg:col-span-2 flex flex-col border border-border/10 bg-card/50 rounded-2xl overflow-hidden h-full">
        {/* Header */}
        <div className="flex justify-between items-center px-5 py-3.5 border-b border-border/10 bg-muted/30">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isSending ? "bg-amber-500 animate-pulse" : "bg-emerald-500"}`} />
            <span className="text-xs font-bold text-foreground uppercase tracking-wider">Agent Chat Simulator</span>
          </div>
          <button
            onClick={clearChat}
            className="text-[10px] bg-muted border border-border/20 hover:bg-secondary text-muted-foreground hover:text-foreground py-1 px-2.5 rounded-lg flex items-center gap-1 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Reset
          </button>
        </div>

        {/* Message Logs */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar min-h-0">
          {messages.map((msg, index) => {
            const isUser = msg.sender === "user";
            return (
              <div
                key={index}
                className={`flex gap-3 max-w-[85%] ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
              >
                <div
                  className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 border ${
                    isUser
                      ? "bg-muted border-border text-foreground"
                      : "bg-[var(--color-primary)]/10 border-[var(--color-primary)]/20 text-[var(--color-primary)]"
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div className="flex flex-col gap-1">
                  <div
                    className={`rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                      isUser
                        ? "bg-muted text-foreground border border-border rounded-tr-none"
                        : "bg-[var(--color-muted)] text-foreground border border-border/10 rounded-tl-none"
                    }`}
                  >
                    {msg.content || (isSending && index === messages.length - 1 ? (
                      <span className="flex gap-1 items-center italic text-muted-foreground">
                        Streaming reply...
                      </span>
                    ) : "")}
                  </div>
                  {!isUser && (msg.tokens || msg.latency) && (
                    <div className="flex items-center gap-2 text-[9px] text-muted-foreground font-mono mt-0.5 px-1">
                      {msg.latency && <span>{msg.latency}ms</span>}
                      {msg.tokens && <span>• {msg.tokens} tokens</span>}
                      {msg.tools && msg.tools.length > 0 && (
                        <span>• tools: {msg.tools.join(", ")}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          <div ref={chatEndRef} />
        </div>

        {/* Input bar */}
        <form onSubmit={handleSend} className="p-4 border-t border-border/10 bg-muted/30 flex gap-2">
          <input
            className="input text-xs py-2.5 flex-1 bg-card/60 border-border text-foreground placeholder-zinc-500"
            placeholder="Type your mock message here..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isSending}
          />
          <button
            type="submit"
            disabled={isSending || !inputValue.trim()}
            className="btn-primary p-2.5 rounded-xl shrink-0 h-10 w-10 flex items-center justify-center disabled:opacity-50"
          >
            {isSending ? (
              <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>

      {/* Traces and Metrics Panel */}
      <div className="border border-border/10 bg-muted/30 rounded-2xl p-5 flex flex-col gap-5 h-full overflow-hidden">
        <h3 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5 shrink-0">
          <Cpu className="w-4 h-4 text-[var(--color-primary)]" />
          Trace Inspector
        </h3>

        {/* Parameter values / stats */}
        <div className="grid grid-cols-2 gap-3 shrink-0">
          <div className="bg-card/60 border border-border/20 rounded-xl p-3 flex flex-col gap-1">
            <span className="text-[9px] text-muted-foreground font-mono uppercase">Target LLM Model</span>
            <span className="text-xs font-bold text-foreground font-mono truncate">{agentModel}</span>
          </div>

          <div className="bg-card/60 border border-border/10 rounded-xl p-3 flex flex-col gap-1">
            <span className="text-[9px] text-muted-foreground font-mono uppercase">Execution Latency</span>
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-bold text-foreground font-mono">
                {latestLatency !== null ? `${latestLatency} ms` : "—"}
              </span>
            </div>
          </div>

          <div className="bg-card/60 border border-border/10 rounded-xl p-3 flex flex-col gap-1">
            <span className="text-[9px] text-muted-foreground font-mono uppercase">Token Count</span>
            <div className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-bold text-foreground font-mono">
                {latestTokens !== null ? `${latestTokens} tokens` : "—"}
              </span>
            </div>
          </div>

          <div className="bg-card/60 border border-border/10 rounded-xl p-3 flex flex-col gap-1">
            <span className="text-[9px] text-muted-foreground font-mono uppercase">Invoked Tools</span>
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-bold text-foreground font-mono truncate">
                {triggeredTools.length > 0 ? triggeredTools.join(", ") : "None"}
              </span>
            </div>
          </div>
        </div>

        {/* Live Trace Steps List */}
        <div className="flex-1 flex flex-col min-h-0 border-t border-border/10 pt-4 overflow-hidden">
          <span className="text-[10px] text-muted-foreground font-mono uppercase mb-2 shrink-0">Live Trace Log</span>
          <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-1 min-h-0">
            {traceSteps.length > 0 ? (
              traceSteps.map((step, idx) => {
                let icon = <Cpu className="w-3.5 h-3.5" />;
                let title = "Step";
                let badgeClass = "bg-secondary text-muted-foreground border-border";

                if (step.type === "thought") {
                  icon = <Brain className="w-3.5 h-3.5" />;
                  title = "Agent Thought";
                  badgeClass = "bg-purple-500/10 text-purple-300 border-purple-500/20";
                } else if (step.type === "action") {
                  icon = <Wrench className="w-3.5 h-3.5" />;
                  title = "Action: Tool Call";
                  badgeClass = "bg-amber-500/10 text-amber-300 border-amber-500/20";
                } else if (step.type === "observation") {
                  icon = <Eye className="w-3.5 h-3.5" />;
                  title = "Observation Result";
                  badgeClass = "bg-emerald-500/10 text-emerald-300 border-emerald-500/20";
                } else if (step.type === "plan" || step.type === "plan_updated") {
                  icon = <ListTodo className="w-3.5 h-3.5" />;
                  title = step.type === "plan" ? "Execution Plan" : "Plan Adjusted";
                  badgeClass = "bg-blue-500/10 text-blue-300 border-blue-500/20";
                } else if (step.type === "step_start") {
                  icon = <Play className="w-3.5 h-3.5" />;
                  title = "Start Step";
                  badgeClass = "bg-indigo-500/10 text-indigo-300 border-indigo-500/20";
                } else if (step.type === "step_complete") {
                  icon = <CheckCircle2 className="w-3.5 h-3.5" />;
                  title = "Complete Step";
                  badgeClass = "bg-teal-500/10 text-teal-300 border-teal-500/20";
                } else if (step.type === "status") {
                  icon = <Activity className="w-3.5 h-3.5" />;
                  title = "Status Update";
                  badgeClass = "bg-secondary text-muted-foreground/80 border-border";
                }

                return (
                  <div key={idx} className="bg-card/60 border border-border/10 rounded-xl p-3 space-y-2 text-xs transition-all hover:bg-muted/50">
                    <div className="flex justify-between items-center">
                      <span className={`text-[10px] font-mono border px-2 py-0.5 rounded-lg flex items-center gap-1.5 ${badgeClass}`}>
                        {icon}
                        {title}
                      </span>
                      <span className="text-[9px] text-muted-foreground font-mono">
                        {step.timestamp.toLocaleTimeString()}
                      </span>
                    </div>

                    <p className="text-muted-foreground/80 text-xs font-sans leading-relaxed whitespace-pre-wrap">
                      {step.content}
                    </p>

                    {step.details && (
                      <div className="mt-1.5 p-2 bg-card border border-border/10 rounded-lg text-[10px] font-mono text-muted-foreground overflow-x-auto">
                        {typeof step.details === "object"
                          ? JSON.stringify(step.details, null, 2)
                          : String(step.details)}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-muted-foreground border border-dashed border-border/10 rounded-xl">
                <Activity className="w-8 h-8 text-muted-foreground mb-2 animate-pulse" />
                <span className="text-[11px] font-mono">Awaiting stream execution...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
