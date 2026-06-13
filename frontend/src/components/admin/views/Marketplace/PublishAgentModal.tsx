"use client";
import React, { useState } from "react";
import { Portal } from "@/components/admin/Portal";
import { toast } from "sonner";

interface PublishAgentModalProps {
  botName: string;
  onCancel: () => void;
  onPublish: (templateData: any) => void;
}

export default function PublishAgentModal({
  botName,
  onCancel,
  onPublish,
}: PublishAgentModalProps) {
  const [name, setName] = useState(`${botName} - Reusable Template`);
  const [tagline, setTagline] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("crm");
  const [priceType, setPriceType] = useState("FREE");
  const [priceValue, setPriceValue] = useState("0");
  
  const handlePublishClick = () => {
    if (!name || !tagline || !description) {
      toast.error("Por favor completa los campos requeridos.");
      return;
    }

    onPublish({
      name,
      tagline,
      description,
      category,
      priceType,
      priceValue: priceType === "FREE" ? 0 : parseFloat(priceValue) || 0,
    });
  };

  return (
    <Portal>
      <div
        className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm"
        onClick={(e) => {
          if (e.target === e.currentTarget) onCancel();
        }}
      >
        <div className="bg-[#18181b] border border-white/10 p-8 w-full max-w-lg rounded-3xl shadow-2xl animate-slide-up flex flex-col text-left text-white text-xs">
          <h2 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent mb-2">
            Publicar Agente en el Marketplace
          </h2>
          <p className="text-zinc-400 text-[11px] mb-6 leading-relaxed">
            Publica la estructura, flujos de decisiones, configuraciones de memoria y herramientas del agente actual para que otros usuarios o departamentos de tu organización lo implementen.
          </p>

          <div className="flex flex-col gap-4 max-h-[50vh] overflow-y-auto pr-1 custom-scrollbar mb-6">
            
            {/* Template Name */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Nombre de la Plantilla *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Nombre descriptivo"
                className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Tagline */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Línea de Introducción (Tagline) *</label>
              <input
                type="text"
                value={tagline}
                onChange={(e) => setTagline(e.target.value)}
                placeholder="Ej: Sincronización autónoma de leads con Salesforce y notificaciones Teams."
                className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Long description */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Descripción Detallada *</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Detalla qué hace este agente, qué APIs requiere y las configuraciones sugeridas."
                className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500 h-24 resize-none leading-relaxed"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Category */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Categoría</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none"
                >
                  <option value="crm">CRM & Ventas</option>
                  <option value="ecommerce">E-Commerce</option>
                  <option value="workflows">Automatización de Workflows</option>
                  <option value="support">Atención al Cliente</option>
                  <option value="devtools">Desarrollo & DevOps</option>
                </select>
              </div>

              {/* Price Type */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Esquema de Precios</label>
                <select
                  value={priceType}
                  onChange={(e) => setPriceType(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none"
                >
                  <option value="FREE">Gratis (Interno)</option>
                  <option value="PAID">Venta Comercial (Premium)</option>
                </select>
              </div>
            </div>

            {priceType === "PAID" && (
              <div className="flex flex-col gap-1.5 animate-fade-in">
                <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Precio de Licencia (USD) *</label>
                <div className="flex items-center gap-2">
                  <span className="text-zinc-400 font-bold">$</span>
                  <input
                    type="number"
                    value={priceValue}
                    onChange={(e) => setPriceValue(e.target.value)}
                    placeholder="99.00"
                    className="w-32 bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <span className="text-zinc-500 font-bold">USD</span>
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3 w-full border-t border-white/5 pt-4">
            <button
              onClick={onCancel}
              className="flex-1 py-3 bg-white/5 hover:bg-white/10 rounded-xl font-semibold border border-white/5 hover:border-white/10 transition-colors text-center"
            >
              Cancelar
            </button>
            <button
              onClick={handlePublishClick}
              className="flex-1 py-3 bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-600 hover:to-cyan-600 rounded-xl font-semibold shadow-lg shadow-indigo-500/20 transition-all text-center"
            >
              Publicar en Catálogo
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
}
