"use client";

import React, { useState } from "react";
import { Search, Regex, CaseSensitive, WholeWord, ChevronRight } from "lucide-react";

interface SearchResult {
  file: string;
  line: number;
  snippet: string;
}

interface SearchPanelProps {
  onSelectFile: (path: string) => void;
}

export default function SearchPanel({ onSelectFile }: SearchPanelProps) {
  const [query, setQuery] = useState("");
  const [replace, setReplace] = useState("");
  const [showReplace, setShowReplace] = useState(false);
  const [useRegex, setUseRegex] = useState(false);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [wholeWord, setWholeWord] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);

  const handleSearch = () => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setResults([
      { file: "src/app/codelab/page.tsx", line: 42, snippet: "  const [activeFilePath, setActiveFilePath] = ..." },
    ]);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-2 space-y-2">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search"
            className="w-full bg-[#3c3c3c] border border-[#3c3c3c] focus:border-[#007acc] rounded px-2 py-1 text-[13px] text-[#cccccc] placeholder-[#858585] outline-none"
          />
        </div>

        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setCaseSensitive(!caseSensitive)}
            className={`p-0.5 rounded ${caseSensitive ? "bg-[#007acc] text-white" : "text-[#858585] hover:text-[#cccccc]"}`}
            title="Match Case"
          >
            <CaseSensitive size={14} />
          </button>
          <button
            onClick={() => setWholeWord(!wholeWord)}
            className={`p-0.5 rounded ${wholeWord ? "bg-[#007acc] text-white" : "text-[#858585] hover:text-[#cccccc]"}`}
            title="Match Whole Word"
          >
            <WholeWord size={14} />
          </button>
          <button
            onClick={() => setUseRegex(!useRegex)}
            className={`p-0.5 rounded ${useRegex ? "bg-[#007acc] text-white" : "text-[#858585] hover:text-[#cccccc]"}`}
            title="Use Regular Expression"
          >
            <Regex size={14} />
          </button>
        </div>

        <button
          onClick={() => setShowReplace(!showReplace)}
          className="flex items-center gap-1 text-[12px] text-[#858585] hover:text-[#cccccc]"
        >
          <ChevronRight size={12} className={`transition-transform ${showReplace ? "rotate-90" : ""}`} />
          Replace
        </button>

        {showReplace && (
          <div className="space-y-1">
            <input
              type="text"
              value={replace}
              onChange={(e) => setReplace(e.target.value)}
              placeholder="Replace"
              className="w-full bg-[#3c3c3c] border border-[#3c3c3c] focus:border-[#007acc] rounded px-2 py-1 text-[13px] text-[#cccccc] placeholder-[#858585] outline-none"
            />
            <button className="w-full text-[12px] bg-[#0e639c] hover:bg-[#1177bb] text-white rounded py-1">
              Replace All
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto border-t border-[#333333]">
        {results.length === 0 && query && (
          <div className="text-[13px] text-[#858585] p-3">No results found.</div>
        )}
        {results.map((r, i) => (
          <div
            key={i}
            onClick={() => onSelectFile(r.file)}
            className="px-3 py-1.5 cursor-pointer hover:bg-[#2a2d2e] border-b border-[#333333]/50"
          >
            <div className="flex items-center gap-1.5 text-[12px] text-[#569cd6] font-semibold">
              <span>{r.file.split("/").pop()}</span>
              <span className="text-[#858585] font-normal">{r.line}</span>
            </div>
            <div className="text-[12px] text-[#cccccc] mt-0.5 truncate">{r.snippet}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
