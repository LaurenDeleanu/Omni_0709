"use client";

import React, { useState } from "react";
import { GitBranch, Check, PackageOpen } from "lucide-react";

interface GitStatusFile {
  path: string;
  status: string;
}

interface GitChangesPanelProps {
  files: GitStatusFile[];
  branch: string;
}

function getStatusLabel(status: string) {
  switch (status) {
    case "M": return { letter: "M", color: "text-green-400", bg: "bg-green-400/10", label: "modified" };
    case "A": return { letter: "A", color: "text-amber-400", bg: "bg-amber-400/10", label: "added" };
    case "D": return { letter: "D", color: "text-red-400", bg: "bg-red-400/10", label: "deleted" };
    case "??": return { letter: "U", color: "text-amber-300", bg: "bg-amber-300/10", label: "untracked" };
    default:
      if (!status) return { letter: "?", color: "text-[#858585]", bg: "bg-[#858585]/10", label: "unknown" };
      return { letter: status, color: "text-[#858585]", bg: "bg-[#858585]/10", label: status.toLowerCase() };
  }
}

export default function GitChangesPanel({ files, branch }: GitChangesPanelProps) {
  const [message, setMessage] = useState("");

  const unstaged = files.filter((f) => f.status !== "staged");
  const staged = files.filter((f) => f.status === "staged");

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-1 px-3 py-2 border-b border-[#333333]">
        <GitBranch size={14} className="text-[#569cd6]" />
        <span className="text-[13px] text-[#cccccc]">{branch}</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {unstaged.length === 0 && staged.length === 0 ? (
          <div className="text-[13px] text-[#858585] p-4 text-center">
            No changes in working tree.
          </div>
        ) : (
          <>
            {staged.length > 0 && (
              <div>
                <div className="flex items-center justify-between px-3 py-1">
                  <span className="text-[12px] font-semibold text-[#bbbbbb] uppercase">Staged Changes</span>
                  <button className="text-[11px] text-[#858585] hover:text-[#cccccc]">Unstage All</button>
                </div>
                {staged.map((f) => {
                  const s = getStatusLabel(f.status);
                  return (
                    <div
                      key={f.path}
                      className="flex items-center gap-1.5 px-3 py-0.5 hover:bg-[#2a2d2e] cursor-pointer text-[13px]"
                    >
                      <span className={`font-bold ${s.color}`}>{s.letter}</span>
                      <span className="text-[#cccccc] truncate">{f.path.split("/").pop()}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {unstaged.length > 0 && (
              <div>
                <div className="flex items-center justify-between px-3 py-1 mt-2">
                  <span className="text-[12px] font-semibold text-[#bbbbbb] uppercase">Changes</span>
                  <button className="text-[11px] text-[#858585] hover:text-[#cccccc]">Stage All</button>
                </div>
                {unstaged.map((f) => {
                  const s = getStatusLabel(f.status);
                  return (
                    <div
                      key={f.path}
                      className="flex items-center gap-1.5 px-3 py-0.5 hover:bg-[#2a2d2e] cursor-pointer text-[13px]"
                    >
                      <span className={`font-bold ${s.color}`}>{s.letter}</span>
                      <span className="text-[#cccccc] truncate">{f.path.split("/").pop()}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>

      {files.length > 0 && (
        <div className="border-t border-[#333333] p-2 space-y-2">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Commit message..."
            className="w-full h-14 bg-[#3c3c3c] border border-[#3c3c3c] focus:border-[#007acc] rounded px-2 py-1 text-[13px] text-[#cccccc] placeholder-[#858585] outline-none resize-none"
          />
          <div className="flex gap-1">
            <button className="flex-1 flex items-center justify-center gap-1 text-[12px] bg-[#0e639c] hover:bg-[#1177bb] text-white rounded py-1 font-semibold">
              <Check size={14} />
              Commit
            </button>
            <button className="flex items-center justify-center gap-1 text-[12px] bg-[#3c3c3c] hover:bg-[#454545] text-[#cccccc] rounded py-1 px-2">
              <PackageOpen size={14} />
              Create Patch
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
