"use client";

import React from "react";
import { X, Circle, File } from "lucide-react";

export interface EditorTab {
  path: string;
  name: string;
  isDirty: boolean;
}

interface EditorTabsProps {
  tabs: EditorTab[];
  activeFilePath: string;
  onSelectTab: (path: string) => void;
  onCloseTab: (path: string) => void;
}

export default function EditorTabs({
  tabs,
  activeFilePath,
  onSelectTab,
  onCloseTab,
}: EditorTabsProps) {
  return (
    <div className="flex items-center bg-[#252526] border-b border-[#1e1e1e] min-h-[35px] overflow-x-auto scrollbar-none">
      {tabs.map((tab) => {
        const isActive = tab.path === activeFilePath;
        return (
          <div
            key={tab.path}
            onClick={() => onSelectTab(tab.path)}
            onMouseDown={(e) => {
              if (e.button === 1) {
                e.preventDefault();
                onCloseTab(tab.path);
              }
            }}
            className={`group flex items-center gap-1.5 h-[35px] px-3 border-r border-[#1e1e1e] cursor-pointer select-none shrink-0 min-w-[120px] max-w-[200px] ${
              isActive
                ? "bg-[#1e1e1e] text-white border-t-2 border-t-[#007acc]"
                : "bg-[#2d2d2d] text-[#969696] hover:bg-[#2d2d30]"
            }`}
          >
            <File size={14} className="shrink-0" />
            <span className="text-[13px] truncate">{tab.name}</span>
            {tab.isDirty ? (
              <Circle size={8} fill="white" className="shrink-0" />
            ) : (
              <span className="w-2 shrink-0" />
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCloseTab(tab.path);
              }}
              className={`p-0.5 rounded hover:bg-[#454545] shrink-0 ${
                isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
              }`}
            >
              <X size={12} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
