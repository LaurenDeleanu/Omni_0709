"use client";

import React from "react";
import { Files, Search, GitBranch, Settings } from "lucide-react";

export type ActivityBarItem = "explorer" | "search" | "source-control" | "settings";

interface ActivityBarProps {
  active: ActivityBarItem;
  onChange: (item: ActivityBarItem) => void;
}

const items: { id: ActivityBarItem; icon: React.ElementType; label: string }[] = [
  { id: "explorer", icon: Files, label: "Explorer" },
  { id: "search", icon: Search, label: "Search" },
  { id: "source-control", icon: GitBranch, label: "Source Control" },
  { id: "settings", icon: Settings, label: "Settings" },
];

export default function ActivityBar({ active, onChange }: ActivityBarProps) {
  return (
    <div className="w-12 flex flex-col items-center bg-[#333333] border-r border-[#252526] py-2 gap-1 shrink-0">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = active === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            title={item.label}
            className={`relative w-12 h-12 flex items-center justify-center transition-colors ${
              isActive
                ? "text-white"
                : "text-[#858585] hover:text-white"
            }`}
          >
            {isActive && (
              <div className="absolute left-0 top-1 bottom-1 w-[2px] bg-white rounded-r" />
            )}
            <Icon size={24} strokeWidth={1.5} />
          </button>
        );
      })}
    </div>
  );
}
