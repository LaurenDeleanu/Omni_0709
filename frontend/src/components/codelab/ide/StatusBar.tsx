"use client";

import React from "react";
import { GitBranch, AlertCircle, AlertTriangle } from "lucide-react";

export interface StatusBarCursor {
  line: number;
  col: number;
}

interface StatusBarProps {
  branch: string;
  cursor: StatusBarCursor;
  language: string;
  editMode: "direct" | "proposal";
  errorCount: number;
  warningCount: number;
}

export default function StatusBar({
  branch,
  cursor,
  language,
  editMode,
  errorCount,
  warningCount,
}: StatusBarProps) {
  return (
    <div className="h-[22px] bg-[#007acc] text-white flex items-center justify-between px-2 select-none shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <GitBranch size={12} strokeWidth={2} />
          <span className="text-[11px]">{branch}</span>
        </div>
        <span className="text-[11px] opacity-80">
          {editMode === "direct" ? "\u25CE Direct" : "\u2726 Proposal"}
        </span>
      </div>

      <div className="flex items-center gap-1">
        {errorCount > 0 && (
          <span className="flex items-center gap-0.5 text-[11px]">
            <AlertCircle size={12} strokeWidth={2} />
            {errorCount}
          </span>
        )}
        {warningCount > 0 && (
          <span className="flex items-center gap-0.5 text-[11px]">
            <AlertTriangle size={12} strokeWidth={2} />
            {warningCount}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <span className="text-[11px]">
          Ln {cursor.line}, Col {cursor.col}
        </span>
        <span className="text-[11px]">Spaces: 2</span>
        <span className="text-[11px]">UTF-8</span>
        <span className="text-[11px]">{language}</span>
      </div>
    </div>
  );
}
