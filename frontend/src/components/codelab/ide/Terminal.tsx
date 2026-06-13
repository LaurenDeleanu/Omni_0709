"use client";

import React from "react";
import { X, Trash2, Terminal as TerminalIcon, AlertTriangle, Bug } from "lucide-react";

export interface Problem {
  file: string;
  line: number;
  col: number;
  type: "error" | "warning";
  message: string;
}

interface TerminalProps {
  output: string;
  problems: Problem[];
  activeTab: "terminal" | "problems" | "output" | "debug";
  onTabChange: (tab: "terminal" | "problems" | "output" | "debug") => void;
  onClear: () => void;
  promptText?: string;
}

const terminalTabs = [
  { id: "terminal" as const, label: "TERMINAL", icon: TerminalIcon },
  { id: "problems" as const, label: "PROBLEMS", icon: AlertTriangle },
  { id: "output" as const, label: "OUTPUT", icon: TerminalIcon },
  { id: "debug" as const, label: "DEBUG CONSOLE", icon: Bug },
];

export default function Terminal({
  output,
  problems,
  activeTab,
  onTabChange,
  onClear,
  promptText = "$ npx tsc --noEmit",
}: TerminalProps) {
  return (
    <div className="flex flex-col bg-[#1e1e1e] border-t border-[#333333]">
      <div className="flex items-center bg-[#252526] border-b border-[#333333] min-h-[28px]">
        <div className="flex items-center flex-1 overflow-x-auto scrollbar-none">
          {terminalTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-1 px-3 h-[28px] text-[11px] border-r border-[#333333] select-none shrink-0 ${
                  isActive
                    ? "bg-[#1e1e1e] text-white"
                    : "bg-[#252526] text-[#858585] hover:text-white"
                }`}
              >
                <Icon size={12} strokeWidth={1.5} />
                {tab.label}
                {tab.id === "problems" && problems.length > 0 && (
                  <span className="bg-[#007acc] text-white text-[10px] px-1 rounded-full ml-1">
                    {problems.length}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <button
          onClick={onClear}
          className="p-1 mx-1 hover:bg-[#454545] rounded text-[#858585] hover:text-[#cccccc]"
          title="Clear Terminal"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto min-h-[60px] max-h-[300px] p-2 font-mono text-[12px] leading-relaxed bg-[#1e1e1e]">
        {activeTab === "terminal" && (
          <div className="text-[#cccccc]">
            {promptText && (
              <div className="text-green-400 mb-1">{promptText}</div>
            )}
            {output ? (
              <pre className="whitespace-pre-wrap break-words text-[#cccccc]">{output}</pre>
            ) : (
              <div className="text-[#858585]">Terminal ready. Use the Omni Agent to run commands.</div>
            )}
          </div>
        )}

        {activeTab === "problems" && (
          <div className="text-[#cccccc]">
            {problems.length === 0 ? (
              <div className="text-[#858585] py-2">No problems detected.</div>
            ) : (
              <table className="w-full text-[11px]">
                <tbody>
                  {problems.map((p, i) => (
                    <tr key={i} className="border-b border-[#333333]/30">
                      <td className="py-1 pr-2 text-[#858585] whitespace-nowrap">
                        {p.file}
                      </td>
                      <td className="py-1 pr-2 text-[#858585] whitespace-nowrap">
                        {p.line}:{p.col}
                      </td>
                      <td className="py-1 pr-2 whitespace-nowrap">
                        <span
                          className={
                            p.type === "error"
                              ? "text-red-400"
                              : "text-amber-400"
                          }
                        >
                          {p.type === "error" ? "ERROR" : "WARNING"}
                        </span>
                      </td>
                      <td className="py-1 text-[#cccccc]">{p.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === "output" && (
          <div className="text-[#858585]">Build output will appear here.</div>
        )}

        {activeTab === "debug" && (
          <div className="text-[#858585]">Debug console ready.</div>
        )}
      </div>
    </div>
  );
}
