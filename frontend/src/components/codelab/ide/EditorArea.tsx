"use client";

import React, { ReactNode } from "react";
import EditorTabs, { EditorTab } from "./EditorTabs";
import MonacoEditorWrapper from "./MonacoEditorWrapper";
import Terminal, { Problem } from "./Terminal";

interface EditorAreaProps {
  tabs: EditorTab[];
  activeFilePath: string;
  onSelectTab: (path: string) => void;
  onCloseTab: (path: string) => void;
  fileContent: string;
  onContentChange: (value: string | undefined) => void;
  language: string;
  terminalOutput: string;
  problems: Problem[];
  terminalTab: "terminal" | "problems" | "output" | "debug";
  onTerminalTabChange: (tab: "terminal" | "problems" | "output" | "debug") => void;
  onClearTerminal: () => void;
  onCursorChange: (line: number, col: number) => void;
  gitModifiedLines?: { added: number[]; removed: number[]; modified: number[] };
  children?: ReactNode;
}

export default function EditorArea({
  tabs,
  activeFilePath,
  onSelectTab,
  onCloseTab,
  fileContent,
  onContentChange,
  language,
  terminalOutput,
  problems,
  terminalTab,
  onTerminalTabChange,
  onClearTerminal,
  onCursorChange,
  gitModifiedLines,
  children,
}: EditorAreaProps) {
  return (
    <div className="flex-1 flex flex-col min-w-0 bg-[#1e1e1e]">
      {tabs.length > 0 ? (
        <>
          <EditorTabs
            tabs={tabs}
            activeFilePath={activeFilePath}
            onSelectTab={onSelectTab}
            onCloseTab={onCloseTab}
          />
          <div className="flex-1 min-h-0">
            <MonacoEditorWrapper
              value={fileContent}
              onChange={onContentChange}
              language={language}
              gitModifiedLines={gitModifiedLines}
              onCursorChange={onCursorChange}
            />
          </div>
          <Terminal
            output={terminalOutput}
            problems={problems}
            activeTab={terminalTab}
            onTabChange={onTerminalTabChange}
            onClear={onClearTerminal}
          />
        </>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-[#858585] bg-[#1e1e1e]">
          <span className="text-4xl mb-3">📂</span>
          <span className="text-[14px]">Open a file from the Explorer to begin editing.</span>
          <span className="text-[12px] text-[#555555] mt-1">Ctrl+P to search files</span>
        </div>
      )}
      {children}
    </div>
  );
}
