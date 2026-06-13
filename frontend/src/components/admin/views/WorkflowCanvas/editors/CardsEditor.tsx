"use client";
import React, { useState } from "react";
import { X, GripVertical, Plus } from "lucide-react";

const CARD_CATALOG = [
  {
    category: "ENVIAR MENSAJES",
    items: [
      { type: "TEXT", label: "Texto", icon: "T", desc: "Envía un mensaje de texto simple al usuario.", defaultProps: { content: "" } },
      { type: "IMAGE", label: "Imagen", icon: "🖼️", desc: "Envía una imagen mediante URL.", defaultProps: { url: "" } },
      { type: "AUDIO", label: "Audio", icon: "🔊", desc: "Envía un archivo de audio (ej. nota de voz).", defaultProps: { url: "" } },
      { type: "VIDEO", label: "Video", icon: "🎥", desc: "Envía un video corto.", defaultProps: { url: "" } },
      { type: "FILE", label: "Documento", icon: "📄", desc: "Envía un documento o archivo adjunto.", defaultProps: { url: "" } },
    ]
  }
];

export function CardsEditor({ stepType, config, onChange }: { stepType: string, config: any, onChange: (c: any) => void }) {
  const cards = Array.isArray(config.cards) ? config.cards : [];

  const addCard = (cardTemplate: any) => {
    const newCards = [...cards, { ...cardTemplate.defaultProps, type: cardTemplate.type, id: crypto.randomUUID().slice(0, 9) }];
    onChange({ ...config, cards: newCards });
  };

  const removeCard = (index: number) => {
    const newCards = [...cards];
    newCards.splice(index, 1);
    onChange({ ...config, cards: newCards });
  };

  const updateCard = (index: number, key: string, value: any) => {
    const newCards = [...cards];
    newCards[index] = { ...newCards[index], [key]: value };
    onChange({ ...config, cards: newCards });
  };

  const moveCard = (index: number, dir: number) => {
    if (index + dir < 0 || index + dir >= cards.length) return;
    const newCards = [...cards];
    const temp = newCards[index];
    newCards[index] = newCards[index + dir];
    newCards[index + dir] = temp;
    onChange({ ...config, cards: newCards });
  };

  const [showCatalog, setShowCatalog] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      {/* Cards List */}
      <div className="flex-1 space-y-4">
        {cards.length === 0 && (
          <div className="text-center p-6 bg-black/20 rounded-xl border border-dashed border-white/10 text-zinc-500 text-xs">
            No hay burbujas de mensaje definidas. Añade una abajo.
          </div>
        )}
        
        {cards.map((c: any, i: number) => (
          <div key={c.id || i} className="bg-zinc-900 border border-white/10 rounded-xl p-4 relative group">
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center gap-2">
                <GripVertical className="w-4 h-4 text-zinc-600 cursor-grab" />
                <span className="text-[10px] font-bold text-white bg-zinc-800 px-2 py-0.5 rounded uppercase tracking-wider">{c.type.replace("_", " ")}</span>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button type="button" onClick={() => moveCard(i, -1)} className="p-1 hover:bg-white/10 rounded text-zinc-400 text-xs" disabled={i === 0}>↑</button>
                <button type="button" onClick={() => moveCard(i, 1)} className="p-1 hover:bg-white/10 rounded text-zinc-400 text-xs" disabled={i === cards.length - 1}>↓</button>
                <button type="button" onClick={() => removeCard(i)} className="p-1 hover:bg-rose-500/20 rounded text-rose-400">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Dynamic Card Fields based on Type */}
            {c.type === "TEXT" && (
              <textarea 
                className="input text-xs w-full bg-black/30 border-white/5" 
                rows={3} 
                placeholder="Contenido del mensaje (Soporta variables como {{nombre}})..."
                value={c.content || ""} 
                onChange={(e) => updateCard(i, "content", e.target.value)} 
              />
            )}
            
            {["IMAGE", "AUDIO", "VIDEO", "FILE"].includes(c.type) && (
              <div className="space-y-1">
                <label className="text-[10px] text-zinc-500 font-bold uppercase">URL del Recurso:</label>
                <input 
                  type="url"
                  className="input text-xs w-full bg-black/30 border-white/5" 
                  placeholder="https://ejemplo.com/archivo.jpg"
                  value={c.url || ""} 
                  onChange={(e) => updateCard(i, "url", e.target.value)} 
                />
              </div>
            )}
          </div>
        ))}

        {/* Add Card Button & Dropdown Menu */}
        <div className="relative mt-2">
          <button 
            type="button" 
            onClick={() => setShowCatalog(!showCatalog)}
            className="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl border border-dashed border-white/20 bg-white/5 hover:bg-white/10 text-white text-xs font-semibold transition-all"
          >
            <Plus className="w-4 h-4 text-indigo-400" />
            Añadir Mensaje
          </button>
          
          {showCatalog && (
            <div className="absolute top-full left-0 right-0 z-50 mt-2 bg-zinc-950 border border-white/10 rounded-xl p-3 shadow-2xl max-h-[300px] overflow-y-auto custom-scrollbar">
              <div className="flex justify-between items-center mb-2 pb-2 border-b border-white/5">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Burbujas de Mensaje</h3>
                <button type="button" onClick={() => setShowCatalog(false)} className="text-zinc-500 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex flex-col gap-1.5">
                {CARD_CATALOG[0].items.map(item => (
                  <button 
                    key={item.type}
                    type="button"
                    onClick={() => {
                      addCard(item);
                      setShowCatalog(false);
                    }}
                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors text-left w-full"
                  >
                    <span className="text-sm w-6 text-center text-emerald-400 bg-emerald-500/10 p-1.5 rounded-lg">{item.icon}</span>
                    <div className="flex flex-col">
                      <span className="text-xs text-zinc-300 font-bold">{item.label}</span>
                      {item.desc && <span className="text-[9px] text-zinc-500 leading-tight mt-0.5">{item.desc}</span>}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
