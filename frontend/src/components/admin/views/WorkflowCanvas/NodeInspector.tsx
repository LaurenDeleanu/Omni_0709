"use client";
import React, { useState, useEffect } from "react";
import { X, Settings, Trash2, Copy, Plus, ArrowDownRight, GitMerge, AlertCircle, Link, HelpCircle, Bot } from "lucide-react";
import { Step } from "@/shared";
import { CardsEditor } from "./editors/CardsEditor";
import { nodeIcons } from "./NodeCategories";

export default function NodeInspector({
  editingStep,
  setEditingStep,
  steps,
  products = [],
  schedules = [],
  dynamicModels = [],
  onSave,
  onClose,
  onDelete,
  onDuplicate
}: {
  editingStep: Step;
  setEditingStep: (s: Step | null) => void;
  steps: Step[];
  products: any[];
  schedules: any[];
  dynamicModels: any[];
  onSave: (stepId: string, updatedData: Partial<Step>) => Promise<void>;
  onClose: () => void;
  onDelete: (stepId: string) => Promise<void>;
  onDuplicate: (stepId: string) => Promise<void>;
}) {
  const [label, setLabel] = useState(editingStep.label || editingStep.name);
  const [config, setConfig] = useState<any>({});
  const [isLocalSaving, setIsLocalSaving] = useState(false);

  useEffect(() => {
    setLabel(editingStep.label || editingStep.name);
    try {
      setConfig(typeof editingStep.config === "string" ? JSON.parse(editingStep.config) : editingStep.config || {});
    } catch {
      setConfig({});
    }
  }, [editingStep]);

  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  const handleConfigChange = (newConfig: any) => {
    setConfig(newConfig);
    if (debounceTimer) clearTimeout(debounceTimer);
    const timer = setTimeout(() => {
      const updatedStep = { ...editingStep, label, config: JSON.stringify(newConfig) };
      onSave(editingStep.id, { label, config: JSON.stringify(newConfig) });
    }, 500);
    setDebounceTimer(timer);
  };

  const handleFieldChange = (key: string, value: any) => {
    const updated = { ...config, [key]: value };
    handleConfigChange(updated);
  };

  const handleLabelChange = (val: string) => {
    setLabel(val);
    onSave(editingStep.id, { label: val, config: JSON.stringify(config) });
  };

  const stepType = editingStep.type;

  // Visual branch editor
  const renderBranchEditor = () => {
    const branches = Array.isArray(config.branches) ? config.branches : [];
    
    const addRule = () => {
      const updated = [...branches, { match: "", goToStepId: "", goToStepOrder: 0 }];
      handleFieldChange("branches", updated);
    };

    const removeRule = (idx: number) => {
      const updated = branches.filter((_: any, i: number) => i !== idx);
      handleFieldChange("branches", updated);
    };

    const updateRule = (idx: number, key: string, value: any) => {
      const updated = branches.map((b: any, i: number) => {
        if (i === idx) {
          const rule = { ...b, [key]: value };
          if (key === "goToStepId") {
            const target = steps.find(s => s.id === value);
            rule.goToStepOrder = target ? target.order : 0;
          }
          return rule;
        }
        return b;
      });
      handleFieldChange("branches", updated);
    };

    return (
      <div className="glass p-4 rounded-xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent">
        <div className="flex justify-between items-center mb-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
            <GitMerge className="w-3.5 h-3.5" /> Lógica de Saltos
          </h4>
          <button 
            type="button" 
            onClick={addRule}
            className="text-[10px] bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-semibold px-2 py-1 rounded border border-amber-500/30 transition-colors"
          >
            + Regla
          </button>
        </div>
        
        {branches.length === 0 ? (
          <p className="text-[10px] text-zinc-500 italic text-center py-4 bg-black/10 rounded-lg">
            Sin reglas. El flujo avanzará linealmente.
          </p>
        ) : (
          <div className="space-y-3 mt-2">
            {branches.map((b: any, idx: number) => (
              <div key={idx} className="bg-black/30 border border-white/5 rounded-lg overflow-hidden flex flex-col">
                <div className="bg-white/5 px-2.5 py-1 flex items-center justify-between text-[8px] font-mono text-zinc-500">
                  <span>REGLA #{idx + 1}</span>
                  <button 
                    type="button" 
                    onClick={() => removeRule(idx)}
                    className="text-rose-400 hover:text-rose-300 transition-colors"
                  >
                    Eliminar
                  </button>
                </div>
                <div className="p-2.5 space-y-2">
                  <div>
                    <label className="text-[9px] text-zinc-500 uppercase font-bold mb-1 block">Si coincide con (Palabra/Regex):</label>
                    <input 
                      className="input text-xs py-1 px-2.5 bg-zinc-900/50" 
                      value={b.match || ""} 
                      placeholder="Ej: sí|ok o ^[0-9]+$"
                      onChange={e => updateRule(idx, "match", e.target.value)} 
                    />
                  </div>
                  <div>
                    <label className="text-[9px] text-zinc-500 uppercase font-bold mb-1 block">Ir al Paso:</label>
                    <select 
                      className="input text-xs py-1 px-2.5 bg-zinc-900/50" 
                      value={b.goToStepId || ""}
                      onChange={e => updateRule(idx, "goToStepId", e.target.value)}
                    >
                      <option value="">-- Siguiente Lineal (Defecto) --</option>
                      {steps.filter(s => s.id !== editingStep.id).map(s => (
                        <option key={s.id} value={s.id}>#{s.order} - {s.label || s.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="w-[450px] border-l border-white/5 bg-zinc-950/70 p-6 flex flex-col gap-6 shrink-0 h-full overflow-y-auto custom-scrollbar relative z-20">
      {/* Header Info */}
      <div className="flex justify-between items-start border-b border-white/5 pb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl p-2 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
            {nodeIcons[stepType] || "📦"}
          </span>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
              <Settings className="w-4 h-4 text-indigo-400" />
              Inspector de Nodo
            </h3>
            <span className="badge badge-indigo text-[9px] uppercase font-bold tracking-wider mt-1">{stepType}</span>
          </div>
        </div>
        <button 
          type="button" 
          onClick={onClose}
          className="p-1.5 hover:bg-white/5 rounded-full text-zinc-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Quick Actions Panel */}
      <div className="flex gap-2">
        <button 
          onClick={() => onDuplicate(editingStep.id)}
          className="flex-1 btn-secondary text-xs py-2 px-3 flex items-center justify-center gap-1.5 hover:text-indigo-400"
        >
          <Copy className="w-3.5 h-3.5" /> Duplicar Paso
        </button>
        <button 
          onClick={() => onDelete(editingStep.id)}
          className="flex-1 btn-secondary text-xs py-2 px-3 flex items-center justify-center gap-1.5 hover:text-rose-400 border-rose-500/20 hover:border-rose-500/40"
        >
          <Trash2 className="w-3.5 h-3.5" /> Eliminar Paso
        </button>
      </div>

      {/* Editor Body */}
      <div className="flex flex-col gap-5">
        {/* Step Label name (Common to all) */}
        <div className="glass p-4 border border-white/5 rounded-xl bg-zinc-900/30">
          <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Nombre / Identificador del Paso</label>
          <input 
            className="input text-xs" 
            placeholder="Ej: Solicitar Correo..." 
            value={label} 
            onChange={e => handleLabelChange(e.target.value)} 
            required 
          />
        </div>

        {/* WELCOME / COLLECT_FIELD / CHOICE_LIST / FILE_UPLOAD Cards messaging */}
        {["WELCOME", "COLLECT_FIELD", "CHOICE_LIST", "FILE_UPLOAD", "BOOKING", "PAYMENT", "COMPLETED", "AI_RESPONDER", "AUTONOMOUS_AGENT"].includes(stepType) && (
          <div className="glass p-4 border border-white/5 rounded-xl bg-zinc-900/30">
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3 text-zinc-400">Mensajes del Bot (Burbujas)</h4>
            <CardsEditor stepType={stepType} config={config} onChange={handleConfigChange} />
          </div>
        )}

        {/* 1. COLLECT_FIELD Editor Fields */}
        {stepType === "COLLECT_FIELD" && (
          <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Variables y Captura</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Nombre de la Variable (Guardar en)</label>
              <input 
                className="input text-xs font-mono" 
                placeholder="Ej: user_email" 
                value={config.field || ""}
                onChange={e => handleFieldChange("field", e.target.value.trim())} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Tipo de Validación</label>
              <select 
                className="input text-xs" 
                value={config.validationType || "none"}
                onChange={e => handleFieldChange("validationType", e.target.value)}
              >
                <option value="none">Ninguna (Entrada Libre)</option>
                <option value="email">📧 Correo Electrónico</option>
                <option value="phone">📱 Teléfono Internacional</option>
                <option value="number">🔢 Número Entero/Decimal</option>
              </select>
            </div>
          </div>
        )}

        {/* 2. CHOICE_LIST Editor Fields */}
        {stepType === "CHOICE_LIST" && (
          <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Lista de Opciones (WhatsApp Buttons)</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable de Destino</label>
              <input 
                className="input text-xs font-mono" 
                value={config.field || "seleccion"}
                onChange={e => handleFieldChange("field", e.target.value.trim())} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1.5 flex justify-between">
                <span>Botones de Opción</span>
                <span className="text-[9px] text-zinc-500">Límite de WhatsApp: 10 botones</span>
              </label>
              <div className="space-y-2">
                {Array.isArray(config.options) && config.options.map((opt: string, idx: number) => (
                  <div key={idx} className="flex gap-2 items-center">
                    <input 
                      className="input text-xs py-1" 
                      value={opt} 
                      onChange={e => {
                        const newOpts = [...config.options];
                        newOpts[idx] = e.target.value;
                        handleFieldChange("options", newOpts);
                      }}
                    />
                    <button 
                      type="button"
                      onClick={() => {
                        const newOpts = config.options.filter((_: any, i: number) => i !== idx);
                        handleFieldChange("options", newOpts);
                      }}
                      className="text-rose-400 hover:text-rose-300 p-1 text-xs"
                    >
                      X
                    </button>
                  </div>
                ))}
                <button 
                  type="button"
                  onClick={() => {
                    const current = Array.isArray(config.options) ? config.options : [];
                    handleFieldChange("options", [...current, `Opción ${current.length + 1}`]);
                  }}
                  className="w-full text-center py-1.5 border border-dashed border-indigo-500/30 hover:bg-indigo-500/10 rounded-lg text-[10px] text-indigo-300 font-bold"
                >
                  + Agregar Opción
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 3. FILE_UPLOAD Editor Fields */}
        {stepType === "FILE_UPLOAD" && (
          <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Parámetros de Archivos</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar URL</label>
              <input 
                className="input text-xs font-mono" 
                value={config.field || "archivo_url"}
                onChange={e => handleFieldChange("field", e.target.value.trim())} 
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-300">Paso Opcional (Permitir saltar)</span>
              <input 
                type="checkbox" 
                checked={config.optional || false} 
                onChange={e => handleFieldChange("optional", e.target.checked)}
                className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Tipos Aceptados</label>
              <select 
                className="input text-xs" 
                value={config.acceptType || "any"}
                onChange={e => handleFieldChange("acceptType", e.target.value)}
              >
                <option value="any">Cualquier tipo de archivo</option>
                <option value="image">🖼️ Sólo Imágenes (PNG, JPG)</option>
                <option value="pdf">📄 Sólo Documentos PDF</option>
              </select>
            </div>
            <div className="flex items-center justify-between border-t border-white/5 pt-3">
              <div className="flex flex-col">
                <span className="text-xs text-zinc-300 font-semibold">Extraer texto de Imagen/PDF (OCR)</span>
                <span className="text-[9px] text-zinc-500">Guarda el texto extraído en {"{{variable_ocr}}"}</span>
              </div>
              <input 
                type="checkbox" 
                checked={config.ocrEnabled || false} 
                onChange={e => handleFieldChange("ocrEnabled", e.target.checked)}
                className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" 
              />
            </div>
          </div>
        )}

        {/* 4. SHOW_PRODUCTS Editor Fields */}
        {stepType === "SHOW_PRODUCTS" && (
          <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">🛍️ Catálogo de Productos</h4>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1 block">Selecciona los productos a mostrar:</label>
            {products.length === 0 ? (
              <p className="text-[10px] text-amber-500 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-lg">
                No tienes productos registrados en tu catálogo. Ve a la sección de Productos.
              </p>
            ) : (
              <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                {products.map(p => {
                  const currentIds = Array.isArray(config.productIds) ? config.productIds : [];
                  const isChecked = currentIds.includes(p.id);
                  return (
                    <label key={p.id} className="flex items-center gap-2.5 text-[11px] text-zinc-300 cursor-pointer p-2 bg-black/20 rounded-xl border border-white/5 hover:bg-white/5 hover:border-white/10 transition-colors">
                      <input 
                        type="checkbox" 
                        checked={isChecked}
                        onChange={e => {
                          const newIds = e.target.checked 
                            ? [...currentIds, p.id] 
                            : currentIds.filter((id: string) => id !== p.id);
                          handleFieldChange("productIds", newIds);
                        }}
                        className="rounded bg-black border-zinc-700 text-indigo-500 focus:ring-indigo-500" 
                      />
                      <span>{p.name} - <span className="text-emerald-400 font-semibold">${p.price} {p.currency}</span></span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* 5. ADD_TO_CART Editor Fields */}
        {stepType === "ADD_TO_CART" && (
          <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">🛒 Motor de Carrito IA</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Carrito Virtual</label>
              <input 
                className="input text-xs font-mono" 
                value={config.cartField || "cart"}
                onChange={e => handleFieldChange("cartField", e.target.value.trim())} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable con el pedido del usuario</label>
              <input 
                className="input text-xs font-mono" 
                value={config.cartSourceField || "seleccion_productos"}
                onChange={e => handleFieldChange("cartSourceField", e.target.value.trim())} 
              />
            </div>
          </div>
        )}

        {/* 6. CHECKOUT Editor Fields */}
        {stepType === "CHECKOUT" && (
          <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">💳 Checkout E-Commerce</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Costo de Envío / Tasas Fijas (USD)</label>
              <input 
                type="number"
                className="input text-xs" 
                value={config.shippingFee ?? 0}
                onChange={e => handleFieldChange("shippingFee", parseFloat(e.target.value) || 0)} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Pasarela de Pagos</label>
              <select 
                className="input text-xs" 
                value={config.gateway || "stripe"}
                onChange={e => handleFieldChange("gateway", e.target.value)}
              >
                <option value="stripe">Stripe Gateway (Automático)</option>
                <option value="mercadopago">MercadoPago Link (Manual)</option>
              </select>
            </div>
          </div>
        )}

        {/* 7. BOOKING Editor Fields */}
        {stepType === "BOOKING" && (
          <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">📅 Reserva de Citas</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Guardar Fecha/Hora en variable:</label>
              <input 
                className="input text-xs font-mono" 
                value={config.field || "fecha_cita"}
                onChange={e => handleFieldChange("field", e.target.value.trim())} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Vincular Agenda Disponible</label>
              <select 
                className="input text-xs" 
                value={config.scheduleId || ""}
                onChange={e => handleFieldChange("scheduleId", e.target.value)}
              >
                <option value="">-- Google Calendar (Integración Directa) --</option>
                {schedules.map(sch => (
                  <option key={sch.id} value={sch.id}>{sch.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-between border-t border-white/5 pt-3">
              <span className="text-xs text-zinc-300 font-semibold">Validación Automática de Disponibilidad</span>
              <input 
                type="checkbox" 
                checked={config.calendarSync !== false} 
                onChange={e => handleFieldChange("calendarSync", e.target.checked)}
                className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" 
              />
            </div>
          </div>
        )}

        {/* 8. PAYMENT Editor Fields */}
        {stepType === "PAYMENT" && (
          <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">💵 Cobro Fijo Directo</h4>
            <div className="flex items-center justify-between bg-black/20 p-2.5 rounded-xl border border-white/5">
              <span className="text-xs text-zinc-300 font-semibold">Monto Dinámico (Basado en total del carrito)</span>
              <input 
                type="checkbox" 
                checked={config.dynamic || false} 
                onChange={e => handleFieldChange("dynamic", e.target.checked)}
                className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" 
              />
            </div>
            {!config.dynamic && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Monto Fijo</label>
                  <input 
                    type="number"
                    className="input text-xs" 
                    value={config.amount || 0}
                    onChange={e => handleFieldChange("amount", parseFloat(e.target.value) || 0)} 
                  />
                </div>
                <div>
                  <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Moneda</label>
                  <select 
                    className="input text-xs" 
                    value={config.currency || "USD"}
                    onChange={e => handleFieldChange("currency", e.target.value)}
                  >
                    <option value="USD">USD ($)</option>
                    <option value="MXN">MXN ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="COP">COP ($)</option>
                  </select>
                </div>
              </div>
            )}
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Confirmación</label>
              <input 
                className="input text-xs font-mono" 
                value={config.field || "pago_completado"}
                onChange={e => handleFieldChange("field", e.target.value.trim())} 
              />
            </div>
          </div>
        )}

        {/* 9. CONDITION Editor Fields */}
        {stepType === "CONDITION" && (
          <div className="glass p-4 border border-amber-500/20 rounded-xl bg-amber-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">🔀 Bifurcación Condicional</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable a Evaluar</label>
              <input 
                className="input text-xs font-mono" 
                placeholder="Ej: conversation.score" 
                value={config.checkField || ""}
                onChange={e => handleFieldChange("checkField", e.target.value.trim())} 
              />
            </div>
          </div>
        )}

        {/* 10. AB_TEST Editor Fields */}
        {stepType === "AB_TEST" && (
          <div className="glass p-4 border border-amber-500/20 rounded-xl bg-amber-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">⚖️ Test Comparativo A/B</h4>
            <div>
              <div className="flex justify-between items-center text-xs mb-1.5 text-zinc-300">
                <span>Tránsito hacia Rama A:</span>
                <span className="font-bold text-pink-400">{config.branchAWeight ?? 50}%</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="100" 
                className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-pink-500"
                value={config.branchAWeight ?? 50} 
                onChange={e => handleFieldChange("branchAWeight", parseInt(e.target.value))} 
              />
              <div className="flex justify-between items-center text-[10px] text-zinc-500 mt-1">
                <span>100% Rama B</span>
                <span>50/50 Equitativo</span>
                <span>100% Rama A</span>
              </div>
            </div>

            <div className="space-y-3 pt-3 border-t border-white/5">
              <div>
                <label className="label text-[10px] text-pink-400 font-bold uppercase mb-1">Paso Destino Rama A</label>
                <select 
                  className="input text-xs bg-black/40 border-pink-500/20" 
                  value={config.branchAStepId || ""}
                  onChange={e => handleFieldChange("branchAStepId", e.target.value)}
                >
                  <option value="">-- Seleccionar Paso --</option>
                  {steps.filter(s => s.id !== editingStep.id).map(s => (
                    <option key={s.id} value={s.id}>#{s.order} - {s.label || s.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label text-[10px] text-violet-400 font-bold uppercase mb-1">Paso Destino Rama B</label>
                <select 
                  className="input text-xs bg-black/40 border-violet-500/20" 
                  value={config.branchBStepId || ""}
                  onChange={e => handleFieldChange("branchBStepId", e.target.value)}
                >
                  <option value="">-- Seleccionar Paso --</option>
                  {steps.filter(s => s.id !== editingStep.id).map(s => (
                    <option key={s.id} value={s.id}>#{s.order} - {s.label || s.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* 11. AI_RESPONDER Editor Fields */}
        {stepType === "AI_RESPONDER" && (
          <div className="glass p-4 border border-purple-500/20 rounded-xl bg-purple-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">🧠 LLM Inteligente (RAG)</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Respuesta IA</label>
              <input 
                className="input text-xs font-mono" 
                value={config.field || "respuesta_ia"}
                onChange={e => handleFieldChange("field", e.target.value.trim())} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Modelo de Inteligencia</label>
              <select 
                className="input text-xs" 
                value={config.aiModel || "llama-3.1-8b-instant"}
                onChange={e => handleFieldChange("aiModel", e.target.value)}
              >
                {dynamicModels.map(m => (
                  <option key={m.id} value={m.id}>{m.name || m.id}</option>
                ))}
                {dynamicModels.length === 0 && (
                  <>
                    <option value="llama-3.1-8b-instant">Groq Llama 3.1 8B</option>
                    <option value="google/gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </>
                )}
              </select>
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Instrucciones del Sistema (System Prompt Override)</label>
              <textarea 
                className="input text-xs" 
                rows={3}
                placeholder="Ej: Eres un vendedor enfocado en concretar la venta de repuestos..." 
                value={config.systemPrompt || ""}
                onChange={e => handleFieldChange("systemPrompt", e.target.value)} 
              />
            </div>
            <div>
              <div className="flex justify-between items-center text-xs text-zinc-300 mb-1.5">
                <span>Creatividad (Temperatura):</span>
                <span className="font-mono text-purple-400">{config.temperature ?? 0.7}</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="1" 
                step="0.1" 
                className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
                value={config.temperature ?? 0.7} 
                onChange={e => handleFieldChange("temperature", parseFloat(e.target.value))} 
              />
            </div>
            <div className="flex items-center justify-between border-t border-white/5 pt-3">
              <div className="flex flex-col">
                <span className="text-xs text-zinc-300 font-semibold">Buscar en Base de Conocimientos</span>
                <span className="text-[9px] text-zinc-500">Activa RAG con tus documentos scrapeados/subidos</span>
              </div>
              <input 
                type="checkbox" 
                checked={config.useKnowledgeBase !== false} 
                onChange={e => handleFieldChange("useKnowledgeBase", e.target.checked)}
                className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" 
              />
            </div>
          </div>
        )}

        {/* 12. AUTONOMOUS_AGENT Editor Fields */}
        {stepType === "AUTONOMOUS_AGENT" && (
          <div className="glass p-4 border border-purple-500/20 rounded-xl bg-purple-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">🤖 Agente Autónomo Completo</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Diálogo</label>
              <input 
                className="input text-xs font-mono" 
                value={config.field || "respuesta_ia"}
                onChange={e => handleFieldChange("field", e.target.value.trim())} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Modelo AI</label>
              <select 
                className="input text-xs" 
                value={config.aiModel || "llama-3.1-8b-instant"}
                onChange={e => handleFieldChange("aiModel", e.target.value)}
              >
                {dynamicModels.map(m => (
                  <option key={m.id} value={m.id}>{m.name || m.id}</option>
                ))}
                {dynamicModels.length === 0 && (
                  <>
                    <option value="llama-3.1-8b-instant">Groq Llama 3.1 8B</option>
                    <option value="google/gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </>
                )}
              </select>
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Instrucciones de Personalidad y Directivas</label>
              <textarea 
                className="input text-xs" 
                rows={4}
                placeholder="Ej: Eres el agente principal de soporte técnico..." 
                value={config.systemPrompt || ""}
                onChange={e => handleFieldChange("systemPrompt", e.target.value)} 
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-300">Base de Conocimientos Activa (RAG)</span>
              <input 
                type="checkbox" 
                checked={config.useKnowledgeBase !== false} 
                onChange={e => handleFieldChange("useKnowledgeBase", e.target.checked)}
                className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" 
              />
            </div>
          </div>
        )}

        {/* 13. FULL API_CALL Editor (Open Question 4 Answer) */}
        {stepType === "API_CALL" && (
          <div className="glass p-4 border border-orange-500/20 rounded-xl bg-orange-500/5 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-orange-400">🔌 Integración API Webhook</h4>
              <span className="text-[8px] bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2 py-0.5 rounded font-mono font-bold">FULL EDITOR</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="col-span-1">
                <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Método</label>
                <select 
                  className="input text-xs" 
                  value={config.apiMethod || "POST"}
                  onChange={e => handleFieldChange("apiMethod", e.target.value)}
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">URL de Destino</label>
                <input 
                  className="input text-xs font-mono" 
                  placeholder="https://ejemplo.com/hook" 
                  value={config.apiUrl || config.webhookUrl || ""}
                  onChange={e => {
                    const val = e.target.value.trim();
                    handleConfigChange({ ...config, apiUrl: val, webhookUrl: val });
                  }} 
                />
              </div>
            </div>

            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1.5 flex justify-between">
                <span>Headers (Formato JSON)</span>
                <span className="text-[8px] text-zinc-500">Ej: {"{\"Authorization\": \"Bearer X\"}"}</span>
              </label>
              <textarea 
                className="input font-mono text-[10px] bg-black/40 border-white/5" 
                rows={2}
                placeholder='{"Content-Type": "application/json"}' 
                value={config.apiHeaders || "{}"}
                onChange={e => handleFieldChange("apiHeaders", e.target.value)} 
              />
            </div>

            {config.apiMethod !== "GET" && (
              <div>
                <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1.5 flex justify-between">
                  <span>Cuerpo de Solicitud (Body Template)</span>
                  <span className="text-[8px] text-zinc-500">Soporta interpolación {"{{variable}}"}</span>
                </label>
                <textarea 
                  className="input font-mono text-[10px] bg-black/40 border-white/5" 
                  rows={4}
                  placeholder='{
  "usuario": "{{nombre}}",
  "celular": "{{client.whatsappNumber}}"
}' 
                  value={config.apiBody || ""}
                  onChange={e => handleFieldChange("apiBody", e.target.value)} 
                />
              </div>
            )}

            <div className="border-t border-white/5 pt-3 space-y-3">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Extracción de Respuesta</span>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label text-[9px] text-zinc-400 font-bold uppercase mb-1">Ruta en JSON (Dot notation)</label>
                  <input 
                    className="input text-xs font-mono" 
                    placeholder="data.ticket_id" 
                    value={config.extractPath || ""}
                    onChange={e => handleFieldChange("extractPath", e.target.value.trim())} 
                  />
                </div>
                <div>
                  <label className="label text-[9px] text-zinc-400 font-bold uppercase mb-1">Guardar en Variable</label>
                  <input 
                    className="input text-xs font-mono" 
                    placeholder="ticket_id" 
                    value={config.saveToField || ""}
                    onChange={e => handleFieldChange("saveToField", e.target.value.trim())} 
                  />
                </div>
              </div>
            </div>

            <div className="border-t border-white/5 pt-3">
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Si la petición falla (Error routing)</label>
              <select 
                className="input text-xs bg-black/40 border-rose-500/20" 
                value={config.errorStepId || ""}
                onChange={e => handleFieldChange("errorStepId", e.target.value)}
              >
                <option value="">-- Ignorar y seguir flujo normal --</option>
                {steps.filter(s => s.id !== editingStep.id).map(s => (
                  <option key={s.id} value={s.id}>#{s.order} - {s.label || s.name}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* 14. CALL_WORKFLOW Editor Fields */}
        {stepType === "CALL_WORKFLOW" && (
          <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">🔄 Llamada a Sub-flujo conversacional</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">ID del Bot / Sub-flujo Destino</label>
              <input 
                className="input text-xs font-mono" 
                placeholder="Ej: bot_clov67x..." 
                value={config.workflowId || ""}
                onChange={e => handleFieldChange("workflowId", e.target.value.trim())} 
              />
              <p className="text-[9px] text-zinc-500 mt-1 leading-normal">
                Al llegar a este paso, el bot actual suspenderá su ejecución y transferirá el control conversacional al bot especificado.
              </p>
            </div>
          </div>
        )}

        {/* 15. CREATE_LEAD Editor Fields */}
        {stepType === "CREATE_LEAD" && (
          <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">👤 Actualización de Etapa Funnel CRM</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Mover Lead a la Etapa:</label>
              <select 
                className="input text-xs font-semibold capitalize" 
                value={config.newLeadStage || "qualified"}
                onChange={e => handleFieldChange("newLeadStage", e.target.value)}
              >
                <option value="lead">Lead (Prospecto)</option>
                <option value="qualified">Qualified (Calificado)</option>
                <option value="proposal">Proposal (Propuesta)</option>
                <option value="won">Won (Ganado/Cliente) 🎉</option>
                <option value="lost">Lost (Perdido)</option>
              </select>
            </div>
          </div>
        )}

        {/* 16. HUMAN_TAKEOVER Editor Fields */}
        {stepType === "HUMAN_TAKEOVER" && (
          <div className="glass p-4 border border-rose-500/20 rounded-xl bg-rose-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400">🎧 Soporte Humano (Handoff)</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Mensaje de Despedida / Handoff</label>
              <textarea 
                className="input text-xs" 
                rows={3}
                placeholder="Un agente humano continuará esta conversación en breve..." 
                value={config.prompt || ""}
                onChange={e => handleFieldChange("prompt", e.target.value)} 
              />
            </div>
          </div>
        )}

        {/* 17. CRM_ACTION Editor Fields */}
        {stepType === "CRM_ACTION" && (
          <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">👤 CRM Action</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Action Type</label>
              <select 
                className="input text-xs" 
                value={config.crmActionType || "CREATE_CONTACT"}
                onChange={e => handleFieldChange("crmActionType", e.target.value)}
              >
                <option value="CREATE_CONTACT">Create/Update Contact</option>
                <option value="CREATE_DEAL">Create Sales Deal</option>
                <option value="UPDATE_DEAL_STAGE">Move Deal Funnel Stage</option>
              </select>
            </div>
            {config.crmActionType === "CREATE_DEAL" && (
              <div className="space-y-3">
                <div>
                  <label className="label text-[9px] text-zinc-500 uppercase font-bold mb-1">Deal Title</label>
                  <input className="input text-xs" placeholder="e.g. {{nombre}} deal" value={config.dealTitle || ""} onChange={e => handleFieldChange("dealTitle", e.target.value)} />
                </div>
                <div>
                  <label className="label text-[9px] text-zinc-500 uppercase font-bold mb-1">Deal Value</label>
                  <input type="number" className="input text-xs" value={config.dealValue || 0} onChange={e => handleFieldChange("dealValue", parseFloat(e.target.value) || 0)} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* 18. CODE_GENERATE Editor Fields */}
        {stepType === "CODE_GENERATE" && (
          <div className="glass p-4 border border-cyan-500/20 rounded-xl bg-cyan-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400">💻 AI Code Generator</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Code Description Prompt</label>
              <textarea 
                className="input text-xs" 
                rows={3} 
                placeholder="Describe what the agent should write..." 
                value={config.codePrompt || ""} 
                onChange={e => handleFieldChange("codePrompt", e.target.value)} 
              />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Save Output File Path</label>
              <input className="input text-xs font-mono" placeholder="src/components/MyModule.ts" value={config.filePath || ""} onChange={e => handleFieldChange("filePath", e.target.value)} />
            </div>
          </div>
        )}

        {/* 19. GIT_COMMIT Editor Fields */}
        {stepType === "GIT_COMMIT" && (
          <div className="glass p-4 border border-cyan-500/20 rounded-xl bg-cyan-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400">🐙 Git Commit & PR</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Git Repository URL</label>
              <input className="input text-xs font-mono" placeholder="https://github.com/org/repo" value={config.repoUrl || ""} onChange={e => handleFieldChange("repoUrl", e.target.value)} />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Dev Branch Target</label>
              <input className="input text-xs font-mono" placeholder="dev" value={config.devBranch || "dev"} onChange={e => handleFieldChange("devBranch", e.target.value)} />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Commit Message</label>
              <input className="input text-xs" placeholder="feat: auto generated module" value={config.commitMessage || ""} onChange={e => handleFieldChange("commitMessage", e.target.value)} />
            </div>
          </div>
        )}

        {/* 20. APPROVAL_GATE Editor Fields */}
        {stepType === "APPROVAL_GATE" && (
          <div className="glass p-4 border border-amber-500/20 rounded-xl bg-amber-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">🛡️ Human Approval Gate</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Notification Supervisor Email</label>
              <input className="input text-xs" placeholder="supervisor@empresa.com" value={config.supervisorEmail || ""} onChange={e => handleFieldChange("supervisorEmail", e.target.value)} />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Review Details Instructions</label>
              <textarea 
                className="input text-xs" 
                rows={2} 
                placeholder="Review the code generated by the agent before merge..." 
                value={config.approvalInstructions || ""} 
                onChange={e => handleFieldChange("approvalInstructions", e.target.value)} 
              />
            </div>
          </div>
        )}

        {/* 21. NOTIFICATION Editor Fields */}
        {stepType === "NOTIFICATION" && (
          <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">📢 Notification Alert</h4>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Channel</label>
              <select className="input text-xs" value={config.notifyChannel || "EMAIL"} onChange={e => handleFieldChange("notifyChannel", e.target.value)}>
                <option value="EMAIL">Email Alert</option>
                <option value="SLACK">Slack Hook Alert</option>
                <option value="SMS">SMS Text Alert</option>
              </select>
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Destination Address / Webhook</label>
              <input className="input text-xs font-mono" placeholder="e.g., #alerts or email" value={config.notifyDest || ""} onChange={e => handleFieldChange("notifyDest", e.target.value)} />
            </div>
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Message Body</label>
              <textarea className="input text-xs" rows={3} placeholder="Alert message body..." value={config.notifyBody || ""} onChange={e => handleFieldChange("notifyBody", e.target.value)} />
            </div>
          </div>
        )}

        {/* Dynamic Branching / Exit conditions for appropriate step types */}
          {["CONDITION", "AUTONOMOUS_AGENT", "CHOICE_LIST"].includes(stepType) && (
          <div className="mt-2">
            {renderBranchEditor()}
          </div>
        )}
      </div>

      <div className="flex gap-3 mt-4 pt-4 border-t border-white/5 pb-10">
        <button 
          type="button" 
          onClick={onClose}
          className="btn-secondary flex-1 py-2 text-xs font-semibold"
        >
          Cerrar Inspector
        </button>
      </div>
    </div>
  );
}
