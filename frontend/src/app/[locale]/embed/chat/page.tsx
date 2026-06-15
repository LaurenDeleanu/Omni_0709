"use client";

import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Send, Loader2, Sparkles } from "lucide-react";
import { MarkdownRenderer } from "@/components/ai/MarkdownRenderer";
import { API_BASE } from "@/lib/api/client";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function EmbedChatPage() {
  const searchParams = useSearchParams();
  const tenant = searchParams.get("tenant") || "default";
  const theme = searchParams.get("theme") || "dark";

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: `Hi! I'm the SuccessCore AI assistant. How can I help you today?`,
    },
  ]);
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const isDark = theme === "dark";

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = prompt.trim();
    if (!clean || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: clean,
    };
    setMessages((prev) => [...prev, userMsg]);
    setPrompt("");
    setIsLoading(true);
    setStreamingText("");

    try {
      const resp = await fetch(`${API_BASE}/ai/copilot/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: clean, module_context: "embed" }),
        credentials: "include",
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let fullResponse = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw.startsWith("event:")) continue;
          try {
            const data = JSON.parse(raw);
            if (data.text) {
              fullResponse += data.text;
              setStreamingText(fullResponse);
            }
          } catch { }
        }
      }

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: fullResponse || "I received your message.",
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `Sorry, an error occurred: ${err.message || "Unknown error"}`,
        },
      ]);
    } finally {
      setIsLoading(false);
      setStreamingText("");
    }
  };

  const handleClose = () => {
    window.parent.postMessage({ type: "successcore-close" }, "*");
  };

  return (
    <div
      className={`flex flex-col h-full w-full ${isDark ? "bg-slate-950 text-zinc-200" : "bg-white text-gray-900"}`}
      style={{
        fontFamily: "Inter, system-ui, -apple-system, sans-serif",
        fontSize: "13px",
      }}
    >
      <div
        className={`flex items-center justify-between px-4 py-3 shrink-0 border-b ${isDark ? "bg-gradient-to-r from-slate-950 to-indigo-950 border-violet-500/15" : "bg-gray-50 border-gray-200"
          }`}
      >
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-violet-400" />
          <span className={`font-bold text-sm ${isDark ? "bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent" : "text-violet-700"}`}>
            SuccessCore AI
          </span>
        </div>
        <button
          onClick={handleClose}
          className={`p-1.5 rounded-lg transition-colors ${isDark ? "text-zinc-500 hover:text-white hover:bg-white/10" : "text-gray-500 hover:text-gray-700 hover:bg-gray-200"}`}
          title="Close"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "assistant" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-xs leading-relaxed ${msg.role === "assistant"
                  ? isDark
                    ? "bg-slate-900 border border-zinc-800 text-zinc-200 rounded-tl-none"
                    : "bg-gray-100 border border-gray-200 text-gray-800 rounded-tl-none"
                  : isDark
                    ? "bg-gradient-to-r from-violet-950/70 to-indigo-950/70 border border-violet-500/30 text-white rounded-tr-none"
                    : "bg-violet-600 text-white rounded-tr-none"
                }`}
            >
              <MarkdownRenderer content={msg.content} />
            </div>
          </div>
        ))}

        {streamingText && (
          <div className="flex justify-start">
            <div
              className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-xs leading-relaxed rounded-tl-none ${isDark ? "bg-slate-900 border border-zinc-800 text-zinc-200" : "bg-gray-100 border border-gray-200 text-gray-800"
                }`}
            >
              <MarkdownRenderer content={streamingText} />
              <span className="animate-pulse ml-0.5 text-violet-400">|</span>
            </div>
          </div>
        )}

        {isLoading && !streamingText && (
          <div className="flex justify-start">
            <div
              className={`px-4 py-3 rounded-2xl text-xs rounded-tl-none ${isDark ? "bg-slate-900 border border-zinc-800 text-zinc-400" : "bg-gray-100 border border-gray-200 text-gray-500"
                }`}
            >
              <Loader2 size={12} className="animate-spin inline mr-1.5 text-violet-400" />
              Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={handleSend}
        className={`p-3 border-t shrink-0 flex gap-2 ${isDark ? "border-violet-500/10 bg-slate-950" : "border-gray-200 bg-gray-50"}`}
      >
        <input
          ref={inputRef}
          type="text"
          disabled={isLoading}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Type your message..."
          className={`flex-1 rounded-xl px-3 py-2 text-xs focus:outline-none transition-colors disabled:opacity-50 ${isDark
              ? "bg-slate-900 border border-zinc-800 focus:border-violet-500/50 text-white placeholder-zinc-600"
              : "bg-white border border-gray-300 focus:border-violet-500 text-gray-900 placeholder-gray-400"
            }`}
        />
        <button
          type="submit"
          disabled={isLoading || !prompt.trim()}
          className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 disabled:opacity-50 disabled:from-zinc-700 disabled:to-zinc-700 text-white p-2.5 rounded-xl transition-all flex items-center justify-center shadow-md"
        >
          {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
        </button>
      </form>
    </div>
  );
}
