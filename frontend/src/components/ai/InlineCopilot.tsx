"use client";

import { useState, useRef } from "react";
import { Bot, X, Send, Loader2 } from "lucide-react";
import { API_BASE, getCsrfToken } from "@/lib/api/client";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface QuickAction {
  label: string;
  message: string;
}

interface InlineMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface InlineCopilotProps {
  moduleContext: string;
  placeholder?: string;
  quickActions?: QuickAction[];
}

export function InlineCopilot({ moduleContext, placeholder, quickActions = [] }: InlineCopilotProps) {
  const [expanded, setExpanded] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [messages, setMessages] = useState<InlineMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleQuickAction = (msg: string) => {
    setPrompt(msg);
    if (!expanded) setExpanded(true);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = prompt.trim();
    if (!clean || isLoading) return;

    const userMsg: InlineMessage = { id: `u-${Date.now()}`, role: "user", content: clean };
    setMessages((prev) => [...prev, userMsg]);
    setPrompt("");
    setIsLoading(true);
    setStreamingText("");
    setExpanded(true);

    const controller = new AbortController();
    abortRef.current = controller;
    let fullResponse = "";

    try {
      const modelPreference = typeof window !== "undefined" ? localStorage.getItem("copilot_model") || "gpt-4o-mini" : "gpt-4o-mini";
      const csrfToken = await getCsrfToken();
      const csrfHeaders: Record<string, string> = { "Content-Type": "application/json" };
      if (csrfToken) csrfHeaders["X-CSRF-Token"] = csrfToken;
      const resp = await fetch(`${API_BASE}/ai/copilot/stream`, {
        method: "POST",
        headers: csrfHeaders,
        body: JSON.stringify({ message: clean, module_context: moduleContext.toLowerCase(), model_preference: modelPreference }),
        credentials: "include",
        signal: controller.signal,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Stream error" }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.text) {
                fullResponse += data.text;
                setStreamingText(fullResponse);
              }
            } catch {}
          }
        }
      }

      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: fullResponse || "Done." }]);
    } catch (error: any) {
      if (error.name === "AbortError") return;
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: `Error: ${error.message}` }]);
    } finally {
      setIsLoading(false);
      setStreamingText("");
      abortRef.current = null;
    }
  };

  return (
    <div className="border border-border/50 rounded-xl bg-card/30 backdrop-blur-sm overflow-hidden">
      {!expanded && quickActions.length > 0 && (
        <div className="px-4 pt-3 flex flex-wrap gap-1.5">
          {quickActions.map((qa, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleQuickAction(qa.message)}
              className="text-[10px] text-zinc-400 hover:text-white bg-slate-900/60 border border-zinc-800 hover:border-violet-500/25 px-2.5 py-1.5 rounded-full transition-all text-left truncate max-w-full"
            >
              {qa.label}
            </button>
          ))}
        </div>
      )}

      {expanded && messages.length > 0 && (
        <div className="max-h-[320px] overflow-y-auto p-4 space-y-3 custom-scrollbar bg-slate-950/20">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "assistant" ? "justify-start" : "justify-end"} animate-fade-in`}>
              <div className="flex gap-2 max-w-[85%]">
                {msg.role === "assistant" && (
                  <div className="w-6 h-6 rounded-full bg-indigo-950 border border-violet-500/20 flex items-center justify-center text-[10px] shrink-0 self-start">
                    <Bot size={12} className="text-violet-400" />
                  </div>
                )}
                <div className={`p-3 rounded-2xl text-xs leading-relaxed border ${msg.role === "assistant" ? "bg-slate-900 border-zinc-800 text-zinc-200 rounded-tl-none" : "bg-gradient-to-r from-violet-950/70 to-indigo-950/70 border-violet-500/30 text-white rounded-tr-none"}`}>
                  <MarkdownRenderer content={msg.content} />
                </div>
              </div>
            </div>
          ))}
          {streamingText && (
            <div className="flex justify-start animate-fade-in">
              <div className="flex gap-2 max-w-[85%]">
                <div className="w-6 h-6 rounded-full bg-indigo-950 border border-violet-500/20 flex items-center justify-center text-[10px] shrink-0">
                  <Bot size={12} className="text-violet-400" />
                </div>
                <div className="p-3 rounded-2xl text-xs leading-relaxed bg-slate-900 border border-zinc-800 text-zinc-200 rounded-tl-none">
                  <MarkdownRenderer content={streamingText} />
                  <span className="animate-pulse ml-0.5 text-violet-400">▌</span>
                </div>
              </div>
            </div>
          )}
          {isLoading && !streamingText && (
            <div className="flex justify-start animate-pulse">
              <div className="flex gap-2 max-w-[85%]">
                <Loader2 size={14} className="animate-spin text-violet-400 self-start mt-1" />
                <div className="p-3 rounded-2xl text-xs bg-slate-900 border border-zinc-800 text-zinc-400 rounded-tl-none">
                  Processing...
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      <form onSubmit={handleSend} className="p-3 flex gap-2 bg-slate-950 border-t border-violet-500/10">
        <input
          type="text"
          disabled={isLoading}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={placeholder || `Ask about ${moduleContext}...`}
          className="flex-1 bg-slate-900 border border-zinc-800 focus:border-violet-500/50 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none transition-colors disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading || !prompt.trim()}
          className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 disabled:opacity-50 disabled:from-zinc-800 disabled:to-zinc-800 text-white p-2 rounded-lg transition-all flex items-center justify-center shadow-md shadow-violet-500/10 cursor-pointer"
        >
          {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
        </button>
      </form>
    </div>
  );
}
