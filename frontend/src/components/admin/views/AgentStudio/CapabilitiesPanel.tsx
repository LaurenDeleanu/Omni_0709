"use client";

import React from "react";
import { Globe, Heart, CheckCircle2, ShieldCheck, FileText } from "lucide-react";

interface CapabilitiesPanelProps {
  settings: Record<string, any>;
  onChange: (settings: Record<string, any>) => void;
}

export default function CapabilitiesPanel({ settings, onChange }: CapabilitiesPanelProps) {

  const capabilities = [
    {
      key: "autoTranslate",
      title: "Auto-Translation Agent",
      desc: "Automatically detects customer's query language and replies in that language.",
      icon: <Globe className="w-5 h-5 text-indigo-400" />,
      badge: "Language",
    },
    {
      key: "sentimentGuard",
      title: "Sentiment Analyzer Guardrail",
      desc: "Triggers immediate handoff to human supervisor upon detecting negative sentiment or frustration.",
      icon: <Heart className="w-5 h-5 text-rose-400" />,
      badge: "Emotional Intelligence",
    },
    {
      key: "leadQualifier",
      title: "Autonomous Lead Qualifier",
      desc: "Collects, extracts, and grades contact parameters from the live dialogue and saves it directly to the CRM.",
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
      badge: "CRM Integration",
    },
    {
      key: "injectionGuard",
      title: "Prompt Injection & Safety Shield",
      desc: "Intercepts and blocks hack inputs, adversarial prompts, or offensive text before they reach the core LLM.",
      icon: <ShieldCheck className="w-5 h-5 text-cyan-400" />,
      badge: "Security",
    },
    {
      key: "autoSummary",
      title: "Human Handoff Summarizer",
      desc: "Instantly synthesizes a neat executive wrap-up of the conversation logs when a human supervisor intervenes.",
      icon: <FileText className="w-5 h-5 text-amber-400" />,
      badge: "Observability",
    },
  ];

  const handleToggle = (key: string) => {
    onChange({
      ...settings,
      [key]: !settings[key],
    });
  };

  return (
    <div className="space-y-4">
      {capabilities.map((cap) => {
        const isEnabled = !!settings[cap.key];
        return (
          <div
            key={cap.key}
            onClick={() => handleToggle(cap.key)}
            className={`flex items-start gap-4 p-5 rounded-2xl border transition-all duration-200 cursor-pointer ${
              isEnabled
                ? "border-[var(--accent-primary)] bg-[rgba(6,182,212,0.04)]"
                : "border-white/5 bg-zinc-950/20 hover:border-white/10 hover:bg-zinc-900/20"
            }`}
          >
            <div className={`p-2.5 rounded-xl bg-zinc-900 border border-white/5`}>
              {cap.icon}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-bold text-white">{cap.title}</span>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-zinc-400 tracking-wide font-mono">
                  {cap.badge}
                </span>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed font-light">{cap.desc}</p>
            </div>

            <div className="relative inline-flex items-center h-6 rounded-full w-11 shrink-0 transition-colors bg-zinc-800 border border-zinc-700 pointer-events-none">
              <span
                className={`inline-block w-4 h-4 transform rounded-full bg-white transition-transform ${
                  isEnabled ? "translate-x-6 bg-[var(--accent-primary)]" : "translate-x-1"
                }`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
