"use client";

import React from "react";
import { MessageSquare, Users, GitBranch, Code, ShieldAlert } from "lucide-react";

interface AgentTypeSelectorProps {
  selectedType: string;
  onChange: (type: string) => void;
}

export default function AgentTypeSelector({ selectedType, onChange }: AgentTypeSelectorProps) {

  const types = [
    {
      id: "CONVERSATIONAL",
      icon: <MessageSquare className="w-5 h-5" />,
      title: "Conversational Agent",
      desc: "Ideal for customer support, FAQs, and WhatsApp/Web chat engagements.",
      badge: "Channels",
      color: "text-blue-400 border-blue-500/20 bg-blue-500/5",
      glowColor: "rgba(59, 130, 246, 0.15)",
    },
    {
      id: "CRM",
      icon: <Users className="w-5 h-5" />,
      title: "CRM Specialist",
      desc: "Manages pipeline stages, qualifies leads, updates deal cards, and acts on CRM data.",
      badge: "SaaS CRM",
      color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5",
      glowColor: "rgba(16, 185, 129, 0.15)",
    },
    {
      id: "WORKFLOW",
      icon: <GitBranch className="w-5 h-5" />,
      title: "Workflow Automator",
      desc: "Triggers actions via webhooks or chron jobs, executing parallel branches of automation.",
      badge: "Automation",
      color: "text-amber-400 border-amber-500/20 bg-amber-500/5",
      glowColor: "rgba(245, 158, 11, 0.15)",
    },
    {
      id: "CODE",
      icon: <Code className="w-5 h-5" />,
      title: "Code Developer",
      desc: "Generates code modules, edits project files, and proposes changes to dev branches.",
      badge: "DevOps / Git",
      color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5",
      glowColor: "rgba(6, 182, 212, 0.15)",
    },
    {
      id: "CUSTOM",
      icon: <ShieldAlert className="w-5 h-5" />,
      title: "Custom Agent",
      desc: "Configure an autonomous combination of tools, prompts, and bespoke logic.",
      badge: "BESPOKE",
      color: "text-violet-400 border-violet-500/20 bg-violet-500/5",
      glowColor: "rgba(139, 92, 246, 0.15)",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {types.map((type) => {
        const isSelected = selectedType === type.id;
        return (
          <button
            key={type.id}
            type="button"
            onClick={() => onChange(type.id)}
            className={`text-left p-5 rounded-2xl border transition-all duration-300 relative overflow-hidden group ${
              isSelected
                ? `border-[var(--accent-primary)] bg-[rgba(6,182,212,0.06)] shadow-lg`
                : "border-white/5 bg-zinc-950/40 hover:bg-zinc-900/60 hover:border-white/10"
            }`}
            style={{
              boxShadow: isSelected ? `0 0 25px ${type.glowColor}` : "none",
            }}
          >
            {isSelected && (
              <div className="absolute top-0 right-0 w-2.5 h-2.5 rounded-bl-lg bg-[var(--accent-primary)]" />
            )}
            <div className="flex justify-between items-start mb-3">
              <div className={`p-2.5 rounded-xl border ${type.color} group-hover:scale-105 transition-transform`}>
                {type.icon}
              </div>
              <span className="text-[9px] font-bold tracking-wider uppercase bg-white/5 border border-white/10 px-2 py-0.5 rounded-full text-zinc-400">
                {type.badge}
              </span>
            </div>
            <h4 className="text-sm font-bold text-white mb-1 group-hover:text-[var(--accent-primary)] transition-colors">
              {type.title}
            </h4>
            <p className="text-xs text-zinc-400 leading-relaxed font-light">
              {type.desc}
            </p>
          </button>
        );
      })}
    </div>
  );
}
