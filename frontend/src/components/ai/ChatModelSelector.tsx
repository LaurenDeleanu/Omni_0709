import React, { useState, useRef, useEffect } from "react";
import { Settings } from "lucide-react";

export const MODEL_OPTIONS = [
  { value: "gpt-4o-mini", label: "Fast (GPT-4o-mini)" },
  { value: "gpt-4o", label: "Balanced (GPT-4o)" },
  { value: "o1-mini", label: "Reasoning (o1-mini)" },
];

interface ChatModelSelectorProps {
  selectedModel: string;
  handleModelChange: (model: string) => void;
}

export function ChatModelSelector({ selectedModel, handleModelChange }: ChatModelSelectorProps) {
  const [showModelSelector, setShowModelSelector] = useState(false);
  const modelSelectorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelSelectorRef.current && !modelSelectorRef.current.contains(e.target as Node)) {
        setShowModelSelector(false);
      }
    };
    if (showModelSelector) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showModelSelector]);

  const onModelChange = (val: string) => {
    handleModelChange(val);
    setShowModelSelector(false);
  };

  return (
    <>
      <div ref={modelSelectorRef} className="relative">
        <button
          onClick={() => setShowModelSelector(!showModelSelector)}
          className="text-zinc-500 hover:text-white p-1 hover:bg-white/5 rounded-lg transition-colors"
          title="Change model"
        >
          <Settings size={16} />
        </button>
        {showModelSelector && (
          <div className="absolute top-full right-0 mt-1 w-52 bg-slate-900 border border-zinc-700 rounded-xl shadow-lg z-50 overflow-hidden">
            {MODEL_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => onModelChange(opt.value)}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-white/5 transition-colors flex items-center justify-between ${
                  selectedModel === opt.value ? "text-violet-400 font-semibold" : "text-zinc-300"
                }`}
              >
                {opt.label}
                {selectedModel === opt.value && <span className="text-violet-400">✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>
      <span className="text-[10px] text-zinc-600 bg-slate-900 border border-zinc-800 px-2 py-0.5 rounded-full">
        {MODEL_OPTIONS.find((m) => m.value === selectedModel)?.label.split(" ")[0]}
      </span>
    </>
  );
}
