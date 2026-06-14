"use client";

import { useState, useRef, useEffect } from "react";
import { Bot, X, Send, Loader2 } from "lucide-react";
import { useSSE } from "@/hooks/use-sse";
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
  const [messages, setMessages] = useState<InlineMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { isStreaming, text, error, start, stop } = useSSE();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, text]);

  useEffect(() => {
    if (!isStreaming && text && text.length > 0) {
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: text }]);
    }
  }, [isStreaming]);

  const handleQuickAction = (msg: string) => {
    setPrompt(msg);
    if (!expanded) setExpanded(true);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = prompt.trim();
    if (!clean || isStreaming) return;

    const userMsg: InlineMessage = { id: `u-${Date.now()}`, role: "user", content: clean };
    setMessages((prev) => [...prev, userMsg]);
    setPrompt("");
    setExpanded(true);

    const modelPreference = typeof window !== "undefined"
      ? localStorage.getItem("copilot_model") || "gpt-4o-mini"
      : "gpt-4o-mini";

    start("/ai/copilot/stream", {
      message: clean,
      module_context: moduleContext.toLowerCase(),
      model_preference: modelPreference,
    }, {
      onError: (err) => {
        setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", content: `Error: ${err.message}` }]);
      },
    });
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
              className="text-xs px-2.5 py-1 rounded-full bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              {qa.label}
            </button>
          ))}
        </div>
      )}

      {expanded && (
        <div className="max-h-64 overflow-y-auto px-4 pt-3 space-y-3">
          {messages.map((m) => (
            <div key={m.id} className={`flex gap-2 ${m.role === "user" ? "justify-end" : ""}`}>
              {m.role === "assistant" && (
                <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                </div>
              )}
              <div className={`text-xs leading-relaxed rounded-xl px-3 py-2 max-w-[85%] ${
                m.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/50 text-foreground"
              }`}>
                <MarkdownRenderer content={m.content} />
              </div>
              {m.role === "user" && (
                <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[10px] text-muted-foreground font-bold">U</span>
                </div>
              )}
            </div>
          ))}
          {isStreaming && text && (
            <div className="flex gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
              <div className="text-xs leading-relaxed rounded-xl px-3 py-2 max-w-[85%] bg-muted/50 text-foreground">
                <MarkdownRenderer content={text} />
              </div>
            </div>
          )}
          {isStreaming && !text && (
            <div className="flex gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-primary animate-pulse" />
              </div>
              <div className="text-xs rounded-xl px-3 py-2 bg-muted/50 text-muted-foreground">
                Thinking...
              </div>
            </div>
          )}
          {error && (
            <div className="text-xs text-destructive px-3 py-1">{error}</div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      <form onSubmit={handleSend} className="flex items-center gap-2 p-3">
        {isStreaming ? (
          <button
            type="button"
            onClick={stop}
            className="p-1.5 rounded-lg bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        ) : (
          <div className="p-1.5">
            <Bot className="w-4 h-4 text-muted-foreground" />
          </div>
        )}
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={placeholder || `Ask about ${moduleContext}...`}
          className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none"
          onFocus={() => setExpanded(true)}
        />
        <button
          type="submit"
          disabled={!prompt.trim() || isStreaming}
          className="p-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-30 transition-colors"
        >
          {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </form>
    </div>
  );
}
