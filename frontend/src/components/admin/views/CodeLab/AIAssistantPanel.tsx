import React, { useState } from "react";
import { FileItem } from "@/lib/git/types";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface AIAssistantPanelProps {
  botId: string;
  activeFile: FileItem | null;
  allFiles: FileItem[];
  onApplyGeneratedCode: (code: string) => void;
}

export default function AIAssistantPanel({
  botId,
  activeFile,
  allFiles,
  onApplyGeneratedCode,
}: AIAssistantPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "¡Hola! Soy tu asistente de Laboratorio de Código. Describe qué quieres cambiar o qué módulo deseas generar, y yo actualizaré el editor." }
  ]);
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !activeFile || isGenerating) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsGenerating(true);

    try {
      const res = await fetch("/api/git/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: userMsg,
          activeFile,
          allFiles,
          botId
        })
      });

      const data = await res.json();
      if (res.ok && data.code) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `He generado los cambios solicitados para \`${activeFile.path}\`. Haz clic en "Aplicar código" para cargarlo en el editor.` }
        ]);
        // Store temporary code generation to apply
        setPendingCode(data.code);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `⚠️ Error al generar código: ${data.error || "Error desconocido"}` }
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Ocurrió un error de red al contactar al asistente." }
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  const [pendingCode, setPendingCode] = useState<string | null>(null);

  const handleApply = () => {
    if (pendingCode) {
      onApplyGeneratedCode(pendingCode);
      setPendingCode(null);
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-lg p-4 text-zinc-300">
      <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3">AI Asistente de Código</h3>
      
      <div className="flex-1 overflow-y-auto space-y-3.5 mb-4 pr-1 min-h-0">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex flex-col rounded-lg p-3 text-xs leading-relaxed max-w-[85%] ${
              msg.role === "user"
                ? "bg-indigo-600/10 border border-indigo-500/20 text-zinc-100 ml-auto"
                : "bg-zinc-900 border border-zinc-800 text-zinc-300 mr-auto"
            }`}
          >
            <div className="font-bold text-[9px] uppercase tracking-wider text-zinc-500 mb-1">
              {msg.role === "user" ? "Tú" : "NexusForge AI"}
            </div>
            <div className="whitespace-pre-line">{msg.content}</div>
          </div>
        ))}

        {isGenerating && (
          <div className="flex items-center gap-2 text-xs text-zinc-500 animate-pulse bg-zinc-900 border border-zinc-800 rounded-lg p-3 max-w-[85%]">
            <span className="animate-spin text-zinc-400">⏳</span> Generando código en tiempo real...
          </div>
        )}
      </div>

      {pendingCode && (
        <button
          onClick={handleApply}
          className="mb-3 w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded text-xs transition-colors flex justify-center items-center gap-1.5 shadow-lg shadow-emerald-950/20"
        >
          ✨ Aplicar código al Editor
        </button>
      )}

      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          placeholder={activeFile ? "ej: optimiza este script, agrega un try-catch" : "Selecciona un archivo para chatear"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!activeFile || isGenerating}
          className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-zinc-700 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!activeFile || isGenerating || !input.trim()}
          className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-600 rounded-lg text-xs font-semibold transition-colors"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
