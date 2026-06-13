"use client";

import React from "react";
import { Search, Calculator, Calendar, Code, Plus } from "lucide-react";

interface ToolBindingPanelProps {
  activeTools: string[];
  onToggleTool: (toolId: string) => void;
}

export default function ToolBindingPanel({ activeTools, onToggleTool }: ToolBindingPanelProps) {

  const skills = [
    {
      id: "get_employee_profile",
      icon: <Search className="w-5 h-5 text-sky-400" />,
      title: "Perfil de Empleado 👥",
      desc: "Obtiene la ficha, datos de contacto, rol y detalles del perfil de un empleado usando su correo o ID.",
      badge: "RRHH",
    },
    {
      id: "list_department_members",
      icon: <Code className="w-5 h-5 text-indigo-400" />,
      title: "Miembros de Departamento 🏢",
      desc: "Lista los miembros activos e información clave de un departamento específico de la empresa.",
      badge: "Organización",
    },
    {
      id: "get_vacation_balance",
      icon: <Calendar className="w-5 h-5 text-emerald-400" />,
      title: "Saldo de Vacaciones 📅",
      desc: "Consulta el saldo de días de vacaciones restantes y acumuladas de un empleado.",
      badge: "Beneficios",
    },
    {
      id: "create_it_ticket",
      icon: <Calculator className="w-5 h-5 text-amber-400" />,
      title: "Ticket de Soporte IT 🛠️",
      desc: "Permite al agente registrar un ticket de soporte técnico (Hardware, Software, Redes) en el panel de IT.",
      badge: "Soporte",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {skills.map((skill) => {
          const isSelected = activeTools.includes(skill.id);
          return (
            <button
              key={skill.id}
              type="button"
              onClick={() => onToggleTool(skill.id)}
              className={`text-left p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between h-44 relative group ${
                isSelected
                  ? "border-[var(--accent-primary)] bg-[rgba(6,182,212,0.04)]"
                  : "border-white/5 bg-zinc-950/20 hover:border-white/10 hover:bg-zinc-900/20"
              }`}
            >
              <div className="flex justify-between items-start w-full">
                <div className="p-2.5 rounded-xl bg-zinc-900 border border-white/5">
                  {skill.icon}
                </div>
                <div className="relative inline-flex items-center h-5 rounded-full w-9 shrink-0 transition-colors bg-zinc-800 border border-zinc-700 pointer-events-none">
                  <span
                    className={`inline-block w-3 h-3 transform rounded-full bg-white transition-transform ${
                      isSelected ? "translate-x-5 bg-[var(--accent-primary)]" : "translate-x-1"
                    }`}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-bold text-white group-hover:text-[var(--accent-primary)] transition-colors">
                    {skill.title}
                  </span>
                  <span className="text-[8px] tracking-wide uppercase px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-zinc-400 font-mono">
                    {skill.badge}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-normal font-light line-clamp-2">
                  {skill.desc}
                </p>
              </div>
            </button>
          );
        })}

        {/* Custom Connector card */}
        <div className="border border-dashed border-white/10 rounded-2xl p-5 flex flex-col justify-center items-center text-center h-44 bg-zinc-950/10 hover:border-zinc-700 transition-colors cursor-pointer group">
          <div className="p-3 rounded-full bg-zinc-900 border border-white/5 mb-3 group-hover:scale-105 transition-transform">
            <Code className="w-5 h-5 text-zinc-500 group-hover:text-[var(--accent-primary)]" />
          </div>
          <span className="text-xs font-bold text-white mb-1">Connect Custom REST Tool</span>
          <p className="text-[10px] text-zinc-500 max-w-[200px] leading-normal font-light">
            Bind custom endpoints, headers, schema models, and webhooks in the Integrations Hub.
          </p>
        </div>
      </div>
    </div>
  );
}
