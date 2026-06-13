"use client";
import React from "react";
import { Portal } from "@/components/admin/Portal";
import { AgentTemplate } from "./AgentTemplateCard";

interface TemplateDetailModalProps {
  template: AgentTemplate;
  onCancel: () => void;
  onUseTemplate: (templateId: string) => void;
  isSaving: boolean;
}

export default function TemplateDetailModal({
  template,
  onCancel,
  onUseTemplate,
  isSaving,
}: TemplateDetailModalProps) {
  return (
    <Portal>
      <div
        className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm"
        onClick={(e) => {
          if (e.target === e.currentTarget) onCancel();
        }}
      >
        <div className="bg-[#18181b] border border-white/10 p-8 w-full max-w-xl rounded-3xl shadow-2xl animate-slide-up flex flex-col text-left text-white text-xs gap-5">
          {/* Header */}
          <div className="flex gap-4 items-start pb-4 border-b border-white/5">
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-3xl shrink-0">
              {template.icon}
            </div>
            
            <div className="flex-1 min-w-0">
              <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 uppercase tracking-wider">
                {template.category.toUpperCase()}
              </span>
              <h2 className="text-xl font-bold mt-1 text-zinc-100">{template.name}</h2>
              <p className="text-[10px] text-zinc-500 mt-0.5">
                Creado por <span className="text-indigo-400 font-semibold">{template.author}</span> • ⭐ {template.rating.toFixed(1)} ({template.installs.toLocaleString()} descargas)
              </p>
            </div>

            <div className="flex flex-col items-end shrink-0">
              <span className="text-lg font-black text-emerald-400 font-mono">
                {template.priceType === "FREE" ? "Gratis" : `$${template.priceValue}`}
              </span>
              <span className="text-[8px] text-zinc-500 mt-0.5">Licencia única</span>
            </div>
          </div>

          {/* Body */}
          <div className="flex flex-col gap-4 max-h-[45vh] overflow-y-auto pr-1 custom-scrollbar leading-relaxed text-zinc-300">
            {/* Overview */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Descripción del Agente:</span>
              <p>{template.description}</p>
            </div>

            {/* Features */}
            <div className="flex flex-col gap-2 border-t border-white/5 pt-3">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Capacidades y Características:</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                {template.features.map((feature, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-zinc-400">
                    <span className="text-emerald-400 font-bold text-sm shrink-0">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Template Specs */}
            <div className="grid grid-cols-2 gap-4 border-t border-white/5 pt-3 mt-1 text-[10px] text-zinc-500">
              <div className="flex flex-col gap-0.5">
                <span className="font-bold text-zinc-400">Nodos de Decisión pre-cargados:</span>
                <span>{template.stepsCount} bloques estructurados</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="font-bold text-zinc-400">Restricciones de Memoria:</span>
                <span>Almacenamiento en base vectorial pre-configurado</span>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex gap-3 w-full border-t border-white/5 pt-4">
            <button
              onClick={onCancel}
              className="flex-1 py-3 bg-white/5 hover:bg-white/10 rounded-xl font-semibold border border-white/5 hover:border-white/10 transition-colors text-center"
            >
              Cerrar
            </button>
            <button
              onClick={() => onUseTemplate(template.id)}
              disabled={isSaving}
              className="flex-1 py-3 bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-600 hover:to-cyan-600 rounded-xl font-semibold shadow-lg shadow-indigo-500/20 transition-all text-center text-white"
            >
              {isSaving ? "Instalando..." : "Utilizar esta Plantilla"}
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
}
