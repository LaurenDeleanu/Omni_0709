import React from "react";
import { Volume2, VolumeX, ChevronDown, ChevronUp, Loader2, ThumbsUp, ThumbsDown, ScrollText } from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { Message } from "./types";

interface MessageBubbleProps {
  msg: Message;
  msgIndex: number;
  expandedTraces: Record<string, boolean>;
  speakingMsgId: string | null;
  feedbackSubmitting: Record<string, boolean>;
  speakMessage: (id: string, content: string) => void;
  handleApprovalAction: (id: string, index: number, action: "approve" | "reject") => void;
  toggleTrace: (id: string) => void;
  handleFeedback: (id: string, index: number, type: "up" | "down") => void;
  setLogsModalMsg: (msg: Message) => void;
  handleFeedbackComment: (index: number, val: string) => void;
  submitFeedbackComment: (id: string, index: number) => void;
}

export function MessageBubble({
  msg,
  msgIndex,
  expandedTraces,
  speakingMsgId,
  feedbackSubmitting,
  speakMessage,
  handleApprovalAction,
  toggleTrace,
  handleFeedback,
  setLogsModalMsg,
  handleFeedbackComment,
  submitFeedbackComment,
}: MessageBubbleProps) {
  const isAssistant = msg.role === "assistant";

  return (
    <div className={`flex ${isAssistant ? "justify-start" : "justify-end"} animate-fade-in`}>
      <div className="flex gap-2 max-w-[85%]">
        {isAssistant && (
          <div className="w-7 h-7 rounded-full bg-indigo-950 border border-violet-500/20 flex items-center justify-center text-xs shrink-0 self-start shadow-inner">
            {msg.mode === "copilot" ? "🤖" : "🌌"}
          </div>
        )}
        <div className={`p-3.5 rounded-2xl text-xs leading-relaxed border ${isAssistant ? "bg-slate-900 border-zinc-800 text-zinc-200 rounded-tl-none" : "bg-gradient-to-r from-violet-950/70 to-indigo-950/70 border-violet-500/30 text-white rounded-tr-none"}`}>
          <MarkdownRenderer content={msg.content} />

          {isAssistant && msg.id !== "welcome" && !msg.id.startsWith("welcome-omni") && (
            <button
              type="button"
              onClick={() => speakMessage(msg.id, msg.content)}
              className={`mt-1.5 p-1 rounded transition-all ${
                speakingMsgId === msg.id
                  ? "text-violet-400 bg-violet-500/10"
                  : "text-zinc-600 hover:text-zinc-400 hover:bg-white/5"
              }`}
              title={speakingMsgId === msg.id ? "Stop speaking" : "Read aloud"}
            >
              {speakingMsgId === msg.id ? <VolumeX size={13} /> : <Volume2 size={13} />}
            </button>
          )}

          {msg.approvalRequestId && (
            <div className="mt-3.5 border-t border-zinc-800 pt-2.5">
              <div className="text-[10px] text-amber-400 font-bold uppercase tracking-wider mb-2">
                ⚠️ Acción Destructiva Requiere Aprobación
              </div>
              {msg.approvalStatus === "pending" || !msg.approvalStatus ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleApprovalAction(msg.id, msgIndex, "approve")}
                    className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30 rounded text-xs font-semibold transition-colors shadow-sm"
                  >
                    Aprobar
                  </button>
                  <button
                    type="button"
                    onClick={() => handleApprovalAction(msg.id, msgIndex, "reject")}
                    className="px-3 py-1.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30 rounded text-xs font-semibold transition-colors shadow-sm"
                  >
                    Rechazar
                  </button>
                </div>
              ) : (
                <div className={`text-xs font-semibold flex items-center gap-1 ${msg.approvalStatus === "approved" ? "text-emerald-400" : "text-red-400"}`}>
                  {msg.approvalStatus === "approved" ? "✅ Aprobada" : "❌ Rechazada"}
                </div>
              )}
            </div>
          )}

          {msg.toolTrace && msg.toolTrace.length > 0 && (
            <div className="mt-3.5 border-t border-zinc-800 pt-2.5">
              <button type="button" onClick={() => toggleTrace(msg.id)} className="flex items-center justify-between w-full text-[10px] text-violet-400 hover:text-violet-300 font-bold uppercase tracking-wider">
                <span>Tool Traces ({msg.toolTrace.length} steps)</span>
                {expandedTraces[msg.id] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {expandedTraces[msg.id] && (
                <div className="space-y-2 mt-2">
                  {msg.toolTrace.map((step, sIdx) => (
                    <div key={sIdx} className="bg-slate-950/50 border border-zinc-800 rounded-lg p-2.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${step.status === "completed" ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]" : "bg-amber-400 animate-pulse shadow-[0_0_6px_rgba(251,191,36,0.5)]"}`} />
                        <span className="text-xs font-semibold text-indigo-400">Used tool: {step.tool}</span>
                        <span className={`text-[10px] font-bold ${step.status === "completed" ? "text-emerald-400" : "text-amber-400"}`}>
                          {step.status === "completed" ? "✓" : <Loader2 size={10} className="animate-spin inline" />}
                        </span>
                      </div>
                      {step.args && Object.keys(step.args).length > 0 && (
                        <div className="mt-1.5 text-[10px] text-zinc-500">
                          <span className="text-zinc-600 text-[9px] uppercase tracking-wider">Arguments: </span>
                          <code className="text-zinc-400 font-mono">{JSON.stringify(step.args)}</code>
                        </div>
                      )}
                      {step.result && (
                        <div className="mt-1.5 text-[10px] text-zinc-500">
                          <span className="text-zinc-600 text-[9px] uppercase tracking-wider">Result: </span>
                          <code className="text-zinc-400 font-mono break-all">{step.result}</code>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {msg.trace && msg.trace.length > 0 && (
            <div className="mt-3.5 border-t border-zinc-800 pt-2.5">
              <button type="button" onClick={() => toggleTrace(msg.id)} className="flex items-center justify-between w-full text-[10px] text-violet-400 hover:text-violet-300 font-bold uppercase tracking-wider">
                <span>Trazas ({msg.trace.length} steps)</span>
                {expandedTraces[msg.id] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {expandedTraces[msg.id] && (
                <div className="relative border-l border-zinc-800 ml-1.5 pl-3.5 mt-2 space-y-3">
                  {msg.trace.map((step, sIdx) => (
                    <div key={sIdx} className="relative text-[10px] leading-normal text-zinc-400">
                      <div className="absolute -left-[18.5px] top-1 w-1.5 h-1.5 rounded-full border border-violet-500 bg-zinc-950 shadow-[0_0_4px_rgba(139,92,246,0.6)]" />
                      <div className="font-semibold text-zinc-300 uppercase tracking-widest text-[9px] mb-0.5">Step {step.step}: {step.tool}</div>
                      <p className="text-zinc-500 italic bg-black/30 p-1.5 rounded border border-zinc-900 leading-normal">"{step.thought}"</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {isAssistant && msg.id !== "welcome" && !msg.id.startsWith("welcome-omni") && (
            <>
              <div className="mt-3 flex items-center gap-2 border-t border-zinc-800 pt-2.5">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={feedbackSubmitting[msg.id]}
                    onClick={() => handleFeedback(msg.id, msgIndex, "up")}
                    className={`p-1 rounded transition-all ${
                      msg.feedback === "up"
                        ? "text-emerald-400 bg-emerald-500/10"
                        : "text-zinc-600 hover:text-zinc-400 hover:bg-white/5"
                    }`}
                  >
                    <ThumbsUp size={12} />
                  </button>
                  <button
                    type="button"
                    disabled={feedbackSubmitting[msg.id]}
                    onClick={() => handleFeedback(msg.id, msgIndex, "down")}
                    className={`p-1 rounded transition-all ${
                      msg.feedback === "down"
                        ? "text-red-400 bg-red-500/10"
                        : "text-zinc-600 hover:text-zinc-400 hover:bg-white/5"
                    }`}
                  >
                    <ThumbsDown size={12} />
                  </button>
                </div>
                {msg.runLog && (
                  <button
                    type="button"
                    onClick={() => setLogsModalMsg(msg)}
                    className="p-1 rounded text-zinc-600 hover:text-cyan-400 hover:bg-cyan-500/10 transition-all flex items-center gap-1"
                    title="Ver logs de ejecucion"
                  >
                    <ScrollText size={12} />
                    <span className="text-[9px] uppercase tracking-wider hidden group-hover:inline">Logs</span>
                  </button>
                )}
                {msg.costUsd !== undefined && msg.costUsd > 0 && (
                  <span className="text-[9px] text-zinc-600 ml-auto">~${msg.costUsd.toFixed(4)}</span>
                )}
              </div>
              {msg.showFeedbackInput && msg.feedback === "down" && (
                <div className="mt-2 flex gap-1.5">
                  <input
                    type="text"
                    placeholder="What went wrong?"
                    value={msg.feedbackComment || ""}
                    onChange={(e) => handleFeedbackComment(msgIndex, e.target.value)}
                    className="flex-1 bg-slate-800 border border-zinc-700 rounded-md px-2 py-1 text-[10px] text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-violet-500/50"
                  />
                  <button
                    type="button"
                    onClick={() => submitFeedbackComment(msg.id, msgIndex)}
                    className="text-[10px] text-violet-400 hover:text-violet-300 bg-slate-800 border border-zinc-700 rounded-md px-2 py-1 font-semibold"
                  >
                    Send
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
