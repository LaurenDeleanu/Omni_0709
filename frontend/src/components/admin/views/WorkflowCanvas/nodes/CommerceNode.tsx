import React from "react";
import { Handle, Position } from "@xyflow/react";
import { ShoppingBag, ShoppingCart, CreditCard, CalendarDays, DollarSign } from "lucide-react";

export default function CommerceNode({ data }: { data: any }) {
  const label = data.label || "Comercio";
  const type = data.type;
  const config = data.config || {};
  const branches = Array.isArray(config.branches) ? config.branches : [];

  const getCommerceIcon = () => {
    switch (type) {
      case "SHOW_PRODUCTS": return <ShoppingBag className="w-3.5 h-3.5" />;
      case "ADD_TO_CART": return <ShoppingCart className="w-3.5 h-3.5" />;
      case "CHECKOUT": return <CreditCard className="w-3.5 h-3.5" />;
      case "BOOKING": return <CalendarDays className="w-3.5 h-3.5" />;
      default: return <DollarSign className="w-3.5 h-3.5" />;
    }
  };

  return (
    <div className="glass-card min-w-[280px] max-w-[340px] rounded-2xl border border-emerald-500/30 hover:border-emerald-500/60 shadow-[0_8px_30px_rgba(16,185,129,0.15)] transition-all duration-300 relative group overflow-hidden bg-gradient-to-br from-emerald-950/20 via-zinc-900/95 to-zinc-950/98 backdrop-blur-xl">
      {/* Target Input handle on Left */}
      <Handle 
        type="target" 
        position={Position.Left} 
        className="w-3 h-3 bg-emerald-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ left: "-6px" }} 
      />

      <div className="absolute top-2 right-3 flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
        {type === "SHOW_PRODUCTS" ? "🛍️ Productos" : type === "ADD_TO_CART" ? "🛒 Carrito" : type === "CHECKOUT" ? "💳 Checkout" : type === "BOOKING" ? "📅 Agenda" : "💵 Pago Fijo"}
      </div>

      {/* Node Header */}
      <div className="p-3 border-b border-emerald-500/10 bg-emerald-500/5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-sm">
          {getCommerceIcon()}
        </div>
        <div className="min-w-0">
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">COMERCIAL</p>
          <h4 className="text-xs font-bold text-white truncate">{label}</h4>
        </div>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2.5">
        {type === "SHOW_PRODUCTS" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 flex items-center justify-between text-[10px]">
            <span className="text-zinc-500 font-bold uppercase">Productos Seleccionados:</span>
            <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-bold">
              {Array.isArray(config.productIds) ? config.productIds.length : 0} ítems
            </span>
          </div>
        )}

        {type === "ADD_TO_CART" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 space-y-1 text-[10px] text-zinc-400">
            <div className="flex justify-between items-center">
              <span>Variable Carrito:</span>
              <span className="font-mono text-emerald-400">{"{{" + (config.cartField || "cart") + "}}"}</span>
            </div>
            <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-1.5">
              <span>Texto Origen:</span>
              <span className="font-mono text-zinc-300">{"{{" + (config.cartSourceField || "seleccion") + "}}"}</span>
            </div>
          </div>
        )}

        {type === "CHECKOUT" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 space-y-1 text-[10px] text-zinc-400">
            <div className="flex justify-between items-center">
              <span>Envío (Costo):</span>
              <span className="font-bold text-emerald-400">${config.shippingFee || 0} USD</span>
            </div>
            <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-1.5">
              <span>Pasarela de Pago:</span>
              <span className="font-bold text-zinc-300 uppercase">{config.gateway || "Stripe"}</span>
            </div>
          </div>
        )}

        {type === "BOOKING" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 space-y-1 text-[10px] text-zinc-400">
            <div className="flex justify-between items-center">
              <span>Agenda ID:</span>
              <span className="font-mono truncate max-w-[120px] text-zinc-300">{config.scheduleId || "Google Calendar"}</span>
            </div>
            <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-1.5">
              <span>Guardar en:</span>
              <span className="font-mono text-emerald-400">{"{{" + (config.field || "fecha") + "}}"}</span>
            </div>
          </div>
        )}

        {type === "PAYMENT" && (
          <div className="bg-black/30 border border-white/5 rounded-xl p-2.5 space-y-1 text-[10px] text-zinc-400">
            <div className="flex justify-between items-center">
              <span>Monto Fijo:</span>
              <span className="font-bold text-emerald-400">
                {config.dynamic ? "Monto Dinámico" : `${config.amount || 0} ${config.currency || "USD"}`}
              </span>
            </div>
            <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-1.5">
              <span>Estado guardado:</span>
              <span className="font-mono text-zinc-300">{"{{" + (config.field || "pago_completado") + "}}"}</span>
            </div>
          </div>
        )}

        {/* Transition routes if branches are configured */}
        {branches.length > 0 && (
          <div className="space-y-1.5 mt-2 pt-2 border-t border-white/5">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">Rutas (Bifurcaciones):</span>
            {branches.map((b: any, idx: number) => (
              <div key={idx} className="relative flex items-center justify-between p-2 rounded bg-black/40 border border-white/5 text-[10px] pr-8">
                <span className="text-zinc-300 font-mono truncate max-w-[200px]">→ {b.match}</span>
                <Handle 
                  type="source" 
                  position={Position.Right} 
                  id={`branch-${idx}`} 
                  className="w-2.5 h-2.5 bg-amber-500 border border-zinc-950 rounded-full hover:scale-125 transition-transform" 
                  style={{ right: "-4px" }} 
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Node action */}
      <button 
        type="button" 
        onClick={(e) => { e.stopPropagation(); data.onEdit(); }}
        className="w-full text-center py-2 border-t border-white/5 hover:bg-white/5 text-[10px] text-zinc-400 font-semibold transition-all hover:text-white"
      >
        Configurar Comercio
      </button>

      {/* Sequential output handle on Right */}
      <Handle 
        type="source" 
        position={Position.Right} 
        id="default" 
        className="w-3 h-3 bg-emerald-500 border-2 border-zinc-950 rounded-full hover:scale-125 transition-transform" 
        style={{ right: "-6px" }} 
      />
    </div>
  );
}
