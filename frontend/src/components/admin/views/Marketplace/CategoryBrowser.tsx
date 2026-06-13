"use client";
import React from "react";

interface Category {
  id: string;
  label: string;
  icon: string;
}

interface CategoryBrowserProps {
  categories: Category[];
  selectedCategory: string;
  onSelectCategory: (id: string) => void;
}

export default function CategoryBrowser({
  categories,
  selectedCategory,
  onSelectCategory,
}: CategoryBrowserProps) {
  return (
    <div className="w-64 border-r border-white/5 bg-[#0a0a0c] overflow-y-auto custom-scrollbar p-4 flex flex-col gap-1.5 shrink-0 text-white text-xs">
      <span className="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">
        Categorías de Plantillas
      </span>
      {categories.map((cat) => (
        <button
          key={cat.id}
          onClick={() => onSelectCategory(cat.id)}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all ${
            selectedCategory === cat.id
              ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium"
              : "text-zinc-400 hover:bg-white/[0.03] hover:text-zinc-200"
          }`}
        >
          <span className="text-base opacity-80">{cat.icon}</span>
          {cat.label}
        </button>
      ))}
    </div>
  );
}
