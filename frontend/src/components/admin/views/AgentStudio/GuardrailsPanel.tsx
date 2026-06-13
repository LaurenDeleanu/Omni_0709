"use client";

import React from "react";
import { ShieldAlert, AlertOctagon, Lock, EyeOff, UserX } from "lucide-react";

interface GuardrailsPanelProps {
  aiGuardrails: string;
  onGuardrailsChange: (val: string) => void;
  settings: any;
  onSettingsChange: (settings: any) => void;
}

export default function GuardrailsPanel({
  aiGuardrails,
  onGuardrailsChange,
  settings = {},
  onSettingsChange,
}: GuardrailsPanelProps) {
  
  const handleToggleSetting = (key: string) => {
    onSettingsChange({
      ...settings,
      [key]: !settings[key],
    });
  };

  return (
    <div className="space-y-6">
      {/* Strict limits description */}
      <div className="p-5 rounded-2xl border border-red-500/20 bg-red-950/5 flex items-start gap-4">
        <div className="p-2 rounded-xl bg-red-500/10 text-red-400 mt-0.5">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-red-400">Strict Behavioral Guardrails</h3>
          <p className="text-xs text-red-200/60 leading-relaxed font-light mt-1">
            Rules typed here override LLM decision chains. If the model generates a reply violating these limits, the output checker intercepts, discards it, and triggers a safety fallback.
          </p>
        </div>
      </div>

      {/* Guardrail Rules editor */}
      <div className="space-y-2">
        <label className="label text-xs uppercase tracking-wider text-zinc-400 font-bold block mb-1">
          Guardrail Directives (Override Instructions)
        </label>
        <textarea
          className="input border-red-500/20 focus:border-red-500/50 bg-zinc-950/60 font-mono text-xs leading-relaxed"
          rows={6}
          placeholder="E.g. NUNCA menciones a competidores (Competidor X, Competidor Y). NUNCA ofrezcas reembolsos de forma directa sin supervisor. NUNCA respondas preguntas de política o religión."
          value={aiGuardrails}
          onChange={(e) => onGuardrailsChange(e.target.value)}
        />
        <span className="text-[10px] text-zinc-500">List instructions clearly using bullet points or CAPITAL keywords for best accuracy.</span>
      </div>

      {/* Strict Compliance controls */}
      <div className="border-t border-white/5 pt-5 space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-2">Automated Policy Interceptors</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            onClick={() => handleToggleSetting("piiRedaction")}
            className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer flex gap-3 items-start ${
              settings.piiRedaction
                ? "border-red-500/30 bg-red-500/5"
                : "border-white/5 bg-zinc-950/20 hover:border-white/10"
            }`}
          >
            <UserX className={`w-5 h-5 mt-0.5 ${settings.piiRedaction ? "text-red-400" : "text-zinc-500"}`} />
            <div>
              <span className="text-xs font-bold text-white block">PII Redaction</span>
              <span className="text-[10px] text-zinc-400 font-light leading-normal block mt-1">
                Mask client credit cards, emails, and phone numbers in vectors and logs.
              </span>
            </div>
          </div>

          <div
            onClick={() => handleToggleSetting("strictModeration")}
            className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer flex gap-3 items-start ${
              settings.strictModeration
                ? "border-red-500/30 bg-red-500/5"
                : "border-white/5 bg-zinc-950/20 hover:border-white/10"
            }`}
          >
            <AlertOctagon className={`w-5 h-5 mt-0.5 ${settings.strictModeration ? "text-red-400" : "text-zinc-500"}`} />
            <div>
              <span className="text-xs font-bold text-white block">Strict Content Filtering</span>
              <span className="text-[10px] text-zinc-400 font-light leading-normal block mt-1">
                Instantly drop prompts containing profanity, racism, or threat flags.
              </span>
            </div>
          </div>

          <div
            onClick={() => handleToggleSetting("hallucinationGuard")}
            className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer flex gap-3 items-start ${
              settings.hallucinationGuard
                ? "border-red-500/30 bg-red-500/5"
                : "border-white/5 bg-zinc-950/20 hover:border-white/10"
            }`}
          >
            <EyeOff className={`w-5 h-5 mt-0.5 ${settings.hallucinationGuard ? "text-red-400" : "text-zinc-500"}`} />
            <div>
              <span className="text-xs font-bold text-white block">Anti-Hallucination Anchor</span>
              <span className="text-[10px] text-zinc-400 font-light leading-normal block mt-1">
                Require the model to cite specific vector chunks or static core contextual keys before replying.
              </span>
            </div>
          </div>

          <div
            onClick={() => handleToggleSetting("competitorShield")}
            className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer flex gap-3 items-start ${
              settings.competitorShield
                ? "border-red-500/30 bg-red-500/5"
                : "border-white/5 bg-zinc-950/20 hover:border-white/10"
            }`}
          >
            <Lock className={`w-5 h-5 mt-0.5 ${settings.competitorShield ? "text-red-400" : "text-zinc-500"}`} />
            <div>
              <span className="text-xs font-bold text-white block">Competitor Blocker</span>
              <span className="text-[10px] text-zinc-400 font-light leading-normal block mt-1">
                Refuse to compare pricing, capabilities, or details with competitors.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
