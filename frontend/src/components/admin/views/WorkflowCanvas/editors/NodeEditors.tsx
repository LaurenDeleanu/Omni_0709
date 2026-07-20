import React from "react";
import { Step } from "@/shared";
import { GitMerge, Zap } from "lucide-react";

interface NodeEditorProps {
  stepType: string;
  config: any;
  handleFieldChange: (key: string, value: any) => void;
  handleConfigChange: (config: any) => void;
  steps: Step[];
  schedules: any[];
  dynamicModels: any[];
  editingStepId: string;
}

export function BranchLogicEditor({
  config,
  handleFieldChange,
  steps,
  editingStepId
}: Omit<NodeEditorProps, "handleConfigChange" | "dynamicModels" | "stepType">) {
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
    <div className="glass p-4 rounded-xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent mt-2">
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
                    {steps.filter(s => s.id !== editingStepId).map(s => (
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
}

export function NodeEditorFields(props: NodeEditorProps) {
  const { stepType, config, handleFieldChange, handleConfigChange, steps, schedules, dynamicModels, editingStepId } = props;

  return (
    <>
      {stepType === "COLLECT_FIELD" && (
        <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Variables y Captura</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Nombre de la Variable (Guardar en)</label>
            <input className="input text-xs font-mono" placeholder="Ej: user_email" value={config.field || ""} onChange={e => handleFieldChange("field", e.target.value.trim())} />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Tipo de Validación</label>
            <select className="input text-xs" value={config.validationType || "none"} onChange={e => handleFieldChange("validationType", e.target.value)}>
              <option value="none">Ninguna (Entrada Libre)</option>
              <option value="email">📧 Correo Electrónico</option>
              <option value="phone">📱 Teléfono Internacional</option>
              <option value="number">🔢 Número Entero/Decimal</option>
            </select>
          </div>
        </div>
      )}

      {stepType === "CHOICE_LIST" && (
        <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Lista de Opciones (WhatsApp Buttons)</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable de Destino</label>
            <input className="input text-xs font-mono" value={config.field || "seleccion"} onChange={e => handleFieldChange("field", e.target.value.trim())} />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1.5 flex justify-between">
              <span>Botones de Opción</span>
              <span className="text-[9px] text-zinc-500">Límite de WhatsApp: 10 botones</span>
            </label>
            <div className="space-y-2">
              {Array.isArray(config.options) && config.options.map((opt: string, idx: number) => (
                <div key={idx} className="flex gap-2 items-center">
                  <input className="input text-xs py-1" value={opt} onChange={e => {
                    const newOpts = [...config.options];
                    newOpts[idx] = e.target.value;
                    handleFieldChange("options", newOpts);
                  }} />
                  <button type="button" onClick={() => {
                    const newOpts = config.options.filter((_: any, i: number) => i !== idx);
                    handleFieldChange("options", newOpts);
                  }} className="text-rose-400 hover:text-rose-300 p-1 text-xs">X</button>
                </div>
              ))}
              <button type="button" onClick={() => {
                const current = Array.isArray(config.options) ? config.options : [];
                handleFieldChange("options", [...current, `Opción ${current.length + 1}`]);
              }} className="w-full text-center py-1.5 border border-dashed border-indigo-500/30 hover:bg-indigo-500/10 rounded-lg text-[10px] text-indigo-300 font-bold">
                + Agregar Opción
              </button>
            </div>
          </div>
        </div>
      )}

      {stepType === "FILE_UPLOAD" && (
        <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">Parámetros de Archivos</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar URL</label>
            <input className="input text-xs font-mono" value={config.field || "archivo_url"} onChange={e => handleFieldChange("field", e.target.value.trim())} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-300">Paso Opcional (Permitir saltar)</span>
            <input type="checkbox" checked={config.optional || false} onChange={e => handleFieldChange("optional", e.target.checked)} className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Tipos Aceptados</label>
            <select className="input text-xs" value={config.acceptType || "any"} onChange={e => handleFieldChange("acceptType", e.target.value)}>
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
            <input type="checkbox" checked={config.ocrEnabled || false} onChange={e => handleFieldChange("ocrEnabled", e.target.checked)} className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" />
          </div>
        </div>
      )}

      {stepType === "BOOKING" && (
        <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">📅 Reserva de Citas</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Guardar Fecha/Hora en variable:</label>
            <input className="input text-xs font-mono" value={config.field || "fecha_cita"} onChange={e => handleFieldChange("field", e.target.value.trim())} />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Vincular Agenda Disponible</label>
            <select className="input text-xs" value={config.scheduleId || ""} onChange={e => handleFieldChange("scheduleId", e.target.value)}>
              <option value="">-- Google Calendar (Integración Directa) --</option>
              {schedules.map(sch => (
                <option key={sch.id} value={sch.id}>{sch.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center justify-between border-t border-white/5 pt-3">
            <span className="text-xs text-zinc-300 font-semibold">Validación Automática de Disponibilidad</span>
            <input type="checkbox" checked={config.calendarSync !== false} onChange={e => handleFieldChange("calendarSync", e.target.checked)} className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" />
          </div>
        </div>
      )}

      {stepType === "CONDITION" && (
        <div className="glass p-4 border border-amber-500/20 rounded-xl bg-amber-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">🔀 Bifurcación Condicional</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable a Evaluar</label>
            <input className="input text-xs font-mono" placeholder="Ej: conversation.score" value={config.checkField || ""} onChange={e => handleFieldChange("checkField", e.target.value.trim())} />
          </div>
        </div>
      )}

      {stepType === "AB_TEST" && (
        <div className="glass p-4 border border-amber-500/20 rounded-xl bg-amber-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">⚖️ Test Comparativo A/B</h4>
          <div>
            <div className="flex justify-between items-center text-xs mb-1.5 text-zinc-300">
              <span>Tránsito hacia Rama A:</span>
              <span className="font-bold text-pink-400">{config.branchAWeight ?? 50}%</span>
            </div>
            <input type="range" min="0" max="100" className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-pink-500" value={config.branchAWeight ?? 50} onChange={e => handleFieldChange("branchAWeight", parseInt(e.target.value))} />
            <div className="flex justify-between items-center text-[10px] text-zinc-500 mt-1">
              <span>100% Rama B</span>
              <span>50/50 Equitativo</span>
              <span>100% Rama A</span>
            </div>
          </div>
          <div className="space-y-3 pt-3 border-t border-white/5">
            <div>
              <label className="label text-[10px] text-pink-400 font-bold uppercase mb-1">Paso Destino Rama A</label>
              <select className="input text-xs bg-black/40 border-pink-500/20" value={config.branchAStepId || ""} onChange={e => handleFieldChange("branchAStepId", e.target.value)}>
                <option value="">-- Seleccionar Paso --</option>
                {steps.filter(s => s.id !== editingStepId).map(s => (
                  <option key={s.id} value={s.id}>#{s.order} - {s.label || s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label text-[10px] text-violet-400 font-bold uppercase mb-1">Paso Destino Rama B</label>
              <select className="input text-xs bg-black/40 border-violet-500/20" value={config.branchBStepId || ""} onChange={e => handleFieldChange("branchBStepId", e.target.value)}>
                <option value="">-- Seleccionar Paso --</option>
                {steps.filter(s => s.id !== editingStepId).map(s => (
                  <option key={s.id} value={s.id}>#{s.order} - {s.label || s.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {stepType === "AI_RESPONDER" && (
        <div className="glass p-4 border border-purple-500/20 rounded-xl bg-purple-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">🧠 LLM Inteligente (RAG)</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Respuesta IA</label>
            <input className="input text-xs font-mono" value={config.field || "respuesta_ia"} onChange={e => handleFieldChange("field", e.target.value.trim())} />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Modelo de Inteligencia</label>
            <select className="input text-xs" value={config.aiModel || "llama-3.1-8b-instant"} onChange={e => handleFieldChange("aiModel", e.target.value)}>
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
            <textarea className="input text-xs" rows={3} placeholder="Ej: Eres un vendedor enfocado en concretar la venta de repuestos..." value={config.systemPrompt || ""} onChange={e => handleFieldChange("systemPrompt", e.target.value)} />
          </div>
          <div>
            <div className="flex justify-between items-center text-xs text-zinc-300 mb-1.5">
              <span>Creatividad (Temperatura):</span>
              <span className="font-mono text-purple-400">{config.temperature ?? 0.7}</span>
            </div>
            <input type="range" min="0" max="1" step="0.1" className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-purple-500" value={config.temperature ?? 0.7} onChange={e => handleFieldChange("temperature", parseFloat(e.target.value))} />
          </div>
          <div className="flex items-center justify-between border-t border-white/5 pt-3">
            <div className="flex flex-col">
              <span className="text-xs text-zinc-300 font-semibold">Buscar en Base de Conocimientos</span>
              <span className="text-[9px] text-zinc-500">Activa RAG con tus documentos scrapeados/subidos</span>
            </div>
            <input type="checkbox" checked={config.useKnowledgeBase !== false} onChange={e => handleFieldChange("useKnowledgeBase", e.target.checked)} className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" />
          </div>
        </div>
      )}

      {stepType === "AUTONOMOUS_AGENT" && (
        <div className="glass p-4 border border-purple-500/20 rounded-xl bg-purple-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">🤖 Agente Autónomo Completo</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Diálogo</label>
            <input className="input text-xs font-mono" value={config.field || "respuesta_ia"} onChange={e => handleFieldChange("field", e.target.value.trim())} />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Modelo AI</label>
            <select className="input text-xs" value={config.aiModel || "llama-3.1-8b-instant"} onChange={e => handleFieldChange("aiModel", e.target.value)}>
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
            <textarea className="input text-xs" rows={4} placeholder="Ej: Eres el agente principal de soporte técnico..." value={config.systemPrompt || ""} onChange={e => handleFieldChange("systemPrompt", e.target.value)} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-300">Base de Conocimientos Activa (RAG)</span>
            <input type="checkbox" checked={config.useKnowledgeBase !== false} onChange={e => handleFieldChange("useKnowledgeBase", e.target.checked)} className="rounded text-indigo-600 bg-black border-zinc-700 focus:ring-indigo-500" />
          </div>
        </div>
      )}

      {stepType === "API_CALL" && (
        <div className="glass p-4 border border-orange-500/20 rounded-xl bg-orange-500/5 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-orange-400">🔌 Integración API Webhook</h4>
            <span className="text-[8px] bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2 py-0.5 rounded font-mono font-bold">FULL EDITOR</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-1">
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Método</label>
              <select className="input text-xs" value={config.apiMethod || "POST"} onChange={e => handleFieldChange("apiMethod", e.target.value)}>
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">URL de Destino</label>
              <input className="input text-xs font-mono" placeholder="https://ejemplo.com/hook" value={config.apiUrl || config.webhookUrl || ""} onChange={e => {
                const val = e.target.value.trim();
                handleConfigChange({ ...config, apiUrl: val, webhookUrl: val });
              }} />
            </div>
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1.5 flex justify-between">
              <span>Headers (Formato JSON)</span>
              <span className="text-[8px] text-zinc-500">Ej: {"{\"Authorization\": \"Bearer X\"}"}</span>
            </label>
            <textarea className="input font-mono text-[10px] bg-black/40 border-white/5" rows={2} placeholder='{"Content-Type": "application/json"}' value={config.apiHeaders || "{}"} onChange={e => handleFieldChange("apiHeaders", e.target.value)} />
          </div>
          {config.apiMethod !== "GET" && (
            <div>
              <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1.5 flex justify-between">
                <span>Cuerpo de Solicitud (Body Template)</span>
                <span className="text-[8px] text-zinc-500">Soporta interpolación {"{{variable}}"}</span>
              </label>
              <textarea className="input font-mono text-[10px] bg-black/40 border-white/5" rows={4} placeholder='{\n  "usuario": "{{nombre}}",\n  "celular": "{{client.whatsappNumber}}"\n}' value={config.apiBody || ""} onChange={e => handleFieldChange("apiBody", e.target.value)} />
            </div>
          )}
          <div className="border-t border-white/5 pt-3 space-y-3">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Extracción de Respuesta</span>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label text-[9px] text-zinc-400 font-bold uppercase mb-1">Ruta en JSON (Dot notation)</label>
                <input className="input text-xs font-mono" placeholder="data.ticket_id" value={config.extractPath || ""} onChange={e => handleFieldChange("extractPath", e.target.value.trim())} />
              </div>
              <div>
                <label className="label text-[9px] text-zinc-400 font-bold uppercase mb-1">Guardar en Variable</label>
                <input className="input text-xs font-mono" placeholder="ticket_id" value={config.saveToField || ""} onChange={e => handleFieldChange("saveToField", e.target.value.trim())} />
              </div>
            </div>
          </div>
          <div className="border-t border-white/5 pt-3">
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Si la petición falla (Error routing)</label>
            <select className="input text-xs bg-black/40 border-rose-500/20" value={config.errorStepId || ""} onChange={e => handleFieldChange("errorStepId", e.target.value)}>
              <option value="">-- Ignorar y seguir flujo normal --</option>
              {steps.filter(s => s.id !== editingStepId).map(s => (
                <option key={s.id} value={s.id}>#{s.order} - {s.label || s.name}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {stepType === "CALL_WORKFLOW" && (
        <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">🔄 Llamada a Sub-flujo conversacional</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">ID del Bot / Sub-flujo Destino</label>
            <input className="input text-xs font-mono" placeholder="Ej: bot_clov67x..." value={config.workflowId || ""} onChange={e => handleFieldChange("workflowId", e.target.value.trim())} />
            <p className="text-[9px] text-zinc-500 mt-1 leading-normal">
              Al llegar a este paso, el bot actual suspenderá su ejecución y transferirá el control conversacional al bot especificado.
            </p>
          </div>
        </div>
      )}

      {stepType === "CREATE_LEAD" && (
        <div className="glass p-4 border border-blue-500/20 rounded-xl bg-blue-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">👤 Actualización de Etapa Funnel CRM</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Mover Lead a la Etapa:</label>
            <select className="input text-xs font-semibold capitalize" value={config.newLeadStage || "qualified"} onChange={e => handleFieldChange("newLeadStage", e.target.value)}>
              <option value="lead">Lead (Prospecto)</option>
              <option value="qualified">Qualified (Calificado)</option>
              <option value="proposal">Proposal (Propuesta)</option>
              <option value="won">Won (Ganado/Cliente) 🎉</option>
              <option value="lost">Lost (Perdido)</option>
            </select>
          </div>
        </div>
      )}

      {stepType === "HUMAN_TAKEOVER" && (
        <div className="glass p-4 border border-rose-500/20 rounded-xl bg-rose-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400">🎧 Soporte Humano (Handoff)</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Mensaje de Despedida / Handoff</label>
            <textarea className="input text-xs" rows={3} placeholder="Un agente humano continuará esta conversación en breve..." value={config.prompt || ""} onChange={e => handleFieldChange("prompt", e.target.value)} />
          </div>
        </div>
      )}

      {stepType === "CRM_ACTION" && (
        <div className="glass p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">👤 CRM Action</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Action Type</label>
            <select className="input text-xs" value={config.crmActionType || "CREATE_CONTACT"} onChange={e => handleFieldChange("crmActionType", e.target.value)}>
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

      {stepType === "CODE_GENERATE" && (
        <div className="glass p-4 border border-cyan-500/20 rounded-xl bg-cyan-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400">💻 AI Code Generator</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Code Description Prompt</label>
            <textarea className="input text-xs" rows={3} placeholder="Describe what the agent should write..." value={config.codePrompt || ""} onChange={e => handleFieldChange("codePrompt", e.target.value)} />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Save Output File Path</label>
            <input className="input text-xs font-mono" placeholder="src/components/MyModule.ts" value={config.filePath || ""} onChange={e => handleFieldChange("filePath", e.target.value)} />
          </div>
        </div>
      )}

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

      {stepType === "APPROVAL_GATE" && (
        <div className="glass p-4 border border-amber-500/20 rounded-xl bg-amber-500/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">🛡️ Human Approval Gate</h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Notification Supervisor Email</label>
            <input className="input text-xs" placeholder="supervisor@empresa.com" value={config.supervisorEmail || ""} onChange={e => handleFieldChange("supervisorEmail", e.target.value)} />
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Review Details Instructions</label>
            <textarea className="input text-xs" rows={2} placeholder="Review the code generated by the agent before merge..." value={config.approvalInstructions || ""} onChange={e => handleFieldChange("approvalInstructions", e.target.value)} />
          </div>
        </div>
      )}

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

      {stepType === "POWER_AUTOMATE" && (
        <div className="glass p-4 border border-[#0078D4]/30 rounded-xl bg-[#0078D4]/5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-[#0078D4] flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5" /> Power Automate Flow
          </h4>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">HTTP Request URL (from Power Automate)</label>
            <input className="input text-xs font-mono" placeholder="https://prod-1...logic.azure.com/workflows/..." value={config.flowUrl || ""} onChange={e => handleFieldChange("flowUrl", e.target.value.trim())} />
            <p className="text-[9px] text-zinc-500 mt-1">Crea un flujo de Power Automate que inicie con &quot;Cuando se recibe una solicitud HTTP&quot; y pega la URL aquí.</p>
          </div>
          <div>
            <label className="label text-[10px] text-zinc-400 font-bold uppercase mb-1">Variable Guardar Respuesta</label>
            <input className="input text-xs font-mono" placeholder="pa_response" value={config.field || ""} onChange={e => handleFieldChange("field", e.target.value.trim())} />
            <p className="text-[9px] text-zinc-500 mt-1">Opcional. Guarda el JSON que responda Power Automate.</p>
          </div>
        </div>
      )}

      {["CONDITION", "AUTONOMOUS_AGENT", "CHOICE_LIST"].includes(stepType) && (
        <BranchLogicEditor
          config={config}
          handleFieldChange={handleFieldChange}
          steps={steps}
          schedules={schedules}
          editingStepId={editingStepId}
        />
      )}
    </>
  );
}
