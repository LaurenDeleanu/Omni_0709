"use client";
import React from "react";

export interface AgentTemplate {
  id: string;
  name: string;
  tagline: string;
  description: string;
  category: string;
  rating: number;
  installs: number;
  priceType: "FREE" | "PAID";
  priceValue: number;
  icon: string;
  features: string[];
  stepsCount: number;
  author: string;
}

interface AgentTemplateCardProps {
  template: AgentTemplate;
  onSelect: () => void;
}

export default function AgentTemplateCard({ template, onSelect }: AgentTemplateCardProps) {
  const getCategoryLabel = (cat: string) => {
    if (cat === "crm") return "Sales & CRM";
    if (cat === "ecommerce") return "E-Commerce";
    if (cat === "workflows") return "Workflows";
    if (cat === "support") return "Atención";
    return "DevOps & Tools";
  };

  return (
    <div
      onClick={onSelect}
      className="group bg-[#18181b]/50 hover:bg-[#202024]/70 border border-white/5 hover:border-white/10 rounded-2xl p-5 transition-all duration-300 cursor-pointer flex flex-col gap-4 text-white hover:-translate-y-1 text-xs"
    >
      {/* Top icons / badges */}
      <div className="flex justify-between items-start">
        <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/25 p-2 flex items-center justify-center text-lg shadow-sm shrink-0">
          {template.icon}
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 uppercase tracking-wider">
            {getCategoryLabel(template.category)}
          </span>
          <span className="text-[10px] font-bold font-mono text-emerald-400">
            {template.priceType === "FREE" ? "Gratis" : `$${template.priceValue}`}
          </span>
        </div>
      </div>

      {/* Main Info */}
      <div className="flex-1 flex flex-col gap-1 min-w-0">
        <h3 className="font-bold text-sm text-zinc-100 group-hover:text-white transition-colors truncate">
          {template.name}
        </h3>
        <p className="text-[10px] text-zinc-400 line-clamp-2 leading-relaxed">
          {template.tagline}
        </p>
      </div>

      {/* Ratings / Install count footer */}
      <div className="flex justify-between items-center border-t border-white/5 pt-3 mt-1 text-[10px] text-zinc-500">
        <div className="flex items-center gap-2">
          <span>⭐ {template.rating.toFixed(1)}</span>
          <span>•</span>
          <span>👥 {template.installs.toLocaleString()} installs</span>
        </div>
        
        <span className="text-[10px] font-bold text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">
          Ver detalles →
        </span>
      </div>
    </div>
  );
}
