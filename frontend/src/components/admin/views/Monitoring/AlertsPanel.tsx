"use client";
import React, { useState } from "react";
import { toast } from "sonner";

export default function AlertsPanel() {
  const [errorRate, setErrorRate] = useState("5");
  const [latencyLimit, setLatencyLimit] = useState("3000");
  const [costCap, setCostCap] = useState("5.00");
  
  // Notification channels
  const [emailAlert, setEmailAlert] = useState(true);
  const [slackAlert, setSlackAlert] = useState(false);
  const [webhookAlert, setWebhookAlert] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");

  const handleSave = () => {
    toast.success("Políticas de alertas actualizadas con éxito.");
  };

  return (
    <div className="flex flex-col gap-6 text-white text-xs">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Threshold Rules form */}
        <div className="lg:col-span-2 flex flex-col bg-zinc-900/60 border border-white/10 rounded-2xl p-5 gap-4">
          <h3 className="text-sm font-bold text-zinc-200">Reglas de Límites de Alerta</h3>
          <p className="text-[11px] text-zinc-400">
            Define los límites operativos para gatillar avisos automáticos a tu equipo.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
            {/* Fail Rate Threshold */}
            <div className="flex flex-col gap-1.5 p-4 bg-zinc-800/40 border border-white/5 rounded-xl">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Tasa de Errores Máx.</label>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="number"
                  value={errorRate}
                  onChange={(e) => setErrorRate(e.target.value)}
                  className="bg-black/40 border border-white/10 rounded-lg p-2 font-mono text-center text-sm w-20 text-white"
                />
                <span className="font-bold text-zinc-400 text-sm">%</span>
              </div>
              <span className="text-[9px] text-zinc-500 mt-2">Alerta si los fallos superan este porcentaje en 1h.</span>
            </div>

            {/* Latency Limit */}
            <div className="flex flex-col gap-1.5 p-4 bg-zinc-800/40 border border-white/5 rounded-xl">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Latencia Máxima</label>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="number"
                  value={latencyLimit}
                  onChange={(e) => setLatencyLimit(e.target.value)}
                  className="bg-black/40 border border-white/10 rounded-lg p-2 font-mono text-center text-sm w-24 text-white"
                />
                <span className="font-bold text-zinc-400 text-sm">ms</span>
              </div>
              <span className="text-[9px] text-zinc-500 mt-2">Alerta si las ejecuciones superan este tiempo de respuesta.</span>
            </div>

            {/* Cost Cap */}
            <div className="flex flex-col gap-1.5 p-4 bg-zinc-800/40 border border-white/5 rounded-xl">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Límite Diario Gasto</label>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="font-bold text-zinc-400 text-sm">$</span>
                <input
                  type="text"
                  value={costCap}
                  onChange={(e) => setCostCap(e.target.value)}
                  className="bg-black/40 border border-white/10 rounded-lg p-2 font-mono text-center text-sm w-20 text-white"
                />
                <span className="font-bold text-zinc-400 text-xs">USD</span>
              </div>
              <span className="text-[9px] text-zinc-500 mt-2">Alerta si el costo total diario supera esta cantidad.</span>
            </div>
          </div>

          <div className="border-t border-white/5 pt-4 mt-2 flex justify-end">
            <button
              onClick={handleSave}
              className="px-6 py-2.5 bg-indigo-500 hover:bg-indigo-600 rounded-xl font-bold transition-all shadow-md"
            >
              Guardar Políticas
            </button>
          </div>
        </div>

        {/* Channels configuration */}
        <div className="flex flex-col bg-zinc-900/60 border border-white/10 rounded-2xl p-5 gap-4">
          <h3 className="text-sm font-bold text-zinc-200">Canales de Alertas</h3>
          <p className="text-[11px] text-zinc-400">¿Dónde deseas recibir los informes de incidentes?</p>

          <div className="flex flex-col gap-3 mt-2">
            {/* Email Checkbox */}
            <label className="flex items-center justify-between p-3.5 bg-zinc-800/25 border border-white/5 rounded-xl cursor-pointer hover:bg-zinc-850 transition-colors">
              <div className="flex flex-col gap-0.5">
                <span className="font-bold text-zinc-200">📧 Alertas por Email</span>
                <span className="text-[9px] text-zinc-500">Enviar correo a administradores de la organización.</span>
              </div>
              <input
                type="checkbox"
                checked={emailAlert}
                onChange={() => setEmailAlert(!emailAlert)}
                className="w-4 h-4 accent-indigo-500 rounded cursor-pointer"
              />
            </label>

            {/* Slack Checkbox */}
            <label className="flex items-center justify-between p-3.5 bg-zinc-800/25 border border-white/5 rounded-xl cursor-pointer hover:bg-zinc-850 transition-colors">
              <div className="flex flex-col gap-0.5">
                <span className="font-bold text-zinc-200">💬 Integración con Slack</span>
                <span className="text-[9px] text-zinc-500">Publicar alertas en el canal Slack instalado.</span>
              </div>
              <input
                type="checkbox"
                checked={slackAlert}
                onChange={() => setSlackAlert(!slackAlert)}
                className="w-4 h-4 accent-indigo-500 rounded cursor-pointer"
              />
            </label>

            {/* Webhook Checkbox */}
            <div className="flex flex-col gap-2 p-3.5 bg-zinc-800/25 border border-white/5 rounded-xl">
              <div className="flex items-center justify-between cursor-pointer" onClick={() => setWebhookAlert(!webhookAlert)}>
                <div className="flex flex-col gap-0.5">
                  <span className="font-bold text-zinc-200">🔗 Webhook Personalizado</span>
                  <span className="text-[9px] text-zinc-500">Enviar JSON payload a una URL de servidor.</span>
                </div>
                <input
                  type="checkbox"
                  checked={webhookAlert}
                  readOnly
                  className="w-4 h-4 accent-indigo-500 rounded cursor-pointer"
                />
              </div>

              {webhookAlert && (
                <input
                  type="text"
                  placeholder="https://api.internal-security.com/incidents"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-xs text-white mt-1.5 focus:outline-none focus:border-indigo-500"
                />
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
