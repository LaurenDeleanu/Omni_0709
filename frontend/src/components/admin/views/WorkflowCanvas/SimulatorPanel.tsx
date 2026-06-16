"use client";
import React, { useState, useEffect, useRef } from "react";
import { X, Send, AlertCircle, RefreshCw } from "lucide-react";

export default function SimulatorPanel({
  workflowId,
  onClose
}: {
  workflowId: string;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<{ sender: "user" | "bot" | "system", text: string, options?: string[] }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initial welcome message prompt
    setMessages([
      { sender: "system", text: "¡Simulador activado! Escribe cualquier mensaje para simular y probar tu flujo conversacional interactivo." }
    ]);
  }, [workflowId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent, customText?: string) => {
    if (e) e.preventDefault();
    const textToSend = customText || input;
    if (!textToSend.trim()) return;

    if (!customText) {
      setInput("");
    }

    setMessages(prev => [...prev, { sender: "user", text: textToSend }]);
    setLoading(true);

    try {
      const res = await fetch(`/api/chat/${workflowId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId: "simulator_" + workflowId,
          message: textToSend
        })
      });

      const data = await res.json();
      setLoading(false);

      if (data.reply) {
        setMessages(prev => [...prev, {
          sender: "bot",
          text: data.reply,
          options: data.options
        }]);
      } else if (data.error) {
        setMessages(prev => [...prev, {
          sender: "system",
          text: `[Error] ${data.error}`
        }]);
      }
    } catch (err) {
      setLoading(false);
      setMessages(prev => [...prev, {
        sender: "system",
        text: "[Error] No se pudo establecer conexión con el motor de chat."
      }]);
    }
  };

  const handleResetSession = async () => {
    try {
      setLoading(true);
      await fetch(`/api/chat/${workflowId}?sessionId=simulator_${workflowId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
      });
      setMessages([
        { sender: "system", text: "Sesión reiniciada. Envía un nuevo mensaje para iniciar la conversación de prueba." }
      ]);
    } catch (err) {
      console.error("Failed to reset simulator session:", err);
      setMessages(prev => [...prev, {
        sender: "system",
        text: "[Error] No se pudo reiniciar la sesión en el servidor."
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-80 h-[500px] bg-zinc-950 border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-slide-up">
      {/* Header bar */}
      <div className="p-4 bg-zinc-900 border-b border-white/5 flex justify-between items-center select-none">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
          <span className="text-xs font-bold text-white uppercase tracking-wider">Simulador de Chat</span>
        </div>
        <div className="flex items-center gap-2">
          <button 
            type="button" 
            onClick={handleResetSession}
            title="Reiniciar Simulación"
            className="text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button 
            type="button" 
            onClick={onClose}
            className="text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3 custom-scrollbar bg-black/40 flex flex-col">
        {messages.map((m, idx) => {
          if (m.sender === "system") {
            return (
              <div key={idx} className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[10px] p-2.5 rounded-xl flex items-start gap-1.5 leading-normal">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{m.text}</span>
              </div>
            );
          }

          const isUser = m.sender === "user";

          return (
            <div key={idx} className={`flex flex-col gap-1.5 max-w-[85%] ${isUser ? "self-end" : "self-start"}`}>
              <div className={`text-xs p-3 rounded-2xl shadow-md leading-normal ${
                isUser 
                  ? "bg-indigo-600 text-white rounded-tr-none" 
                  : "bg-zinc-800 text-zinc-200 rounded-tl-none border border-white/5"
              }`}>
                {m.text}
              </div>
              {/* Option quick-reply buttons */}
              {!isUser && m.options && m.options.length > 0 && (
                <div className="flex flex-col gap-1 mt-1">
                  {m.options.map((opt, oIdx) => (
                    <button 
                      key={oIdx}
                      type="button"
                      onClick={(e) => handleSend(e, opt)}
                      className="text-[10px] bg-zinc-900 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/20 hover:border-indigo-500 px-3 py-1.5 rounded-xl font-medium transition-all text-left truncate"
                    >
                      🔘 {opt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {loading && (
          <div className="bg-zinc-900/50 text-zinc-400 text-xs p-2.5 rounded-2xl rounded-tl-none self-start flex items-center gap-1 animate-pulse border border-white/5">
            <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
            <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
            <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-3 bg-zinc-900 border-t border-white/5 flex gap-2">
        <input 
          type="text" 
          placeholder="Escribe tu mensaje de prueba..." 
          value={input}
          onChange={e => setInput(e.target.value)}
          className="flex-1 bg-black/50 border border-white/10 rounded-xl py-1.5 px-3 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
        />
        <button 
          type="submit" 
          className="p-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-colors text-white hover:scale-105 active:scale-95"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}
