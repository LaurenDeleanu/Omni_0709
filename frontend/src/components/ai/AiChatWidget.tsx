"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Bot, X, Sparkles, Send, Loader2, Terminal, ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, Settings, Mic, MicOff, Volume2, VolumeX, ScrollText, Copy, Check, Clock } from "lucide-react";
import { usePathname } from "@/i18n/routing";
import { API_BASE, getCsrfToken } from "@/lib/api/client";
import { CopilotAPI } from "@/lib/api/ai";
import { toast } from "sonner";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { useSSE } from "@/hooks/use-sse";

import { MessageBubble } from "./MessageBubble";
import { ChatModelSelector, MODEL_OPTIONS } from "./ChatModelSelector";
import { RunLogsModal } from "./RunLogsModal";
import { Message, TraceStep, ToolTraceStep, RunLog } from "./types";

function getModuleContextFromPath(pathname: string): string {
  const segments = pathname.split("/").filter(Boolean);
  const dashboardIdx = segments.findIndex((s) => s === "dashboard");
  if (dashboardIdx === -1) return "";
  const moduleSegment = segments[dashboardIdx + 1];
  if (!moduleSegment) return "";
  const mapping: Record<string, string> = {
    crm: "CRM",
    employees: "HR",
    it: "IT",
    finance: "Finance",
    training: "Training",
    sales: "Sales",
    admin: "Admin",
    schedules: "Schedules",
    kudos: "Kudos",
    hire: "Hire",
    pay: "Pay",
    legal: "Legal",
    work: "Work",
    ops: "Ops",
    reports: "Reports",
    workflows: "Workflows",
    settings: "Settings",
    calendar: "Calendar",
    grow: "Grow",
    imports: "Imports",
    monitoring: "Monitoring",
  };
  return mapping[moduleSegment] || moduleSegment.charAt(0).toUpperCase() + moduleSegment.slice(1);
}

const CONTEXT_OPTIONS = [
  "Auto (URL)", "CRM", "HR", "IT", "Finance", "Training", "Sales", "Admin",
  "Schedules", "Kudos", "Hire", "Pay", "Legal", "Work", "Ops", "Reports", "Workflows", "Calendar",
];

export function AiChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeMode, setActiveMode] = useState<"copilot" | "omni">("copilot");
  const [prompt, setPrompt] = useState("");
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({});
  const [sessionCost, setSessionCost] = useState(0);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [manualContext, setManualContext] = useState<string>("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState<Record<string, boolean>>({});
  const [logsModalMsg, setLogsModalMsg] = useState<Message | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const [isListening, setIsListening] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const synthRef = useRef<SpeechSynthesisUtterance | null>(null);

  const { isStreaming, text, start, stop } = useSSE();
  const [isOmniLoading, setIsOmniLoading] = useState(false);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hola! Soy tu Copiloto de Plataforma. Puedo ayudarte a interactuar con los modulos de SAS (RRHH, IT, Finanzas, Calendarios) respetando tus permisos de usuario. Que deseas hacer hoy?",
      mode: "copilot"
    }
  ]);

  const pathname = usePathname();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const modelSelectorRef = useRef<HTMLDivElement>(null);

  const moduleContext = manualContext || getModuleContextFromPath(pathname);

  const isLoading = isStreaming || isOmniLoading;

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("copilot_model");
      if (stored && MODEL_OPTIONS.some((m) => m.value === stored)) {
        setSelectedModel(stored);
      }
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelSelectorRef.current && !modelSelectorRef.current.contains(e.target as Node)) {
        setShowModelSelector(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [messages, isLoading, isOpen, text]);

  const handleSuggestionClick = (text: string) => {
    setPrompt(text);
  };

  const handleModelChange = (model: string) => {
    setSelectedModel(model);
    if (typeof window !== "undefined") {
      localStorage.setItem("copilot_model", model);
    }
    setShowModelSelector(false);
  };

  const handleFeedback = async (msgId: string, msgIndex: number, rating: "up" | "down") => {
    const msg = messages[msgIndex];
    if (!msg.feedbackMessageId) return;

    setFeedbackSubmitting((prev) => ({ ...prev, [msgId]: true }));
    try {
      await CopilotAPI.sendFeedback(msg.feedbackMessageId, rating);
      setMessages((prev) => {
        const updated = [...prev];
        updated[msgIndex] = {
          ...updated[msgIndex],
          feedback: updated[msgIndex].feedback === rating ? "none" : rating,
          showFeedbackInput: rating === "down" && updated[msgIndex].feedback !== "down",
        };
        return updated;
      });
    } catch {
      toast.error("Failed to submit feedback");
    } finally {
      setFeedbackSubmitting((prev) => ({ ...prev, [msgId]: false }));
    }
  };

  const handleFeedbackComment = (msgIndex: number, comment: string) => {
    setMessages((prev) => {
      const updated = [...prev];
      updated[msgIndex] = { ...updated[msgIndex], feedbackComment: comment };
      return updated;
    });
  };

  const submitFeedbackComment = async (msgId: string, msgIndex: number) => {
    const msg = messages[msgIndex];
    if (!msg.feedbackMessageId || msg.feedback !== "down") return;
    try {
      await CopilotAPI.sendFeedback(msg.feedbackMessageId, "down", msg.feedbackComment);
      setMessages((prev) => {
        const updated = [...prev];
        updated[msgIndex] = { ...updated[msgIndex], showFeedbackInput: false };
        return updated;
      });
      toast.success("Feedback sent");
    } catch {
      toast.error("Failed to send comment");
    }
  };

  const handleApprovalAction = async (msgId: string, msgIndex: number, action: "approve" | "reject") => {
    const msg = messages[msgIndex];
    if (!msg.approvalRequestId) return;
    try {
      const csrfToken = await getCsrfToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
      
      const body = action === "reject" ? JSON.stringify({ reason: "Rechazado por usuario en chat" }) : JSON.stringify({});
      
      const res = await fetch(`${API_BASE}/approvals/${msg.approvalRequestId}/${action}`, {
        method: "POST",
        headers,
        body,
        credentials: "include",
      });
      if (!res.ok) throw new Error("Approval action failed");
      
      setMessages(prev => {
        const next = [...prev];
        next[msgIndex] = { ...next[msgIndex], approvalStatus: action === "approve" ? "approved" : "rejected" };
        return next;
      });
      toast.success(action === "approve" ? "Acción aprobada y programada" : "Acción rechazada");
    } catch (err) {
      toast.error("No tienes permisos suficientes o la acción falló");
    }
  };

  const startListening = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast.error("Speech recognition not supported in this browser");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "es-ES";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      if (event.results[0].isFinal) {
        setPrompt((prev) => prev + transcript);
        setIsListening(false);
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  const speakMessage = useCallback((msgId: string, content: string) => {
    if (!window.speechSynthesis) {
      toast.error("Speech synthesis not supported in this browser");
      return;
    }

    if (speakingMsgId === msgId) {
      window.speechSynthesis.cancel();
      setSpeakingMsgId(null);
      return;
    }

    window.speechSynthesis.cancel();
    setSpeakingMsgId(msgId);

    const utterance = new SpeechSynthesisUtterance(content);
    utterance.lang = "es-ES";
    utterance.rate = 1.0;
    utterance.pitch = 1.1;

    utterance.onend = () => {
      setSpeakingMsgId(null);
    };

    utterance.onerror = () => {
      setSpeakingMsgId(null);
    };

    synthRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, [speakingMsgId]);

  const streamCopilotResponse = useCallback(async (message: string) => {
    const toolTraceSteps: ToolTraceStep[] = [];
    let runLogData: RunLog | undefined;
    let tokensUsed = 0;
    let costUsd = 0;
    let feedbackMessageId = "";
    let approvalRequestId = "";

    const ctx = moduleContext.toLowerCase();
    const csrfToken = await getCsrfToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;

    start("/ai/copilot/stream",
      { message, module_context: ctx, model_preference: selectedModel },
      {
        headers,
        onToken: () => {
        },
        onTrace: (event) => {
          if (event.tool_name && event.output === undefined) {
            toolTraceSteps.push({
              type: "tool_call",
              tool: event.tool_name as string,
              args: (event.arguments as Record<string, unknown>) || {},
              status: "running",
            });
          }

          if (event.tool_name && event.output !== undefined) {
            const running = toolTraceSteps.find(s => s.tool === event.tool_name && s.status === "running");
            if (running) {
              running.status = "completed";
              running.result = typeof event.output === "string" ? event.output as string : JSON.stringify(event.output);

              try {
                const outJson = typeof event.output === "string" ? JSON.parse(event.output as string) : event.output;
                if (outJson.status === "pending_approval" && outJson.approval_id) {
                  approvalRequestId = outJson.approval_id;
                }
              } catch {}
            }
          }

          if (event.tokens_used !== undefined) {
            tokensUsed = event.tokens_used as number;
            costUsd = (event.cost_usd as number) || 0;
            feedbackMessageId = (event.message_id as string) || "";
          }

          if (event.run_id) {
            runLogData = {
              runId: event.run_id as string,
              status: (event.status as string) || "unknown",
              latencyMs: (event.latency_ms as number) || 0,
              tokenUsage: (event.token_usage as number) || tokensUsed,
              costUsd: (event.cost_usd as number) || costUsd,
              model: event.model as string | undefined,
              toolTrace: toolTraceSteps.length > 0 ? toolTraceSteps : undefined,
            };
          }
        },
        onDone: (fullText) => {
          const assistantMessage: Message = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: fullText || "Completed successfully.",
            mode: "copilot",
            toolTrace: toolTraceSteps.length > 0 ? toolTraceSteps : undefined,
            tokensUsed,
            costUsd,
            feedbackMessageId,
            feedback: "none",
            showFeedbackInput: false,
            approvalRequestId: approvalRequestId || undefined,
            approvalStatus: approvalRequestId ? "pending" : undefined,
            runLog: runLogData,
          };
          if (costUsd) {
            setSessionCost(prev => prev + costUsd);
          }
          setMessages(prev => [...prev, assistantMessage]);
        },
        onError: (err) => {
          const errorMsg = err.message || "Unknown error";
          setMessages(prev => [...prev, {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: `Lo siento, ocurrio un error: ${errorMsg}`,
            mode: "copilot"
          }]);
          toast.error("Error processing with Copilot");
        },
      }
    );
  }, [moduleContext, selectedModel, start]);

  const callOmniMode = async (message: string) => {
    try {
      const csrfToken = await getCsrfToken();
      const csrfHeaders: Record<string, string> = { "Content-Type": "application/json" };
      if (csrfToken) csrfHeaders["X-CSRF-Token"] = csrfToken;
      const resp = await fetch(`${API_BASE}/omni/master`, {
        method: "POST",
        headers: csrfHeaders,
        body: JSON.stringify({ prompt: message }),
        credentials: "include",
      });
      const data = await resp.json();

      const reply = data.response || data.error || "No response";
      const omniRunLog: RunLog = {
        runId: data.run_id || "",
        status: data.success ? "completed" : "failed",
        latencyMs: data.latency_ms || 0,
        tokenUsage: data.token_usage || 0,
        costUsd: data.cost_usd || 0,
        trace: data.trace || [],
      };
      setMessages(prev => [...prev, {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: reply,
        mode: "omni",
        trace: data.trace || [],
        runLog: omniRunLog
      }]);
    } catch (error: any) {
      setMessages(prev => [...prev, {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: `Error: ${error.message || "Connection failed"}`,
        mode: "omni"
      }]);
    } finally {
      setIsOmniLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt || isLoading) return;

    const userMsgId = `user-${Date.now()}`;
    const userMessage: Message = {
      id: userMsgId,
      role: "user",
      content: cleanPrompt,
      mode: activeMode
    };
    setMessages(prev => [...prev, userMessage]);
    setPrompt("");

    if (activeMode === "copilot") {
      await streamCopilotResponse(cleanPrompt);
    } else {
      setIsOmniLoading(true);
      await callOmniMode(cleanPrompt);
    }
  };

  const toggleTrace = (msgId: string) => {
    setExpandedTraces(prev => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleCopyLog = (log: RunLog) => {
    const logText = [
      `Run ID: ${log.runId}`,
      `Status: ${log.status}`,
      `Latency: ${log.latencyMs}ms`,
      `Token Usage: ${log.tokenUsage}`,
      `Cost: $${log.costUsd.toFixed(6)}`,
      log.model ? `Model: ${log.model}` : null,
      log.trace ? `\nTraces (${log.trace.length}):\n${log.trace.map(s => `  Step ${s.step}: ${s.tool} - "${s.thought}"`).join('\n')}` : null,
      log.toolTrace ? `\nTool Calls (${log.toolTrace.length}):\n${log.toolTrace.map(s => `  ${s.status === 'completed' ? '✓' : '...'} ${s.tool} ${s.args ? JSON.stringify(s.args) : ''} ${s.result ? '→ ' + s.result : ''}`).join('\n')}` : null,
    ].filter(Boolean).join('\n');

    navigator.clipboard.writeText(logText).then(() => {
      setCopiedField(log.runId);
      setTimeout(() => setCopiedField(null), 2000);
    }).catch(() => {});
  };

  const suggestions = activeMode === "copilot"
    ? [
        "Solicita 5 dias de vacaciones para la proxima semana",
        "Crea una incidencia de IT de soporte para mi portatil",
        "Consulta mi saldo deudor acumulado de IA",
        "Busca empleados del departamento de RRHH"
      ]
    : [
        "Dime que routers de API estan registrados",
        "Genera un test unitario simple para vacacionales en backend/scratch",
        "Inspecciona que archivos contiene la carpeta backend/app/models"
      ];

  const filteredMessages = messages.filter(m => m.id === "welcome" || m.mode === activeMode);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 p-4 bg-gradient-to-r from-violet-600 via-indigo-600 to-fuchsia-600 hover:brightness-110 text-white rounded-full shadow-[0_0_20px_rgba(139,92,246,0.4)] transition-all duration-300 hover:scale-105 z-50 flex items-center justify-center group"
        title="Abrir Asistente AI"
      >
        <Sparkles size={24} className="group-hover:rotate-12 transition-transform" />
      </button>

      {isOpen && (
        <div className="fixed bottom-24 right-6 w-[430px] h-[550px] bg-slate-950/95 backdrop-blur-xl border border-violet-500/10 rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.6)] z-50 overflow-hidden flex flex-col animate-in slide-in-from-bottom-5 fade-in duration-300">
          <div className="bg-gradient-to-r from-slate-950 to-indigo-950 border-b border-violet-500/15 p-4 shrink-0 flex flex-col gap-3">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="text-xl">🌌</span>
                <div>
                  <h3 className="font-extrabold text-sm bg-gradient-to-r from-violet-400 via-indigo-300 to-fuchsia-400 bg-clip-text text-transparent">SuccessCore AI Assistant</h3>
                  <p className="text-[10px] text-zinc-500">Workspace & Platform Copilot</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                {sessionCost > 0 && (
                  <span className="text-[10px] text-zinc-500 bg-slate-900 border border-zinc-800 px-2 py-0.5 rounded-full">
                    Session: ${sessionCost.toFixed(2)}
                  </span>
                )}
                <ChatModelSelector
                  selectedModel={selectedModel}
                  handleModelChange={handleModelChange}
                />
                <button onClick={() => setIsOpen(false)} className="text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg transition-colors">
                  <X size={18} />
                </button>
              </div>
            </div>

            {activeMode === "copilot" && pathname && (
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-zinc-600 uppercase tracking-wider">Context:</span>
                <div className="relative">
                  <select
                    value={manualContext || ""}
                    onChange={(e) => setManualContext(e.target.value)}
                    className="appearance-none bg-slate-900 border border-zinc-800 rounded-md px-2 py-0.5 text-[10px] text-violet-400 font-semibold focus:outline-none focus:border-violet-500/50 cursor-pointer pr-5"
                  >
                    {CONTEXT_OPTIONS.map((opt) => (
                      <option key={opt} value={opt === "Auto (URL)" ? "" : opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={10} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                </div>
                {!manualContext && moduleContext && (
                  <span className="text-[9px] text-indigo-400/70 bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 rounded-full">
                    {moduleContext}
                  </span>
                )}
              </div>
            )}

            <div className="flex bg-slate-900 border border-zinc-800 rounded-xl p-1 gap-1">
              <button type="button" onClick={() => { setActiveMode("copilot"); if (messages.length === 1) { setMessages([{ id: "welcome", role: "assistant", content: "Hola! Soy tu Copiloto de Plataforma.", mode: "copilot" }]); } }}
                className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${activeMode === "copilot" ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow" : "text-zinc-500 hover:text-zinc-300"}`}
              ><Sparkles size={13} />Copiloto</button>
              <button type="button" onClick={() => { setActiveMode("omni"); if (!messages.some(m => m.mode === "omni")) { setMessages(prev => [...prev, { id: `welcome-omni-${Date.now()}`, role: "assistant", content: "Modo Omni Controller activado. Tengo privilegios para leer y modificar el codebase.", mode: "omni" }]); } }}
                className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${activeMode === "omni" ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow" : "text-zinc-500 hover:text-zinc-300"}`}
              ><Terminal size={13} />Omni</button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-slate-950/30">
            {filteredMessages.map((msg, msgIndex) => {
              const isAssistant = msg.role === "assistant";
              return (
                <MessageBubble
                  key={msg.id}
                  msg={msg}
                  msgIndex={msgIndex}
                  expandedTraces={expandedTraces}
                  speakingMsgId={speakingMsgId}
                  feedbackSubmitting={feedbackSubmitting}
                  speakMessage={speakMessage}
                  handleApprovalAction={handleApprovalAction}
                  toggleTrace={toggleTrace}
                  handleFeedback={handleFeedback}
                  setLogsModalMsg={setLogsModalMsg}
                  handleFeedbackComment={handleFeedbackComment}
                  submitFeedbackComment={submitFeedbackComment}
                />
              );
            })}

            {isStreaming && text && (
              <div className="flex justify-start animate-fade-in">
                <div className="flex gap-2 max-w-[85%]">
                  <div className="w-7 h-7 rounded-full bg-indigo-950 border border-violet-500/20 flex items-center justify-center text-xs shrink-0">🤖</div>
                  <div className="p-3.5 rounded-2xl text-xs leading-relaxed bg-slate-900 border border-zinc-800 text-zinc-200 rounded-tl-none">
                    <MarkdownRenderer content={text} />
                    <span className="animate-pulse ml-0.5 text-violet-400">▌</span>
                  </div>
                </div>
              </div>
            )}

            {isLoading && !text && (
              <div className="flex justify-start animate-pulse">
                <div className="flex gap-2 max-w-[85%]">
                  <div className="w-7 h-7 rounded-full bg-indigo-950 border border-violet-500/20 flex items-center justify-center text-xs shrink-0 self-start shadow-inner">
                    <Loader2 size={13} className="animate-spin text-violet-400" />
                  </div>
                  <div className="p-3.5 rounded-2xl text-xs leading-normal bg-slate-900 border border-zinc-800 text-zinc-400 rounded-tl-none flex flex-col gap-2">
                    <span className="font-bold text-violet-400 text-[10px] uppercase tracking-widest animate-pulse flex items-center gap-1.5">
                      <Loader2 size={10} className="animate-spin" />
                      {activeMode === "copilot" ? "Processing..." : "Executing codebase loop..."}
                    </span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {!isLoading && (
            <div className="px-4 py-2 flex flex-wrap gap-1.5 bg-slate-950 border-t border-zinc-900 shrink-0">
              {suggestions.map((sug, idx) => (
                <button key={idx} type="button" onClick={() => handleSuggestionClick(sug)} className="text-[9px] text-zinc-400 hover:text-white bg-slate-900/60 border border-zinc-800 hover:border-violet-500/25 px-2.5 py-1.5 rounded-full transition-all text-left truncate max-w-full">{sug}</button>
              ))}
            </div>
          )}

          <form onSubmit={handleSendMessage} className="p-4 border-t border-violet-500/10 bg-slate-950 shrink-0 flex gap-2">
            <button
              type="button"
              disabled={isLoading}
              onClick={isListening ? stopListening : startListening}
              className={`p-2.5 rounded-xl transition-all flex items-center justify-center cursor-pointer ${
                isListening
                  ? "bg-red-600 animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.5)] text-white"
                  : "bg-slate-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-violet-500/30"
              }`}
              title={isListening ? "Stop recording" : "Start voice input"}
            >
              {isListening ? <MicOff size={14} /> : <Mic size={14} />}
            </button>
            <input type="text" disabled={isLoading} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder={activeMode === "copilot" ? "Ej: Busca empleados de RRHH..." : "Ej: Busca la ruta del router de vacaciones..."}
              className="flex-1 bg-slate-900 border border-zinc-800 focus:border-violet-500/50 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none transition-colors disabled:opacity-50" />
            {isStreaming ? (
              <button
                type="button"
                onClick={stop}
                className="bg-red-600 hover:bg-red-700 text-white p-2.5 rounded-xl transition-all flex items-center justify-center shadow-md cursor-pointer"
                title="Stop streaming"
              >
                <X size={14} />
              </button>
            ) : (
              <button type="submit" disabled={isOmniLoading || !prompt.trim()} className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 disabled:opacity-50 disabled:from-zinc-800 disabled:to-zinc-800 text-white p-2.5 rounded-xl transition-all flex items-center justify-center shadow-md shadow-violet-500/10 cursor-pointer">
                {isOmniLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              </button>
            )}
          </form>
        </div>
      )}

      {logsModalMsg && logsModalMsg.runLog && (
        <RunLogsModal
          msg={logsModalMsg}
          onClose={() => setLogsModalMsg(null)}
          onCopy={handleCopyLog}
          copiedField={copiedField}
        />
      )}
    </>
  );
}